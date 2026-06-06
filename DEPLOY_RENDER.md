# Render Deployment Guide

## Files added for Render

- `requirements.txt` includes `gunicorn` and `whitenoise`.
- `build.sh` installs dependencies, collects static files, runs Django migrations, and bootstraps MongoDB indexes.
- `Procfile` starts the API with Gunicorn.
- `render.yaml` can be used as a Render Blueprint.

## Render build settings

Use these values if creating the service manually:

- **Runtime:** Python
- **Build command:** `bash build.sh`
- **Start command:** `gunicorn village.wsgi:application --bind 0.0.0.0:$PORT`

## Required Render environment variables

Set these in Render dashboard:

- `DEBUG=False`
- `DJANGO_SECRET_KEY=<strong-random-secret>`
- `JWT_SECRET_KEY=<strong-random-secret>`
- `ALLOWED_HOSTS=.onrender.com,your-api-name.onrender.com`
- `MONGODB_URI=<your MongoDB Atlas connection string>`
- `MONGODB_DATABASE=village_governance`
- `CLOUDINARY_CLOUD_NAME=<cloudinary cloud name>`
- `CLOUDINARY_API_KEY=<cloudinary api key>`
- `CLOUDINARY_API_SECRET=<cloudinary api secret>`
- `CORS_ALLOW_ALL_ORIGINS=False`
- `CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com`
- `CSRF_TRUSTED_ORIGINS=https://your-frontend-domain.com,https://your-api-name.onrender.com`
- `SECURE_SSL_REDIRECT=True`
- `SECURE_HSTS_SECONDS=31536000`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`
- `SECURE_HSTS_PRELOAD=True`

Optional first-deploy super admin bootstrap:

- `AUTO_BOOTSTRAP_BACKEND=True`
- `SUPER_ADMIN_EMAIL=owner@example.com`
- `SUPER_ADMIN_USERNAME=owner`
- `SUPER_ADMIN_PASSWORD=<strong-password>`

After the first successful deploy, set `AUTO_BOOTSTRAP_BACKEND=False`.

## Local deploy verification

```bash
pip install -r requirements.txt
python manage.py check --deploy
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py bootstrap_backend
gunicorn village.wsgi:application --bind 0.0.0.0:8000
```

On Windows local development, run the API with:

```powershell
python manage.py runserver
```

## Render CLI commands

```bash
npm install -g @render/cli
render login
render blueprint launch
```

If deploying manually from GitHub:

```bash
git add requirements.txt village/settings.py build.sh Procfile render.yaml .python-version .env.example DEPLOY_RENDER.md
git commit -m "prepare backend for render deployment"
git push origin master
```

Then create a new Render **Web Service** from the GitHub repo and use the build/start commands above.
