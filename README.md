# CodeAtlas

ACM/OI 竞赛私人知识库 AI 助教平台。

## Phase 0

```powershell
Copy-Item .env.example .env
docker compose up -d
```

后端：`cd backend; pip install -e ".[dev]"; uvicorn app.main:app --reload --port 8000`  
前端：`cd frontend; npm install; npm run dev`

访问 `http://localhost:3000`、`http://localhost:8000/docs` 和 MinIO 控制台 `http://localhost:9001`。
详见 [docs/development-baseline.md](docs/development-baseline.md)。
