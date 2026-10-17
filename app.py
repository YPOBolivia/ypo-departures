"""YPO Bolivia Departures: the season's experiences as an airport board, with stage emails."""
import datetime as dt
import os
import secrets

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import db
import emails
import mailer
import views
from stages import MAIL_STAGES, STAGE_KEYS, GATE_BY_KEY, fmt_dates

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=os.environ["SECRET_KEY"],
                   max_age=60 * 60 * 24 * 30, same_site="lax", https_only=os.environ.get("HTTPS_ONLY", "1") == "1")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

MAX_PHOTO = 3 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


# ---------------------------------------------------------------- helpers

def role(request: Request):
    return request.session.get("role")


def go(url: str):
    return RedirectResponse(url, status_code=303)


def need(request: Request, admin=False):
    r = role(request)
    if not r:
        return go("/login")
    if admin and r != "admin":
        return go("/")
    return None


def flash(request: Request, msg: str):
    request.session["flash"] = msg


def pop_flash(request: Request) -> str:
    return request.session.pop("flash", "")


def base_url(request: Request) -> str:
    return os.environ.get("BASE_URL") or str(request.base_url)


def split_list(v: str):
    return [x.strip() for x in (v or "").split(",") if x.strip()]


def parse_date(v: str):
    v = (v or "").strip()
    return dt.date.fromisoformat(v) if v else None


def blank_none(v: str):
    v = (v or "").strip()
    return v or None


EVENTS_SQL = "SELECT * FROM events ORDER BY start_date NULLS LAST, id"


def prepare_email(event_id: int, stage: str, request: Request) -> bool:
    """Creates (or refreshes) the pending email for this flight and stage. Returns True if one is waiting."""
    ev = db.one("SELECT * FROM events WHERE id=%s", (event_id,))
    if not ev or stage not in MAIL_STAGES or ev["scope"] != "chapter" or not ev["mail_lists"]:
        return False
    subject, html, text = emails.render(ev, stage, base_url(request))
    existing = db.one("SELECT id FROM email_queue WHERE event_id=%s AND stage=%s AND status='pending'", (event_id, stage))
    if existing:
        db.run("UPDATE email_queue SET recipients=%s, subject=%s, html=%s, text=%s WHERE id=%s",
               (ev["mail_lists"], subject, html, text, existing["id"]))
    else:
        db.run("INSERT INTO email_queue (event_id, stage, recipients, subject, html, text) VALUES (%s,%s,%s,%s,%s,%s)",
               (event_id, stage, ev["mail_lists"], subject, html, text))
    return True


# ---------------------------------------------------------------- auth

@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if role(request):
        return go("/")
    return views.login_page()


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, password: str = Form(...)):
    admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    board_pw = os.environ.get("BOARD_PASSWORD", "")
    if admin_pw and secrets.compare_digest(password, admin_pw):
        request.session["role"] = "admin"
        return go("/admin")
    if board_pw and secrets.compare_digest(password, board_pw):
        request.session["role"] = "member"
        return go("/")
    return HTMLResponse(views.login_page("That password didn't work. Try again."), status_code=401)


@app.get("/logout")
@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return go("/login")


# ---------------------------------------------------------------- board & flights

@app.get("/", response_class=HTMLResponse)
def board(request: Request):
    if (r := need(request)):
        return r
    events = db.all(EVENTS_SQL)
    updated = db.one("SELECT max(updated_at) AS u FROM events")["u"]
    return views.board_page(events, role(request), updated)


def _flight(code: str):
    return db.one("SELECT * FROM events WHERE upper(code)=upper(%s)", (code,))


@app.get("/flight/{code}", response_class=HTMLResponse)
def flight(request: Request, code: str):
    if (r := need(request)):
        return r
    ev = _flight(code)
    if not ev:
        return go("/")
    return views.flight_page(ev, role(request))


@app.get("/flight/{code}/poster", response_class=HTMLResponse)
def poster(request: Request, code: str):
    if (r := need(request)):
        return r
    ev = _flight(code)
    if not ev:
        return go("/")
    return views.poster_page(ev, role(request))


@app.get("/media/{token}")
def media(token: str):
    # Public on purpose: email clients load the Day Chair photo without a session.
    # Tokens are long random strings, so photos can't be listed or guessed.
    row = db.one("SELECT mime, data FROM photos WHERE token=%s", (token,))
    if not row:
        return Response(status_code=404)
    return Response(bytes(row["data"]), media_type=row["mime"],
                    headers={"Cache-Control": "public, max-age=86400"})


# ---------------------------------------------------------------- control tower

