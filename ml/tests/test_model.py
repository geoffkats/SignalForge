"""
test_model.py
-------------
Unit tests for the SignalForgeNet dual-encoder architecture.
"""
import numpy as np
import pytest
import torch

from signalforge_ml.model import SignalForgeNet


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def model_default():
    """Default dims: compound=2048, gene=1107."""
    return SignalForgeNet()


@pytest.fixture()
def model_small():
    """Smaller dims for fast tests."""
    return SignalForgeNet(compound_dim=64, gene_dim=32)


# ---------------------------------------------------------------------------
# Architecture shape tests
# ---------------------------------------------------------------------------

class TestSignalForgeNetShapes:
    def test_forward_output_shape(self, model_default):
        B = 16
        Xc = torch.randn(B, 2048)
        Xg = torch.randn(B, 1107)
        logits = model_default(Xc, Xg)
        assert logits.shape == (B, 2), f"Expected (16, 2), got {logits.shape}"

    def test_forward_single_sample(self, model_default):
        model_default.eval()
        Xc = torch.randn(1, 2048)
        Xg = torch.randn(1, 1107)
        logits = model_default(Xc, Xg)
        assert logits.shape == (1, 2)

    def test_forward_small_model(self, model_small):
        B = 8
        Xc = torch.randn(B, 64)
        Xg = torch.randn(B, 32)
        logits = model_small(Xc, Xg)
        assert logits.shape == (B, 2)

    def test_predict_proba_sums_to_one(self, model_small):
        model_small.eval()
        Xc = torch.randn(10, 64)
        Xg = torch.randn(10, 32)
        probs = model_small.predict_proba(Xc, Xg)
        sums = probs.sum(dim=1)
        assert torch.allclose(sums, torch.ones(10), atol=1e-5)

    def test_compound_dim_stored(self):
        m = SignalForgeNet(compound_dim=512, gene_dim=100)
        assert m.compound_dim == 512
        assert m.gene_dim == 100


# ---------------------------------------------------------------------------
# Gradient / training sanity
# ---------------------------------------------------------------------------

class TestSignalForgeNetTraining:
    def test_parameters_update_on_backward(self, model_small):
        model_small.train()
        optimizer = torch.optim.Adam(model_small.parameters(), lr=1e-3)
        criterion = torch.nn.CrossEntropyLoss()

        Xc = torch.randn(8, 64)
        Xg = torch.randn(8, 32)
        labels = torch.randint(0, 2, (8,))

        before = [p.clone().detach() for p in model_small.parameters()]
        logits = model_small(Xc, Xg)
        loss = criterion(logits, labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        any_changed = any(
            not torch.equal(a, b)
            for a, b in zip(before, model_small.parameters())
        )
        assert any_changed, "No parameters updated after backward pass"

    def test_loss_decreases_over_steps(self, model_small):
        """Loss should trend downward over 30 steps on a fixed batch."""
        model_small.train()
        optimizer = torch.optim.Adam(model_small.parameters(), lr=5e-3)
        criterion = torch.nn.CrossEntropyLoss()

        torch.manual_seed(0)
        Xc = torch.randn(32, 64)
        Xg = torch.randn(32, 32)
        labels = torch.randint(0, 2, (32,))

        losses = []
        for _ in range(30):
            logits = model_small(Xc, Xg)
            loss = criterion(logits, labels)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            losses.append(loss.item())

        assert losses[-1] < losses[0], (
            f"Loss did not decrease: start={losses[0]:.4f}  end={losses[-1]:.4f}"
        )

    def test_eval_mode_deterministic(self, model_small):
        model_small.eval()
        Xc = torch.randn(4, 64)
        Xg = torch.randn(4, 32)
        with torch.no_grad():
            out1 = model_small(Xc, Xg)
            out2 = model_small(Xc, Xg)
        assert torch.equal(out1, out2)


# ---------------------------------------------------------------------------
# State dict save / load round-trip
# ---------------------------------------------------------------------------

class TestSignalForgeNetPersistence:
    def test_save_load_roundtrip(self, tmp_path, model_small):
        model_small.eval()
        Xc = torch.randn(4, 64)
        Xg = torch.randn(4, 32)

        with torch.no_grad():
            logits_before = model_small(Xc, Xg)

        ckpt = tmp_path / "model.pt"
        torch.save(model_small.state_dict(), ckpt)

        loaded = SignalForgeNet(compound_dim=64, gene_dim=32)
        loaded.load_state_dict(torch.load(ckpt, map_location="cpu"))
        loaded.eval()

        with torch.no_grad():
            logits_after = loaded(Xc, Xg)

        assert torch.allclose(logits_before, logits_after, atol=1e-6)
