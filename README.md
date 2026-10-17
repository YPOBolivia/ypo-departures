# YPO Bolivia · Departures

The season's experiences as an airport departures board, with stage emails that wait for approval.

- `/` board (shared password), `/flight/<code>` flight page, `/flight/<code>/poster` downloadable poster
- `/admin` control tower (admin password), `/admin/outbox` emails waiting for approval

## Stack
FastAPI on Render (free) · Postgres on Neon (schema `departures`) · email through a Google Apps Script
running inside events@ypobolivia.com (Render's free plan blocks SMTP).

## Environment variables (Render)
| Key | What |
|---|---|
| DATABASE_URL | Neon connection string |
| SECRET_KEY | random string for session cookies |
| BOARD_PASSWORD | shared password for members & spouses |
| ADMIN_PASSWORD | Chapter Manager password |
| MAIL_WEBHOOK_URL | Apps Script web app URL |
| MAIL_SECRET | same value as the script's SECRET property |
| BASE_URL | public URL, e.g. https://ypo-departures.onrender.com |
| PYTHON_VERSION | 3.12.6 |

Build: `pip install -r requirements.txt` · Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`

## Emails
Moving a chapter flight to Day Chair on board, Date confirmed, Boarding or Final call prepares an email
in the Outbox. Nothing is sent until it is approved there. Regional flights never send emails.

## Data
`schema.sql` creates the tables; `make_seed.py` builds `seed.sql` from the FY26-27 Learning Calendar.
