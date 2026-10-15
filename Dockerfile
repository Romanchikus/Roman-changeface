FROM nvidia/cuda:13.0.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/uv-python \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl ffmpeg libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY facefusion/requirements.txt /tmp/facefusion-requirements.txt
RUN grep -v '^onnxruntime' /tmp/facefusion-requirements.txt > /tmp/facefusion-deps.txt \
    && uv pip install --python /app/.venv/bin/python -r /tmp/facefusion-deps.txt "onnxruntime-gpu[cuda,cudnn]==1.30.0"

COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
COPY facefusion ./facefusion
COPY scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
COPY scripts/facefusion-headless.sh /app/facefusion-headless.sh
RUN chmod +x /app/docker-entrypoint.sh /app/facefusion-headless.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
