FROM docker.m.daocloud.io/library/python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml .
RUN pip install --no-cache-dir --timeout 120 --retries 5 --no-build-isolation --index-url https://mirrors.cloud.tencent.com/pypi/simple/ .
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

