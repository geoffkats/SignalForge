# SignalForge Training Incident Log (2026-05-02)

## Purpose
This document records what happened during the long LINCS training session, including failures, root causes, fixes, and final outcomes. Keep this file as an operational runbook for future full-data runs.

## Environment Snapshot
- OS: Windows
- Workspace: C:/Users/User/Desktop/backdoor/ai-project
- Main config: ml/configs/deep_lincs.yaml
- Dataset: ml/data/processed/lincs_multicell_full.parquet
- Dataset rows loaded: 1,727,650
- Training hardware: CPU-only

## User Requirement (Sequence)
- Run full dual-encoder training.
- After encoder completion, run full-fidelity RF.
- Do not skip the second step.

## Timeline Summary
- Ingest completion was verified.
- RF baseline was run first, but required runtime/memory tuning to finish reliably.
- Deep training was started and repeatedly exited before completion.
- Deep training code was refactored for memory safety.
- Deep training then completed successfully.
- RF full-fidelity run was auto-triggered after encoder completion.

## Major Issues, Root Causes, and Fixes

### 1) Path Resolution Failures from Workspace Root
- Symptom: Scripts failed to find config-relative dataset/artifact files.
- Root cause: Relative paths depended on current working directory.
- Fix:
  - Added config-root path resolution in CLI entrypoints.
  - In both deep and RF scripts, relative paths are resolved against ml/ directory derived from config path.
- Files updated:
  - ml/signalforge_ml/train_deep.py
  - ml/signalforge_ml/train_rf_lincs.py

### 2) RF OOM / Extremely Slow Runtime on Full Data
- Symptom: RF run appeared stuck for hours or exhausted resources.
- Root cause: Oversized dense feature creation and heavy RF defaults on very large training set.
- Fix:
  - Added practical RF controls via config-driven settings.
  - Performed split before feature build.
  - Built features separately for train and test partitions.
- Applied settings for practical baseline:
  - rf_max_rows: 200000 (default baseline)
  - rf_n_estimators: 200
  - rf_max_depth: 30
  - rf_min_samples_leaf: 2
  - rf_max_samples: 0.7
- Full-fidelity profile later set higher in config for post-encoder run.

### 3) Deep Training Exited Without Python Traceback
- Symptom: Process terminated after dataset load or feature prep with no explicit exception.
- Root cause: Memory pressure and hidden process termination during large in-memory operations.
- Fix set A (first pass):
  - Reworked feature build to two-pass approach.
  - Pass 1 identifies valid rows and counts.
  - Pass 2 preallocates arrays and fills sequentially.
  - Stored features as float16.
  - Disabled scaler by default for full-data CPU runs.
- Files updated:
  - ml/signalforge_ml/train_deep.py

### 4) Deep Training Still Vulnerable to Large Split Copies
- Symptom: Additional risk remained because train/val/test arrays were materialized as full copies.
- Root cause: `X[train_idx]`, `X[val_idx]`, `X[test_idx]` creates large duplicated arrays.
- Fix set B (second pass):
  - Refactored training/evaluation to use index-based `Subset` loaders from one shared tensor dataset.
  - Removed large split-copy allocations.
  - Updated feature matrix return metadata to index-based kept rows.
  - Preserved CPU-safe casting in epoch loop.
- Files updated:
  - ml/signalforge_ml/train_deep.py

### 5) Duplicate Python Processes Causing Confusion
- Symptom: Two python processes appeared for the same run.
- Root cause:
  - In early runs, actual duplicate launches occurred from different runtimes.
  - In later runs, process pair was parent/child from one launch.
- Fix:
  - Killed true duplicate idle processes when found.
  - Verified parent-child relations before stopping anything.
  - Standardized launches via the venv command path and explicit PYTHONPATH.

### 6) Auto-Trigger Flow Missed RF After Failed Deep Run
- Symptom: Watcher exited with "Deep manifest missing" and did not start RF.
- Root cause: Deep process exited before writing trained manifest.
- Fix:
  - Re-ran with improved deep memory behavior.
  - Kept watcher logic: only start RF if deep manifest exists and status is trained.

## Config Updates Applied
File: ml/configs/deep_lincs.yaml
- Added deep stability settings:
  - training.feature_dtype: float16
  - training.use_scaler: false
- Added full-fidelity RF settings for post-encoder run:
  - training.rf_max_rows: 500000
  - training.rf_n_estimators: 500
  - training.rf_max_depth: 30
  - training.rf_min_samples_leaf: 2
  - training.rf_max_samples: 0.7

## Commands Used for Reliable Launch
- Deep run:
  - `$env:PYTHONPATH = "C:\Users\User\Desktop\backdoor\ai-project\ml"; C:\Users\User\Desktop\backdoor\ai-project\ml\.venv\Scripts\python.exe -m signalforge_ml.train_deep C:\Users\User\Desktop\backdoor\ai-project\ml\configs\deep_lincs.yaml`
- Chained deep then RF:
  - `$env:PYTHONPATH = "C:\Users\User\Desktop\backdoor\ai-project\ml"; $cfg = "C:\Users\User\Desktop\backdoor\ai-project\ml\configs\deep_lincs.yaml"; C:\Users\User\Desktop\backdoor\ai-project\ml\.venv\Scripts\python.exe -m signalforge_ml.train_deep $cfg; if ($LASTEXITCODE -eq 0) { C:\Users\User\Desktop\backdoor\ai-project\ml\.venv\Scripts\python.exe -m signalforge_ml.train_rf_lincs $cfg }`

## First Encoder Final Results (Successful)
- Removed conflicting labels: 1727650 -> 1659055 rows
- Feature matrix kept: 1630296 rows
- Dropped for no-compound: 15023
- Dropped for no-gene: 13736
- Split:
  - train: 1226168
  - val: 157731
  - test: 246397
- Early stopping: epoch 24
- Test accuracy: 0.8736
- Macro F1: 0.8733
- Artifacts:
  - Model: ml/artifacts/models/deep_dual_encoder.pt
  - Manifest: ml/artifacts/manifests/deep_latest.json

## Operational Lessons
- Full-data CPU training can be stable if memory copies are minimized.
- Index-based dataloading is safer than materializing split arrays for this dataset size.
- Keep scaler off for full-data CPU runs unless system memory is upgraded.
- Always verify whether dual python processes are true duplicates or parent-child before killing.
- Use watcher logic to enforce encoder-then-RF sequencing.

## Next Steps for Team
- Keep this file updated after each long run.
- Add periodic progress logs (elapsed time per epoch) if more visibility is needed.
- Consider optional checkpoint resume support for very long CPU training jobs.
- Consider moving heavy runs to a GPU node for faster turnaround.
