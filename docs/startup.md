# Startup screen

The frontend waits for the backend setup-status endpoint before performing the normal authentication check. This prevents a container that is still waiting for PostgreSQL or applying migrations from appearing to be logged out.

The startup screen reports descriptive phases: PostgreSQL/backend unavailable, database startup, migrations, and API startup. These are not migration percentages; the frontend cannot know exact migration progress until the API is serving requests.

The retry loop backs off to a maximum of three seconds and continues until the backend responds. Once it does, normal authentication and routing begin.
