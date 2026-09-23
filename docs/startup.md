# Startup screen

The frontend waits for the backend setup-status endpoint before running the normal authentication check. A backend that is still waiting for PostgreSQL or applying migrations therefore does not look like a logged-out user.

The screen reports descriptive startup phases for backend/database availability, migrations, and API readiness. These are explanatory phases, not measured progress percentages.

The retry loop backs off to a maximum of three seconds and continues until the backend responds. Once the endpoint responds successfully, normal authentication and routing begin.

## Manual validation

- Start the frontend before the backend and confirm the startup screen remains visible.
- Start PostgreSQL/backend and confirm the screen progresses and then disappears.
- Restart the backend during startup and confirm retry continues.
- Confirm a normal API/application error is not incorrectly treated as endless startup.
- Confirm a fresh installation reaches setup rather than login.
