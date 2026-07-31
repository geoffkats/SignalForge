"""
train_deep.py
-------------
PyTorch dual-encoder trainer for SignalForge Phase 3.

Architecture  (SignalForgeNet in model.py)
-----------------------------------------
  compound_encoder: Linear(2048->256) + BN + ReLU + Dropout(0.3)
  gene_encoder:     Linear(gene_dim->256) + BN + ReLU + Dropout(0.3)
  classifier:       Linear(512->256)+BN+ReLU+Drop(0.3)
                 -> Linear(256->128)+BN+ReLU+Drop(0.2)
                 -> Linear(128->2)

  Separate branches allow independent pretraining on ChEMBL / expression
  data, then fine-tune only the joint classifier head.

Training
--------
  - Adam + ReduceLROnPlateau, CrossEntropyLoss with per-sample weights
  - Early stopping on validation loss (configurable patience)
  - Independent StandardScaler for compound branch and gene branch

Noise reduction
---------------
  - Requires |zscore| >= 3.0 (set at ingest time)
  - Sample weights: abs(zscore) normalised
  - Drops (pert_id, gene_symbol) pairs with conflicting labels
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset, Subset

from .model import SignalForgeNet

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent.parent / "data"
_SMILES_CSV = _DATA_DIR / "processed" / "lincs_smiles.csv"
_PRECOMP_CSV = _DATA_DIR / "raw" / "deepcop" / "inhouse_morgan_2048.csv"
_GO_CSV = _DATA_DIR / "raw" / "deepcop" / "go_fingerprints.csv"

MORGAN_BITS = 2048
GO_DIMS = 1107


# ---------------------------------------------------------------------------
# Compound -> Morgan fingerprint
# ---------------------------------------------------------------------------
_smiles_cache: dict[str, np.ndarray] | None = None
_precomp_cache: dict[str, np.ndarray] | None = None


def _load_smiles_lookup() -> dict[str, np.ndarray]:
    global _smiles_cache
    if _smiles_cache is not None:
        return _smiles_cache

    _smiles_cache = {}
    if not _SMILES_CSV.exists():
        log.warning(
            "lincs_smiles.csv not found at %s -- run extract_smiles.py first", _SMILES_CSV
        )
        return _smiles_cache

    from rdkit import Chem
    from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator

    gen = GetMorganGenerator(radius=2, fpSize=MORGAN_BITS)
    df = pd.read_csv(_SMILES_CSV)
    skipped = 0
    for _, row in df.iterrows():
        smi = str(row["canonical_smiles"])
        pid = str(row["pert_id"])
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            skipped += 1
            continue
        bv = gen.GetFingerprint(mol)
        arr = np.zeros(MORGAN_BITS, dtype=np.float32)
        for bit in bv.GetOnBits():
            arr[bit] = 1.0
        _smiles_cache[pid] = arr

    log.info(
        "Loaded %d compound Morgan FPs from SMILES (%d skipped)", len(_smiles_cache), skipped
    )
    return _smiles_cache


def _load_precomp_lookup() -> dict[str, np.ndarray]:
    global _precomp_cache
    if _precomp_cache is not None:
        return _precomp_cache

    _precomp_cache = {}
    if not _PRECOMP_CSV.exists():
        return _precomp_cache

    df = pd.read_csv(_PRECOMP_CSV)
    fp_cols = [c for c in df.columns if c.startswith("fps")]
    for _, row in df.iterrows():
        name = str(row["mol"]).upper()
        _precomp_cache[name] = row[fp_cols].to_numpy(dtype=np.float32)
    return _precomp_cache


def compound_to_vector(pert_id: str, pert_iname: str = "") -> np.ndarray | None:
    """Return 2048-dim Morgan FP. Lookup: SMILES CSV -> pre-computed -> None."""
    smiles = _load_smiles_lookup()
    if pert_id in smiles:
        return smiles[pert_id]

    precomp = _load_precomp_lookup()
    key = pert_iname.upper()
    if key in precomp:
        return precomp[key]

    return None


# ---------------------------------------------------------------------------
# Gene -> GO fingerprint
# ---------------------------------------------------------------------------
_go_matrix: pd.DataFrame | None = None


def _load_go_matrix() -> pd.DataFrame:
    global _go_matrix
    if _go_matrix is None:
        if _GO_CSV.exists():
            _go_matrix = pd.read_csv(_GO_CSV, index_col=0).astype(np.float32)
        else:
            _go_matrix = pd.DataFrame()
    return _go_matrix


def gene_to_vector(gene_symbol: str) -> np.ndarray | None:
    go = _load_go_matrix()
    if gene_symbol in go.index:
        return go.loc[gene_symbol].to_numpy(dtype=np.float32)
    return None


# ---------------------------------------------------------------------------
# Feature matrix (separate compound and gene branches)
# ---------------------------------------------------------------------------


def build_feature_matrix(
    df: pd.DataFrame,
    feature_dtype: np.dtype = np.float16,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns
    -------
    Xc      : (N, 2048) float32  compound Morgan FP
    Xg      : (N, GO_DIMS) float32  gene GO vector
    y       : (N,) int64
    w       : (N,) float32  abs(zscore) normalised sample weights
    kept_indices : row indices retained from source dataframe
    """
    required = {"pert_id", "pert_iname", "gene_symbol", "zscore", "label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Parquet missing columns: {missing}")

    total = len(df)
    no_compound = 0
    no_gene = 0
    kept_indices: list[int] = []

    # Pass 1: count valid rows and keep indices only (memory-safe).
    for idx, row in df.iterrows():
        comp = compound_to_vector(str(row["pert_id"]), str(row.get("pert_iname", "")))
        if comp is None:
            no_compound += 1
            continue

        gene = gene_to_vector(str(row["gene_symbol"]))
        if gene is None:
            no_gene += 1
            continue

        kept_indices.append(idx)

    n_kept = len(kept_indices)
    log.info(
        "Feature matrix: %d/%d rows kept (dropped %d no-compound, %d no-gene)",
        n_kept,
        total,
        no_compound,
        no_gene,
    )

    # Pass 2: preallocate arrays and fill sequentially.
    Xc = np.empty((n_kept, MORGAN_BITS), dtype=feature_dtype)
    Xg = np.empty((n_kept, GO_DIMS), dtype=feature_dtype)
    y = np.empty(n_kept, dtype=np.int64)
    w = np.empty(n_kept, dtype=np.float32)

    out_i = 0
    for idx in kept_indices:
        row = df.loc[idx]
        comp = compound_to_vector(str(row["pert_id"]), str(row.get("pert_iname", "")))
        gene = gene_to_vector(str(row["gene_symbol"]))
        if comp is None or gene is None:
            # Defensive guard in case source files changed between passes.
            continue

        Xc[out_i] = comp.astype(feature_dtype, copy=False)
        Xg[out_i] = gene.astype(feature_dtype, copy=False)
        y[out_i] = int(row["label"])
        w[out_i] = float(abs(row["zscore"]))
        out_i += 1

    # If guards skipped any rows, trim arrays.
    if out_i != n_kept:
        Xc = Xc[:out_i]
        Xg = Xg[:out_i]
        y = y[:out_i]
        w = w[:out_i]
        kept_indices = kept_indices[:out_i]
    w = w / (w.mean() + 1e-9)

    return Xc, Xg, y, w, np.asarray(kept_indices, dtype=np.int64)


