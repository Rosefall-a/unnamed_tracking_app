# running the api
docker compose down -v
docker compose up -d build
docker compose run -rm app


# Database updates

```bash
docker compose exec app alembic -c app/alembic.ini revision --autogenerate -m "your changes here eg add playtime to game table"
```