from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PerturbationRecord:
    perturbation_id: str
    compound_id: str
    compound_name: str
    smiles: str
    gene_symbol: str
    regulation_label: str