# ---------------------------------------------------------------------------
# Noise filter
# ---------------------------------------------------------------------------


def remove_conflicting_labels(df: pd.DataFrame) -> pd.DataFrame:
    grp = df.groupby(["pert_id", "gene_symbol"])["label"]
    consistent = grp.transform(lambda x: x.nunique() == 1)
    before = len(df)
    df = df[consistent].copy()
    log.info("Removed conflicting labels: %d -> %d rows", before, len(df))
    return df


# ---------------------------------------------------------------------------
# PyTorch training loop
# ---------------------------------------------------------------------------


def _run_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer | None,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float]:
    """One training or evaluation epoch. Returns (avg_loss, accuracy)."""
    training = optimizer is not None
    model.train(training)

    total_loss = 0.0
    correct = 0
    total = 0

    with torch.set_grad_enabled(training):
        for Xc, Xg, labels, weights in loader:
            Xc = Xc.to(device=device, dtype=torch.float32)
            Xg = Xg.to(device=device, dtype=torch.float32)
            labels = labels.to(device)
            weights = weights.to(device)

            logits = model(Xc, Xg)
            loss = (criterion(logits, labels) * weights).mean()

            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            total_loss += loss.item() * len(labels)
            preds = logits.argmax(dim=1)
            correct += (preds == labels).sum().item()
            total += len(labels)

    return total_loss / total, correct / total


