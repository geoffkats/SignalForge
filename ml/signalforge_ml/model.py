"""
model.py  —  SignalForge dual-encoder neural network
------------------------------------------------------
Architecture (matches the plan from design notes):

  compound_encoder: Linear(2048→256) + BN + ReLU + Dropout(0.3)
  gene_encoder:     Linear(gene_dim→256) + BN + ReLU + Dropout(0.3)
  classifier:       Linear(512→256) + BN + ReLU + Dropout(0.3)
                 →  Linear(256→128) + BN + ReLU + Dropout(0.2)
                 →  Linear(128→2)

Separate encoders allow:
 - Independent pretraining on ChEMBL / expression data later
 - Cell-line adaptation by fine-tuning only the classifier head
 - SHAP / attribution on each branch independently
"""
from __future__ import annotations

import torch
import torch.nn as nn


class SignalForgeNet(nn.Module):
    """
    Dual-encoder MLP for compound–gene up/down regulation prediction.

    Parameters
    ----------
    compound_dim : int
        Size of compound input vector (default 2048, Morgan FP).
    gene_dim : int
        Size of gene input vector (default 1107, GO terms).
    enc_dim : int
        Output dim of each encoder branch before fusion (default 256).
    """

    def __init__(
        self,
        compound_dim: int = 2048,
        gene_dim: int = 1107,
        enc_dim: int = 256,
    ) -> None:
        super().__init__()

        self.compound_dim = compound_dim
        self.gene_dim = gene_dim

        self.compound_encoder = nn.Sequential(
            nn.Linear(compound_dim, enc_dim),
            nn.BatchNorm1d(enc_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
        )

        self.gene_encoder = nn.Sequential(
            nn.Linear(gene_dim, enc_dim),
            nn.BatchNorm1d(enc_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
        )

        self.classifier = nn.Sequential(
            nn.Linear(enc_dim * 2, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 2),
        )

    def forward(self, compound_x: torch.Tensor, gene_x: torch.Tensor) -> torch.Tensor:
        c = self.compound_encoder(compound_x)
        g = self.gene_encoder(gene_x)
        joint = torch.cat([c, g], dim=1)
        return self.classifier(joint)

    def predict_proba(self, compound_x: torch.Tensor, gene_x: torch.Tensor) -> torch.Tensor:
        """Softmax probabilities — (N, 2)."""
        logits = self.forward(compound_x, gene_x)
        return torch.softmax(logits, dim=1)