@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    if (r := need(request, admin=True)):
        return r
    pending = db.one("SELECT count(*) AS n FROM email_queue WHERE status='pending'")["n"]
    return views.admin_page(db.all(EVENTS_SQL), pending, pop_flash(request))


@app.get("/admin/event/new", response_class=HTMLResponse)
def new_event_form(request: Request):
    if (r := need(request, admin=True)):
        return r
    return views.admin_event_page(None)


def _form_values(form) -> dict:
    status = form.get("status") or "scheduled"
    if status not in STAGE_KEYS:
        status = "scheduled"
    scope = "regional" if form.get("scope") == "regional" else "chapter"
    gate = GATE_BY_KEY.get(form.get("gate") or "all", GATE_BY_KEY["all"])
    score = blank_none(form.get("score"))
    score_n = blank_none(form.get("score_n"))
    return {
        "name": (form.get("name") or "").strip(),
        "status": status,
        "status_note": blank_none(form.get("status_note")),
        "previous_date": blank_none(form.get("previous_date")),
        "start_date": parse_date(form.get("start_date")),
        "end_date": parse_date(form.get("end_date")),
        "city": blank_none(form.get("city")),
        "connect_url": blank_none(form.get("connect_url")),
        "day_chair": blank_none(form.get("day_chair")),
        "champions": blank_none(form.get("champions")),
        "quote": blank_none(form.get("quote")),
        "audience_label": (form.get("audience_label") or "").strip(),
        "scope": scope,
        "chips": list(gate[2]),
        "tags": list(gate[3]),
        "mail_lists": list(gate[4]) if scope == "chapter" else [],
        "score": float(score.replace(",", ".")) if score else None,
        "score_n": int(score_n) if score_n else None,
    }


COLS = ["name", "status", "status_note", "previous_date", "start_date", "end_date", "city", "connect_url",
        "day_chair", "champions", "quote", "audience_label", "scope", "chips", "tags", "mail_lists", "score", "score_n"]


@app.post("/admin/event/new", response_class=HTMLResponse)
async def create_event(request: Request):
    if (r := need(request, admin=True)):
        return r
    form = await request.form()
    try:
        v = _form_values(form)
    except ValueError:
        return views.admin_event_page(None, error="Please check the dates and the score.")
    if not v["name"] or not v["audience_label"]:
        return views.admin_event_page(None, error="Name and audience are required.")
    last = db.one("SELECT max(substring(code from 4)::int) AS n FROM events WHERE code ~ '^YPO[0-9]+$'")["n"] or 2600
    code = f"YPO{last + 1}"
    cols = ", ".join(COLS + ["code"])
    ph = ", ".join(["%s"] * (len(COLS) + 1))
    row = db.one(f"INSERT INTO events ({cols}) VALUES ({ph}) RETURNING id", [v[c] for c in COLS] + [code])
    queued = prepare_email(row["id"], v["status"], request) if v["status"] in MAIL_STAGES else False
    flash(request, f"Flight {code} created." + (" Its email is waiting in the Outbox." if queued else ""))
    return go("/admin")


@app.get("/admin/event/{event_id}", response_class=HTMLResponse)
def edit_event_form(request: Request, event_id: int):
    if (r := need(request, admin=True)):
        return r
    ev = db.one("SELECT * FROM events WHERE id=%s", (event_id,))
    if not ev:
        return go("/admin")
    return views.admin_event_page(ev, pop_flash(request))


@app.post("/admin/event/{event_id}", response_class=HTMLResponse)
async def save_event(request: Request, event_id: int):
    if (r := need(request, admin=True)):
        return r
    old = db.one("SELECT * FROM events WHERE id=%s", (event_id,))
    if not old:
        return go("/admin")
    form = await request.form()
    try:
        v = _form_values(form)
    except ValueError:
        return views.admin_event_page(old, error="Please check the dates and the score.")
    if not v["name"] or not v["audience_label"]:
        return views.admin_event_page(old, error="Name and audience are required.")
    # A delayed flight remembers its old date automatically.
    if (v["status"] == "delayed" and not v["previous_date"] and old["start_date"]
            and (v["start_date"], v["end_date"]) != (old["start_date"], old["end_date"])):
        v["previous_date"] = fmt_dates(old["start_date"], old["end_date"])
    sets = ", ".join(f"{c}=%s" for c in COLS)
    db.run(f"UPDATE events SET {sets}, updated_at=now() WHERE id=%s", [v[c] for c in COLS] + [event_id])

    msgs = ["Saved."]
    if v["status"] != old["status"]:
        db.run("INSERT INTO status_log (event_id, from_status, to_status) VALUES (%s,%s,%s)",
               (event_id, old["status"], v["status"]))
        if v["status"] in MAIL_STAGES:
            if prepare_email(event_id, v["status"], request):
                msgs.append("Its email is waiting in the Outbox for your approval.")
            elif v["scope"] == "chapter":
                msgs.append("No email prepared: this flight has no mailing lists.")
    # Keep any waiting email in sync with the latest details.
    for p in db.all("SELECT stage FROM email_queue WHERE event_id=%s AND status='pending'", (event_id,)):
        prepare_email(event_id, p["stage"], request)
    flash(request, " ".join(msgs))
    return go(f"/admin/event/{event_id}")


