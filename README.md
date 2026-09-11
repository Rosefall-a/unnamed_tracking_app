# running the api
docker compose down -v
docker compose up -d build
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

## recommended vscode extensions
- ruff by charliermarsh

# Database updates

```bash
docker compose exec backend alembic -c alembic.ini revision --autogenerate -m "your changes here eg add playtime to game table"
```



# Security
yea no theres none please do not expose this to the web