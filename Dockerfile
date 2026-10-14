# One container: FastAPI serves the API at /api and the built web app at /.
# Run: docker compose up --build, then open http://localhost:8008 (keys come from .env; see .env.example).

FROM node:24-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/
RUN uv sync --project backend --frozen --no-dev --no-install-project
COPY backend/src backend/src
RUN uv sync --project backend --frozen --no-dev
# The recorded Arena the app replays by default (backend/scripts/record_arena.py).
COPY evidence/runs evidence/runs
COPY --from=web /web/dist web/dist
ENV WEB_DIST=/app/web/dist PATH="/app/backend/.venv/bin:$PATH"
EXPOSE 8008
CMD ["uvicorn", "--factory", "marginarena.api:create_app", "--host", "0.0.0.0", "--port", "8008"]
