FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

COPY --chown=appuser:appuser analytics ./analytics
COPY --chown=appuser:appuser backend ./backend
COPY --chown=appuser:appuser config ./config
COPY --chown=appuser:appuser database ./database
COPY --chown=appuser:appuser pipelines ./pipelines
COPY --chown=appuser:appuser scripts ./scripts
COPY --chown=appuser:appuser sql ./sql
RUN mkdir -p data/raw data/exports logs && chown -R appuser:appuser data logs

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
