# SafeSphere AI Backend

FastAPI backend with MongoDB + JWT authentication for:
- User auth (`/register`, `/login`, `/profile`)
- Emergency flow (`/sos`, `/location-update`, `/stop`)
- Missing person flow (`/report-missing`, `/missing-list`, `/seen-report`)
- Notifications (`/notifications`, `/add-notification`, `/mark-read`)

## Local Development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

API docs:
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Production Deploy (Docker, Recommended)

1. Create `.env` from `.env.example` and set real values:
- `JWT_SECRET_KEY`: strong random secret
- `CORS_ORIGINS`: frontend domains (comma-separated)
- `TRUSTED_HOSTS`: API domain(s) (comma-separated)

2. Start production stack:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

3. Check status and logs:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api
```

4. Stop:

```bash
docker compose -f docker-compose.prod.yml down
```

## Production Deploy (Systemd + Nginx, Optional)

1. Put project at `/opt/safesphere_backend`, create virtualenv, install dependencies.
2. Copy `deploy/safesphere-api.service` to `/etc/systemd/system/`.
3. Copy `deploy/nginx.conf` to `/etc/nginx/sites-available/safesphere` and enable it.
4. Run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable safesphere-api
sudo systemctl start safesphere-api
sudo systemctl restart nginx
```

## Health Endpoint

- `GET /healthz`

## Deploy on Render

1. Push this repo to GitHub/GitLab.
2. Create MongoDB on Atlas (recommended) and copy connection string.
3. In Render Dashboard, click `New +` -> `Blueprint`, connect repo, deploy using `render.yaml`.
4. In Render service env vars, set these required secrets:
- `JWT_SECRET_KEY`
- `MONGO_URI` (Atlas URI)
- `CORS_ORIGINS` (your frontend domain(s), comma-separated)
- `TRUSTED_HOSTS` (your Render domain + custom domain, comma-separated)
5. After deploy, open:
- `https://<your-render-service>/healthz`
- `https://<your-render-service>/docs`
