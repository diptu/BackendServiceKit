FROM python:3.11.9-slim AS builder

RUN pip install uv

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --frozen --no-dev

COPY . .

# ---- runtime ----
FROM python:3.11.9-slim AS runtime

WORKDIR /app

COPY --from=builder /app /app
COPY --from=builder /root/.local /root/.local

ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["opentelemetry-instrument", \
     "uv", "run", "gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-"]
