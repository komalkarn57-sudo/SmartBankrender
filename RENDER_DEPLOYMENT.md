# Deploy SmartBank on Render

This project is a Flask app backed by MySQL. The included Render Blueprint config uses Gunicorn and reads database credentials from environment variables.

## 1. Upload the project to GitHub

1. Extract this ZIP on your computer.
2. Open the `SmartBank` folder and push its contents to a GitHub repository.
3. Do not upload your local `venv`, `.env` file, database passwords, or real customer data. This ZIP intentionally excludes the local virtual environment and `.git` folder.

## 2. Create a remote MySQL database

Render's web service does not provide a MySQL server at `localhost`. Create/use a MySQL database from a provider that permits remote connections. Keep its hostname, port, database name, username, and password available. Do not use your laptop's `localhost` as the production database host.

## 3. Create the Render web service

1. Sign in at https://render.com/ and choose **New + → Blueprint** (or create a **Web Service** connected to the repository).
2. If using Blueprint, Render can read `render.yaml`. If creating a Web Service manually, use:
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
3. In the service's **Environment** settings, set:
   - `SECRET_KEY`: a long, random secret value
   - `DB_HOST`: remote MySQL hostname
   - `DB_USER`: database username
   - `DB_PASSWORD`: database password
   - `DB_NAME`: database name
   - `DB_PORT`: database port, usually `3306`
4. Deploy the service.

## 4. Create the database tables

Open your remote MySQL provider's SQL editor or connect using a MySQL client and run the table definitions from `database.sql`. If your provider already created the database, do not run `CREATE DATABASE smartbank;` unless your account has permission and the database name is correct. Run the `CREATE TABLE` statements in that database instead.

## 5. Test

Open the root URL (`/`) to load the home page. The `/login` endpoint is a POST form endpoint, not a separate login page; submit the login form from the home page. If a page fails, check Render's **Logs** and verify the database environment variables and network access.

## Important

- Never commit database credentials or `SECRET_KEY` to GitHub.
- This is a student/demo banking application. Do not use real funds, real banking credentials, or sensitive customer information without a professional security review.
- A free web service may sleep when idle, and free database options/retention vary by provider. Confirm the current database provider's terms and backups before relying on it.
