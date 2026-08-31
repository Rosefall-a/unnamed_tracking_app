# running the api
docker compose down -v
docker compose up -d build
docker compose run -rm app


# Database updates

```bash
docker compose exec backend alembic -c alembic.ini revision --autogenerate -m "your changes here eg add playtime to game table"
```