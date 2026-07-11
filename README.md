# CareerRoadmap AI

## What changed from the original version

**Security**
- `SECRET_KEY` and `DEBUG` no longer have unsafe defaults — the app now refuses to start in production without a real secret key, and debug mode is tied to `FLASK_ENV`.
- Added CSRF protection (`Flask-WTF`) on all forms and JSON `fetch()` calls.
- Added rate limiting (`Flask-Limiter`) on login, register, and the chat API to blunt brute-force/spam attempts.
- Secure, HTTP-only, `SameSite` cookies (enforced once `FLASK_ENV=production` and you're behind HTTPS).
- Custom 404/500 pages instead of leaking stack traces.
- Fixed a real bug: `recommendations.html`'s "Add to Learning" button called `/add_learning`, which didn't exist — it's now implemented.

**Real AI**
- The chatbot and roadmap generator now call the Anthropic API (`claude-sonnet-4-6`) when `ANTHROPIC_API_KEY` is set, producing dynamic, personalized responses instead of picking from ~10 hardcoded phrases or 4 fixed roadmap templates.
- If no API key is set, both fall back gracefully to the original rule-based logic — nothing breaks in local/demo use.

**Deployment**
- `wsgi.py` + `Dockerfile` + `docker-compose.yml` to run behind Gunicorn + Postgres instead of the Flask dev server + SQLite.
- `.env.example` documents every required environment variable; the real `.env` is git-ignored.

## Local development

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set SECRET_KEY, set FLASK_ENV=development, optionally ANTHROPIC_API_KEY
python app.py
```

## Running with Docker (recommended for anything real)

```bash
cp .env.example .env
# Fill in SECRET_KEY, POSTGRES_PASSWORD, ANTHROPIC_API_KEY
docker compose up --build
```

The app will be on `http://localhost:8000`, backed by Postgres instead of SQLite.

## Deploying for real users

Easiest options, roughly in order of simplicity:
1. **Render** or **Railway** — connect this repo, add a managed Postgres, set the env vars from `.env.example`, done. They handle HTTPS for you.
2. **Fly.io** — `fly launch` picks up the Dockerfile automatically.
3. Any VPS (DigitalOcean, etc.) — run via `docker compose up -d`, put Nginx or Caddy in front for TLS.

Whichever you choose, set these environment variables on the host:
- `SECRET_KEY` (random, 32+ bytes)
- `DATABASE_URL` (Postgres connection string)
- `FLASK_ENV=production`
- `ANTHROPIC_API_KEY` (for real AI features)

## Still worth doing before real users touch this

- Email verification on signup (currently `is_verified` is set `True` unconditionally).
- A "forgot password" flow.
- Automated tests (pytest) for auth and the roadmap/chat endpoints.
- Scheduled Postgres backups.
- An error-tracking service (e.g. Sentry) wired into the new logger.
