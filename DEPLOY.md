# Deploy Aung Market

## Render

1. Sign in to Render.
2. Click `New` -> `Web Service`.
3. Connect the GitHub repo:

   `myatthuaung3305/aung_market`

4. Use these settings:
   - Branch: `main`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn wsgi:app`

5. Add environment variable:
   - `SECRET_KEY` = your own random secret

6. Deploy the service.

## Notes

- `render.yaml` is already included in the repo.
- The app is configured to read `PORT` and `SECRET_KEY` from the environment.
- SQLite works for simple demos, but PostgreSQL is a better long-term choice for production.
