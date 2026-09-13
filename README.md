# Running the API

docker compose down -v
docker compose up -d --build
docker compose run --rm backend

# Backend checks
cd src/backend
mypy --config-file pyproject.toml src
pylint --rcfile=pyproject.toml src

# Frontend checks
cd /src/frontend
npm run lint
npm run format # if this fails run npm run format:fix
npm run typecheck

## Recommended VS Code extensions
- Ruff by charliermarsh

# Database updates

```bash
docker compose exec backend alembic -c alembic.ini revision --autogenerate -m "your changes here eg add playtime to game table"
```

## Security

This project is not currently hardened for direct public-internet exposure. Keep the API behind an appropriate network boundary and do not expose it directly to the public internet.