@app.post("/admin/event/{event_id}/photo")
async def upload_photo(request: Request, event_id: int, photo: UploadFile = File(...)):
    if (r := need(request, admin=True)):
        return r
    data = await photo.read()
    if photo.content_type not in PHOTO_TYPES:
        flash(request, "Please upload a JPG, PNG or WebP image.")
    elif len(data) > MAX_PHOTO:
        flash(request, "That photo is over 3 MB. Please use a smaller one.")
    else:
        token = secrets.token_urlsafe(18)
        db.run("INSERT INTO photos (token, mime, data) VALUES (%s,%s,%s)", (token, photo.content_type, data))
        db.run("UPDATE events SET photo_token=%s, updated_at=now() WHERE id=%s", (token, event_id))
        for p in db.all("SELECT stage FROM email_queue WHERE event_id=%s AND status='pending'", (event_id,)):
            prepare_email(event_id, p["stage"], request)
        flash(request, "Photo updated.")
    return go(f"/admin/event/{event_id}")


# ---------------------------------------------------------------- outbox

@app.get("/admin/outbox", response_class=HTMLResponse)
def outbox(request: Request):
    if (r := need(request, admin=True)):
        return r
    # Rebuild every waiting email from the flight's current details and the current design,
    # so what you preview is always exactly what will be sent.
    for p in db.all("SELECT event_id, stage FROM email_queue WHERE status='pending'"):
        prepare_email(p["event_id"], p["stage"], request)
    items = db.all("""SELECT q.*, e.code FROM email_queue q JOIN events e ON e.id=q.event_id
                      WHERE q.status='pending' ORDER BY q.created_at""")
    return views.outbox_page(items, pop_flash(request))


@app.get("/admin/outbox/{item_id}/preview", response_class=HTMLResponse)
def outbox_preview(request: Request, item_id: int):
    if (r := need(request, admin=True)):
        return r
    it = db.one("SELECT html FROM email_queue WHERE id=%s", (item_id,))
    return HTMLResponse(it["html"] if it else "Not found", status_code=200 if it else 404)


@app.post("/admin/outbox/{item_id}/approve")
def outbox_approve(request: Request, item_id: int):
    if (r := need(request, admin=True)):
        return r
    it = db.one("SELECT * FROM email_queue WHERE id=%s AND status='pending'", (item_id,))
    if not it:
        flash(request, "That email was already handled.")
        return go("/admin/outbox")
    try:
        mailer.send(it["recipients"], it["subject"], it["html"], it["text"])
    except mailer.MailError as ex:
        db.run("UPDATE email_queue SET error=%s WHERE id=%s", (str(ex), item_id))
        flash(request, f"Not sent. {ex}")
        return go("/admin/outbox")
    db.run("UPDATE email_queue SET status='sent', decided_at=now(), error=NULL WHERE id=%s", (item_id,))
    flash(request, f"Sent to {', '.join(it['recipients'])}.")
    return go("/admin/outbox")


@app.post("/admin/outbox/{item_id}/test")
def outbox_test(request: Request, item_id: int, to: str = Form(...)):
    if (r := need(request, admin=True)):
        return r
    it = db.one("SELECT * FROM email_queue WHERE id=%s", (item_id,))
    if not it:
        return go("/admin/outbox")
    try:
        mailer.send([to.strip()], "[TEST] " + it["subject"], it["html"], it["text"])
        flash(request, f"Test sent to {to.strip()}. The real email is still waiting for approval.")
    except mailer.MailError as ex:
        flash(request, f"Test not sent. {ex}")
    return go("/admin/outbox")


@app.post("/admin/outbox/{item_id}/discard")
def outbox_discard(request: Request, item_id: int):
    if (r := need(request, admin=True)):
        return r
    db.run("UPDATE email_queue SET status='discarded', decided_at=now() WHERE id=%s AND status='pending'", (item_id,))
    flash(request, "Email discarded. Nothing was sent.")
    return go("/admin/outbox")
