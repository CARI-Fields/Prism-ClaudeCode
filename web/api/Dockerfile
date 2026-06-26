FROM python:3.11-slim
WORKDIR /app

COPY web/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY web/__init__.py ./web/__init__.py
COPY web/api/ ./web/api/
COPY analysis/__init__.py ./analysis/__init__.py
COPY analysis/report_variants.py ./analysis/report_variants.py

# Data is NOT baked into this (public) image — it is pulled at startup from a
# private HF Dataset via the HF_DATASET_REPO + HF_ACCESS_TOKEN Space secrets.
ENV DATA_DIR=/app/analysis/data/processed
EXPOSE 7860
CMD ["uvicorn", "web.api.app:app", "--host", "0.0.0.0", "--port", "7860"]