def train_pytorch(
    Xc: np.ndarray,
    Xg: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    gene_dim: int,
    training_config: dict,
    device: torch.device,
) -> SignalForgeNet:
    """Train SignalForgeNet and return the best-val-loss checkpoint."""
    batch_size = training_config.get("batch_size", 512)
    lr = training_config.get("learning_rate_init", 1e-3)
    max_epochs = training_config.get("max_iter", 200)
    patience = training_config.get("patience", 15)
    random_state = training_config.get("random_state", 42)
    torch.manual_seed(random_state)

    dataset = TensorDataset(
        torch.from_numpy(Xc),
        torch.from_numpy(Xg),
        torch.from_numpy(y),
        torch.from_numpy(w),
    )

    train_loader = DataLoader(
        Subset(dataset, train_idx.tolist()),
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
    )
    val_loader = DataLoader(
        Subset(dataset, val_idx.tolist()),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )

    model = SignalForgeNet(compound_dim=MORGAN_BITS, gene_dim=gene_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )
    # reduction="none" so we multiply by per-sample weights manually
    criterion = nn.CrossEntropyLoss(reduction="none")

    best_val_loss = float("inf")
    best_state: dict = {}
    no_improve = 0

    for epoch in range(1, max_epochs + 1):
        tr_loss, tr_acc = _run_epoch(model, train_loader, optimizer, criterion, device)
        val_loss, val_acc = _run_epoch(model, val_loader, None, criterion, device)
        scheduler.step(val_loss)

        if epoch % 5 == 0 or epoch == 1:
            log.info(
                "Epoch %3d | tr_loss=%.4f tr_acc=%.4f | val_loss=%.4f val_acc=%.4f | lr=%.6f",
                epoch,
                tr_loss,
                tr_acc,
                val_loss,
                val_acc,
                optimizer.param_groups[0]["lr"],
            )

        if val_loss < best_val_loss - 1e-5:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                log.info("Early stopping at epoch %d (patience=%d)", epoch, patience)
                break

    model.load_state_dict(best_state)
    return model


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def train_deep(config: dict) -> dict:
    """Train SignalForgeNet on LINCS parquet. Returns manifest dict."""
    dataset_config = config["dataset"]
    training_config = config["training"]
    artifact_config = config["artifacts"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("Device: %s", device)

    # Load parquet
    input_path = Path(dataset_config["input_path"])
    log.info("Loading dataset from %s", input_path)
    df = pd.read_parquet(input_path)
    log.info(
        "Loaded %d rows, %d compounds, %d genes, cell lines: %s",
        len(df),
        df["pert_id"].nunique(),
        df["gene_symbol"].nunique(),
        df["cell_id"].unique().tolist() if "cell_id" in df.columns else "?",
    )

    df = remove_conflicting_labels(df)

    feature_dtype_name = training_config.get("feature_dtype", "float16")
    feature_dtype = np.float16 if str(feature_dtype_name).lower() == "float16" else np.float32
    log.info("Building feature matrix (Morgan 2048 + GO %d) as %s...", GO_DIMS, feature_dtype_name)
    Xc, Xg, y, w, kept_indices = build_feature_matrix(df, feature_dtype=feature_dtype)
    gene_dim = Xg.shape[1]
    kept_meta = df.loc[kept_indices, ["pert_id", "gene_symbol"]]
    groups = kept_meta["pert_id"].to_numpy()
    log.info(
        "Xc: %s  Xg: %s  label balance: up=%d down=%d",
        Xc.shape, Xg.shape, (y == 1).sum(), (y == 0).sum(),
    )

    random_state = training_config.get("random_state", 42)
    test_size = training_config.get("test_size", 0.15)
    val_frac = training_config.get("validation_fraction", 0.1)

    outer_gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_val_idx, test_idx = next(outer_gss.split(Xc, y, groups=groups))

    inner_groups = groups[train_val_idx]
    inner_test_size = val_frac / (1.0 - test_size)
    inner_gss = GroupShuffleSplit(n_splits=1, test_size=inner_test_size, random_state=random_state)
    inner_train_idx, inner_val_idx = next(
        inner_gss.split(Xc[train_val_idx], y[train_val_idx], groups=inner_groups)
    )

    train_idx = train_val_idx[inner_train_idx]
    val_idx = train_val_idx[inner_val_idx]

    y_train = y[train_idx]
    y_val = y[val_idx]
    y_test = y[test_idx]
    log.info("Split: train=%d  val=%d  test=%d", len(train_idx), len(val_idx), len(test_idx))
    log.info(
        "Compound-level split: train=%d compounds, val=%d compounds, test=%d compounds",
        int(pd.Series(groups[train_idx]).nunique()),
        int(pd.Series(groups[val_idx]).nunique()),
        int(pd.Series(groups[test_idx]).nunique()),
    )

    # Optional scaling remains disabled by default for full-data CPU runs to avoid
    # full-matrix memory expansion and duplicate copies.
    use_scaler = bool(training_config.get("use_scaler", False))
    scaler_c = None
    scaler_g = None
    if use_scaler:
        raise RuntimeError(
            "use_scaler=true is not supported in full-data memory-safe mode; set use_scaler=false"
        )

    y = y.astype(np.int64, copy=False)

    model = train_pytorch(
        Xc, Xg, y, w,
        train_idx, val_idx,
        gene_dim=gene_dim,
        training_config=training_config,
        device=device,
    )

    # Evaluate on held-out test set
    model.eval()
    test_dataset = TensorDataset(
        torch.from_numpy(Xc),
        torch.from_numpy(Xg),
        torch.from_numpy(y),
    )
    test_loader = DataLoader(
        Subset(test_dataset, test_idx.tolist()),
        batch_size=training_config.get("batch_size", 512),
        shuffle=False,
        num_workers=0,
    )
    preds_all: list[np.ndarray] = []
    with torch.no_grad():
        for Xc_b, Xg_b, _ in test_loader:
            logits = model(
                Xc_b.to(device=device, dtype=torch.float32),
                Xg_b.to(device=device, dtype=torch.float32),
            )
            preds_all.append(logits.argmax(dim=1).cpu().numpy())
    y_pred = np.concatenate(preds_all)

    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    log.info("Test accuracy: %.4f", accuracy)
    log.info(
        "Classification report:\n%s",
        classification_report(y_test, y_pred, zero_division=0),
    )

    # Save model + scalers bundle
    model_path = Path(artifact_config["model_path"])
    model_path.parent.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "state_dict": model.state_dict(),
            "compound_dim": MORGAN_BITS,
            "gene_dim": gene_dim,
            "scaler_c": scaler_c,
            "scaler_g": scaler_g,
        },
        model_path,
    )
    log.info("Saved model to %s", model_path)

    manifest = {
        "model_version": "signalforge-dual-encoder-v1",
        "algorithm": (
            f"SignalForgeNet dual-encoder | "
            f"compound=Morgan-{MORGAN_BITS} | gene=GO-{gene_dim} | "
            f"zscore-threshold=3.0 | noise-filtered"
        ),
        "pytorch_version": torch.__version__,
        "artifact_path": str(model_path),
        "compound_dim": MORGAN_BITS,
        "gene_dim": gene_dim,
        "n_train": int(len(train_idx)),
        "n_val": int(len(val_idx)),
        "n_test": int(len(test_idx)),
        "n_compounds": int(kept_meta["pert_id"].nunique()),
        "n_genes": int(kept_meta["gene_symbol"].nunique()),
        "metrics": report,
        "accuracy": float(accuracy),
        "macro_f1": float(report.get("macro avg", {}).get("f1-score", 0.0)),
        "status": "trained",
    }

    manifest_path = Path(
        artifact_config.get("manifest_path", "artifacts/manifests/deep_latest.json")
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log.info(
        "Manifest written: accuracy=%.4f  macro_f1=%.4f",
        accuracy, manifest["macro_f1"],
    )

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import yaml

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("configs/deep_lincs.yaml")
    config_path = config_path.resolve()
    config_root = config_path.parent.parent  # ml/ directory

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # Resolve relative paths in config against the ml/ directory.
    dataset_input = Path(cfg["dataset"]["input_path"])
    if not dataset_input.is_absolute():
        cfg["dataset"]["input_path"] = str(config_root / dataset_input)

    for key in ("model_path", "manifest_path"):
        if key in cfg.get("artifacts", {}):
            p = Path(cfg["artifacts"][key])
            if not p.is_absolute():
                cfg["artifacts"][key] = str(config_root / p)

    m = train_deep(cfg)
    print(f"\nAccuracy : {m['accuracy']:.4f}")
    print(f"Macro F1 : {m['macro_f1']:.4f}")
    print(f"N train  : {m['n_train']}")
    print(f"Compounds: {m['n_compounds']}")
    print(f"Model    : {m['artifact_path']}")
