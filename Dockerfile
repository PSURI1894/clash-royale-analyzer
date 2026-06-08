# Backend API image. Build from the repo root:  docker build -t cr-helper-api .
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Install the backend (editable keeps cr_helper at /app/backend so settings.data_dir
# resolves to /app/data). Deps are layer-cached on pyproject.
COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/cr_helper backend/cr_helper
RUN pip install -e "./backend[postgres]"

# Runtime data: curated edges, strategy corpus, scraped fixture.
COPY data data

EXPOSE 8000
# Override DATABASE_URL to the Postgres service in production (see docker-compose.yml).
CMD ["python", "-m", "uvicorn", "cr_helper.main:app", "--host", "0.0.0.0", "--port", "8000"]
