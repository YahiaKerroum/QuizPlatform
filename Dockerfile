FROM python:3.13-slim

WORKDIR /app

# Install deps first (layer cache)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# App code
COPY backend/ backend/

# ML model (service falls back to rule-based selection if absent)
COPY ["ML NOTEBOOKS/models/best_model_single_module.pkl", "ML NOTEBOOKS/models/best_model_single_module.pkl"]

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
