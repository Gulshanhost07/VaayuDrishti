FROM python:3.11-slim AS base

ARG INSTALL_ML=0
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY requirements.txt ./
RUN pip install -r requirements.txt

RUN if [ "$INSTALL_ML" = "1" ]; then \
      pip install --extra-index-url https://download.pytorch.org/whl/cpu \
        sentence-transformers transformers torch; \
    fi

COPY . .

RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
