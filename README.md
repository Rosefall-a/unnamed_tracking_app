# Game Tracking API

## 🚀 Getting Started

This project is a backend service for tracking game play sessions and associated data.

### Prerequisites
*   **Python:** Python 3.8+
*   **Database:** A running PostgreSQL instance (required by SQLAlchemy).
*   **Docker & Docker Compose:** Used to manage the environment dependencies.

### 🛠 System Dependencies (Critical)
If you plan to use any image processing features (e.g., uploading screenshots), you must install native system libraries, particularly **zlib**. Failure to do this will cause `Pillow` compilation errors.

*   **Windows:** Install Visual Studio Build Tools and ensure development headers are available for image libraries.
*   **Linux (Debian/Ubuntu):** `sudo apt-get update && sudo apt-get install -y zlib1g-dev libjpeg-dev`
*   **macOS:** `brew install zlib`

## ⚙️ Setup and Execution

### 1. Install Python Dependencies
Run this command to install all required libraries:
```bash
pip install -r src/requirements.txt
```

### 2. Database Initialization (Alembic)
First, generate the initial schema structure using Alembic. **Ensure your database container is running.**

```bash
# Generate a fresh revision script
docker compose exec app alembic -c app/alembic.ini revision --autogenerate -m "initial_schema"

# Apply all pending migrations to update the schema
docker compose exec app alembic upgrade head
```

### 3. Running the API
To build and run the services in detached mode:

```bash
docker compose up -d build
```

To manually run a single command or test endpoint against the service:

```bash
# Example: Run a health check on port 8000
docker compose run --rm app http://localhost:8000/health
```

### Data Integrity & Disaster Recovery
**WARNING:** Before performing *any* major schema migration (`alembic upgrade head`) or making significant data-altering changes to the application logic (e.g., new features that modify playtimes), you **MUST** perform a database dump and backup of the current state.

**Recommended Backup Procedure:**
1.  Identify your PostgreSQL credentials used by Docker Compose.
2.  Use `pg_dump` to create a full backup file:
    ```bash
    docker compose exec app pg_dump -U postgres > db_backup_$(date +%Y%m%d).sql
    ```
3.  Store this `.sql` file securely outside of the project directory.

Always restore from this dump before testing major changes to ensure rapid recovery if errors occur.