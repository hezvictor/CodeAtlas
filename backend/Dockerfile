FROM python@sha256:d1e9ca7c4e78d1e8ecadb5d44bfc8e956e7a65b659a9950f569f243d72b326d0
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir --timeout 120 --retries 5 --index-url https://mirrors.cloud.tencent.com/pypi/simple/ uv==0.8.13 \
    && uv sync --frozen --no-dev --no-install-project --no-cache --default-index https://mirrors.cloud.tencent.com/pypi/simple/
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
