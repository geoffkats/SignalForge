FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install ML inference deps only (no torch/CUDA/cmapPy/pyarrow)
COPY ml/pyproject.toml /ml/pyproject.toml
COPY ml/signalforge_ml /ml/signalforge_ml
# Feature files required by signalforge_ml.features at inference time
COPY ml/data/raw/deepcop/go_fingerprints.csv /ml/data/raw/deepcop/go_fingerprints.csv
COPY ml/data/raw/deepcop/LNCAPcorr_cols.csv /ml/data/raw/deepcop/LNCAPcorr_cols.csv
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --no-deps -e /ml \
    && pip install --no-cache-dir "joblib>=1.4,<2.0" "numpy>=2.2,<3.0" "pandas>=2.2,<3.0" "rdkit>=2024.9.6" "scikit-learn>=1.7,<1.8"

# Install backend
COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/app /app/app

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
