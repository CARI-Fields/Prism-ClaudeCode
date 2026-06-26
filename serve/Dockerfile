FROM python:3.11-slim
WORKDIR /app

COPY serve/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY serve/ ./serve/
COPY analysis/__init__.py ./analysis/__init__.py
COPY analysis/report_variants.py ./analysis/report_variants.py
COPY data/processed/ ./data/processed/

ENV DATA_DIR=/app/data/processed
EXPOSE 7860
CMD ["uvicorn", "serve.app:app", "--host", "0.0.0.0", "--port", "7860"]
