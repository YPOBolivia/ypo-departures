"""HTML for every page, built with plain Python so it stays easy to read and test."""
import datetime as dt
from html import escape as _esc

from stages import (STAGES, STAGE_BY_KEY, TRACK, LISTS, LA_PAZ, fmt_dates, chip_list,
                    track_position, at_least, AUDIENCES, derive)

SEASON = "FY26-27"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;'
         '0,9..144,600;0,9..144,700;1,9..144,400&family=IBM+Plex+Mono:wght@400;500;600&'
         'family=Public+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">')
MAIL_ICON = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#D6B26E" stroke-width="2" '
             'stroke-linecap="round" stroke-linejoin="round" {a}><rect x="3" y="5" width="18" height="14" rx="2">'
             '</rect><path d="M3 7l9 6 9-6"></path></svg>')
PERSON_ICON = ('<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="#8FA3C4" stroke-width="1.5" '
               'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4">'
               '</circle><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"></path></svg>')


def e(v) -> str:
    return _esc("" if v is None else str(v), quote=True)


# ---------------------------------------------------------------- data shaping

def score_label(ev):
    if ev.get("score") is None:
        return ""
    s = f"★ {float(ev['score']):.2f}/5"
    if ev.get("score_n"):
        s += f" · {ev['score_n']} responses"
    return s


def enrich(ev: dict) -> dict:
    """Adds everything the pages and emails need on top of the raw DB row."""
    ev = dict(ev)
    st = STAGE_BY_KEY.get(ev.get("status") or "scheduled", STAGE_BY_KEY["scheduled"])
    ev["stage"] = st
    ev["date_label"] = fmt_dates(ev.get("start_date"), ev.get("end_date"))
    ev["chips_rich"] = chip_list(ev.get("chips"))
    ev["is_regional"] = ev.get("scope") == "regional"
    ev["photo_url"] = f"/media/{ev['photo_token']}" if ev.get("photo_token") else None
    dc, ch = ev.get("day_chair"), ev.get("champions")
    ev["lead"] = dc or ch
    ev["lead_is_champions"] = bool(ch) and not dc
    ev["lead_kicker"] = "YOUR CHAMPIONS ON THIS FLIGHT" if ev["lead_is_champions"] else "YOUR CAPTAIN ON THIS FLIGHT"
    ev["crew_line"] = f"With {ch}" if (dc and ch) else ""
    ev["captain_shown"] = bool(ev["lead"]) and at_least(st["key"], "captain")
    ev["tags"] = list(ev.get("tags") or [])
    ev["city_label"] = ev.get("city") or "TBA"
    # Short line under the status on the board.
    note = ev.get("status_note") or ""
    k = st["key"]
    if not note:
        if k == "landed":
            note = score_label(ev) or "Baggage claim · feedback in progress"
        elif k == "delayed" and ev.get("previous_date"):
            note = f"Was: {ev['previous_date']}"
        elif k == "boarding":
            note = "Register on YPO Connect"
        elif k == "captain":
            note = "Setting the date"
        elif k == "dated":
            note = "Registration opening soon"
        elif k == "gate_closed":
            note = "Registration closed · see you there"
    ev["note"] = note
    return ev


def filter_tags(ev) -> str:
    tags = set(ev["tags"])
    tags.add("regional" if ev["is_regional"] else "chapter")
    return " ".join(sorted(tags))


# ---------------------------------------------------------------- shell

def page(title: str, body: str, extra_head: str = "") -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title>{FONTS}<link rel="stylesheet" href="/static/style.css">'
            f'{extra_head}</head><body>{body}</body></html>')


def topbar(role: str | None, current: str = "") -> str:
    links = ['<a href="/">Departures</a>']
    if role == "admin":
        links.append('<a href="/admin">Control tower</a>')
    if role:
        links.append('<a href="/logout">Log out</a>')
    return (f'<div class="topbar"><a class="brand" href="/" aria-label="Departures home">'
            f'<img class="logo" src="/static/logo-h-white.png" alt="YPO Bolivia Integrated" width="214" height="40"></a>'
            f'<nav aria-label="Main">{"".join(links)}</nav></div>')


def lamp(st, blink=False) -> str:
    cls = "lamp blink" if blink else "lamp"
    return (f'<span class="{cls}" aria-hidden="true" '
            f'style="background:{st["color"]};box-shadow:0 0 10px {st["color"]}"></span>')


def chips_html(ev) -> str:
    return "".join(f'<span class="chip" style="background:{c["color"]}">{e(c["label"])}</span>'
                   for c in ev["chips_rich"])


# ---------------------------------------------------------------- login

def login_page(error: str = "") -> str:
    err = f'<p class="err" role="alert">{e(error)}</p>' if error else ""
    body = f'''<main class="login"><form method="post" action="/login">
<img src="/static/logo-stack-white.png" alt="YPO Bolivia Integrated" width="110" height="128" style="align-self:center;margin-bottom:8px">
<h1 style="text-align:center">Departures</h1>
<p style="margin:0;color:var(--muted);line-height:1.5;text-align:center">The experiences our community is creating this season.</p>
<label>Password<input type="password" name="password" autocomplete="current-password" required autofocus></label>
{err}<button class="btn" type="submit">Enter</button></form></main>'''
    return page("Departures · YPO Bolivia", body)


# ---------------------------------------------------------------- board

def board_row(ev) -> str:
    st = ev["stage"]
    flaps = "".join(f'<span class="flap">{e(c)}</span>' for c in ev["code"])
    tba = " tba" if ev["date_label"].startswith("—") else ""
    if ev["is_regional"] or (st["key"] == "landed" and not ev["captain_shown"]):
        cap = ""
    elif ev["captain_shown"]:
        cap = f'<div class="cap">{"Champions" if ev["lead_is_champions"] else "Captain"}: {e(ev["lead"])}</div>'
    else:
        cap = '<div class="cap none">Seeking a captain</div>'
    regional = '<span class="regional">REGIONAL · GLOBAL YPO</span>' if ev["is_regional"] else ""
    return f'''<a class="row" href="/flight/{e(ev["code"])}" data-tags="{e(filter_tags(ev))}">
<div class="c-code"><span class="flaps" aria-label="Flight {e(ev["code"])}">{flaps}</span></div>
<div class="c-date{tba}">{e(ev["date_label"])}</div>
<div class="c-exp"><div class="name">{e(ev["name"])}</div>{cap}</div>
<div class="c-city">{e(ev["city_label"])}</div>
<div class="c-gate"><div class="chips" title="{e(ev.get("audience_label"))}">{chips_html(ev)}</div>{regional}</div>
<div class="c-status">{lamp(st, st["key"] == "final_call")}<div>
<span class="st" style="color:{st["color"]}">{e(st["label"])}</span>
<span class="note">{e(ev["note"])}</span></div></div></a>'''


def board_table(rows, label, empty_text) -> str:
    head = ('<div class="board-head" aria-hidden="true"><div>FLIGHT</div><div>DATE</div>'
            '<div>EXPERIENCE · CAPTAIN</div><div>DESTINATION</div><div>GATE</div><div>STATUS</div></div>')
    inner = "".join(board_row(r) for r in rows) or f'<div class="empty">{e(empty_text)}</div>'
    return f'<section class="board" aria-label="{e(label)}">{head}{inner}</section>'


def board_page(events, role, updated_at) -> str:
    evs = [enrich(x) for x in events]
    departures = [x for x in evs if x["stage"]["key"] != "landed"]
    arrivals = list(reversed([x for x in evs if x["stage"]["key"] == "landed"]))
    upd = ""
    if updated_at:
        u = updated_at.astimezone(LA_PAZ)
        upd = f"Updated {u.day:02d} {u.strftime('%b').upper()} {u.year} · {u:%H:%M}"
    filters = [("all", "All flights"), ("members", "Members"), ("spouses", "Spouses"),
               ("families", "Families & YNG"), ("guests", "Guests & KA"), ("chapter", "Chapter"), ("regional", "Regional")]
    pills = "".join(f'<button type="button" class="pill" data-filter="{k}" aria-pressed="{"true" if k == "all" else "false"}">{e(v)}</button>'
                    for k, v in filters)
    stages = "".join(
        f'''<div class="stage{' mail' if s['mail'] else ''}"><div class="n"><span>{i + 1:02d}</span>{MAIL_ICON.format(a='role="img" aria-label="Sends email"') if s['mail'] else ''}</div>
<div class="l" style="color:{s['color']}"><span class="lamp" aria-hidden="true" style="width:10px;height:10px;background:{s['color']}"></span>{e(s['label'])}</div>
<div class="d">{e(s['desc'])}</div></div>''' for i, s in enumerate(STAGES))
    gates = f'''<div class="gates">
<div class="card"><div class="chips"><span class="chip" style="background:#D6B26E">MEMBERS</span></div><div class="who">Members only</div></div>
<div class="card"><div class="chips"><span class="chip" style="background:#D6B26E">MEMBERS</span><span class="chip" style="background:#E9B9C1">SPOUSES</span></div><div class="who">Members &amp; spouses</div></div>
<div class="card"><div class="chips"><span class="chip" style="background:#E9B9C1">SPOUSES</span></div><div class="who">Spouses only</div></div>
<div class="card"><div class="chips"><span class="chip" style="background:#9EC1F0">MEN</span><span class="chip" style="background:#F2C6A0">WOMEN</span></div><div class="who">Men-only and women-only gatherings for members &amp; spouses</div></div>
<div class="card"><div class="chips"><span class="chip" style="background:#74D3C9">FAMILIES</span></div><div class="who">Members, spouses and their children, YNG included</div></div>
<div class="card"><div class="chips"><span class="chip" style="background:#74D3C9">YNG</span></div><div class="who">YNG community only</div></div>
<div class="card"><div class="chips"><span class="chip" style="background:#BFD7A5">KEY ASSOCIATES</span><span class="chip" style="background:#D9C7F0">GUESTS</span></div><div class="who">Open to Key Associates or guests when the flight says so</div></div>
</div>'''
    body = f'''<div class="wrap">{topbar(role)}
<header class="hero"><div><h1>Departures</h1>
<p>The experiences our community is creating this season. Find your gate and follow your flight.</p></div>
<div class="season"><span class="k">SEASON</span><span class="v">{SEASON}</span><span class="u">{e(upd)}</span></div></header>
<nav class="filters" aria-label="Filter by gate"><span class="k">GATE</span>{pills}</nav>
{board_table(departures, "Departures", "No departures yet.")}
<section class="section"><div class="section-head"><h2>Arrivals</h2><span class="hint">Flights that already landed, with how our community rated them.</span></div>
{board_table(arrivals, "Arrivals", "No flights have landed yet this season.")}</section>
<section class="section"><div class="section-head"><h2>Every flight's journey</h2>
<span class="hint">{MAIL_ICON.format(a='aria-hidden="true"')} Sends an email to the flight's gate, after approval</span></div>
<div class="stages">{stages}</div></section>
<section class="section"><h2>Boarding gates</h2>{gates}</section>
<footer class="foot"><span>Official registration always happens on YPO Connect.</span><span class="mono" style="letter-spacing:2px">ONLY IN YPO</span></footer>
</div>
<script>
(function(){{
  var pills=document.querySelectorAll('.pill');
  pills.forEach(function(p){{p.addEventListener('click',function(){{
    var f=p.getAttribute('data-filter');
    pills.forEach(function(q){{q.setAttribute('aria-pressed',q===p?'true':'false');}});
    document.querySelectorAll('.row').forEach(function(r){{
      var tags=(r.getAttribute('data-tags')||'').split(' ');
      r.hidden=!(f==='all'||tags.indexOf(f)>-1);
    }});
  }});}});
}})();
</script>'''
    return page("Departures · YPO Bolivia", body)


# ---------------------------------------------------------------- flight page

def captain_card(ev, big=False) -> str:
    if not ev["captain_shown"]:
        return ""
    avatar = (f'<img class="avatar" src="{e(ev["photo_url"])}" alt="{e(ev["lead"])}">' if ev["photo_url"]
              else f'<div class="avatar">{PERSON_ICON.format(s=40)}</div>')
    champs = f'<div class="ch">{e(ev["crew_line"])}</div>' if ev["crew_line"] else ""
    quote = f'<blockquote>“{e(ev["quote"])}”</blockquote>' if ev.get("quote") else ""
    return f'''<section class="cabin" aria-label="Captain's cabin"><div class="k">{ev["lead_kicker"]}</div>
<div class="who">{avatar}<div><div class="nm">{e(ev["lead"])}</div>{champs}</div></div>{quote}</section>'''


def track_html(ev) -> str:
    pos = track_position(ev["stage"]["key"])
    items = []
    for i, key in enumerate(TRACK):
        s = STAGE_BY_KEY[key]
        cls = "done" if i < pos else ("done now" if i == pos else "")
        label = s["label"]
        if i == pos and ev["stage"]["key"] == "delayed":
            label = "Delayed · new date"
        items.append(f'<li class="{cls}"><span class="dot" aria-hidden="true"></span>'
                     f'<span class="t">{e(label)}</span></li>')
    return f'<ol class="track" aria-label="Flight progress">{"".join(items)}</ol>'


def flight_page(ev_raw, role) -> str:
    ev = enrich(ev_raw)
    st = ev["stage"]
    k = st["key"]
    register = ""
    if k in ("boarding", "final_call") and ev.get("connect_url"):
        register = f'<a class="btn" href="{e(ev["connect_url"])}" target="_blank" rel="noopener">Register on YPO Connect</a>'
    landed = ""
    if k == "landed" and ev.get("score") is not None:
        landed = f'<div class="flash">Our community rated this flight {e(score_label(ev))}.</div>'
    elif k == "landed":
        landed = ('<div class="flash">Baggage claim: we are gathering your feedback. '
                  'The score will appear here once it is in.</div>')
    seeking = ""
    if not ev["captain_shown"] and not ev["is_regional"] and k != "landed":
        seeking = ('<section class="card"><div class="k mono" style="font-size:13px;letter-spacing:3px;color:var(--gold)">'
                   'CAPTAIN</div><div class="who">This flight is still looking for its Day Chair.</div></section>')
    regional = ('<p style="margin:0;color:var(--dim);font-size:14px">Regional or global YPO experience: shown here so the '
                'whole chapter knows.</p>') if ev["is_regional"] else ""
    date_v = ev["date_label"] if (at_least(k, "dated") or ev["is_regional"] or k == "scheduled") else "Set by your captain"
    body = f'''<div class="wrap">{topbar(role)}
<a href="/" style="font-size:14px">← All departures</a>
<div class="flight"><div style="display:flex;flex-direction:column;gap:24px">
<section class="ticket"><div class="status-big" style="color:{st["color"]}">{lamp(st, k == "final_call")}{e(st["label"])}</div>
<div><div class="mono" style="font-size:15px;letter-spacing:3px;color:var(--muted)">FLIGHT {e(ev["code"])}</div>
<h1>{e(ev["name"])}</h1></div>
<div class="facts"><div class="fact"><span class="k">DATE</span><span class="v">{e(date_v)}</span></div>
<div class="fact"><span class="k">DESTINATION</span><span class="v">{e(ev["city_label"])}</span></div>
<div class="fact"><span class="k">GATE</span><span class="chips">{chips_html(ev)}</span></div></div>
<p style="margin:0;color:var(--muted)">For: {e(ev.get("audience_label"))}</p>{regional}
{f'<p style="margin:0;font-size:17px">{e(ev["note"])}</p>' if ev["note"] and k != "landed" else ""}
{landed}<div class="actions">{register}<a class="btn ghost" href="/flight/{e(ev["code"])}/poster">See the poster</a></div></section>
{captain_card(ev)}{seeking}</div>
<aside class="ticket" aria-label="Journey"><h2 style="font-size:24px">The journey</h2>{track_html(ev)}</aside></div>
<footer class="foot"><span>Official registration always happens on YPO Connect.</span><span class="mono" style="letter-spacing:2px">ONLY IN YPO</span></footer></div>'''
    return page(f'{ev["name"]} · Departures', body)


# ---------------------------------------------------------------- poster (the "gigantografía")

POSTER_COPY = {
    "scheduled": ("COMING THIS SEASON", "Something is<br>taking off."),
    "captain": ("DAY CHAIR ON BOARD", "We have<br>a captain."),
    "dated": ("DATE CONFIRMED", "Save<br>the date."),
    "boarding": ("NOW BOARDING", "Now<br>boarding."),
    "final_call": ("FINAL CALL", "Final<br>call."),
    "gate_closed": ("GATE CLOSED", "All on board.<br>See you there."),
    "delayed": ("NEW DATE", "Same flight,<br>new date."),
    "in_flight": ("IN FLIGHT", "Today<br>we fly."),
    "landed": ("LANDED", "Thank you for<br>flying with us."),
}


def poster_page(ev_raw, role) -> str:
    """Same look as the emails: navy header with the stage tag and the event name, then the ticket strip."""
    ev = enrich(ev_raw)
    st = ev["stage"]
    k = st["key"]
    kicker = POSTER_COPY.get(k, POSTER_COPY["scheduled"])[0]
    mono = "font-family:var(--mono)"
    if ev["captain_shown"]:
        photo = (f'<img src="{e(ev["photo_url"])}" alt="" style="width:100%;height:100%;object-fit:cover;display:block">'
                 if ev["photo_url"] else PERSON_ICON.format(s=96))
        quote = (f'<div style="font-family:var(--serif);font-style:italic;font-size:30px;line-height:1.35;color:#4A5568">“{e(ev["quote"])}”</div>'
                 if ev.get("quote") else "")
        champs = f'<div style="font-size:22px;color:#4A5568">{e(ev["crew_line"])}</div>' if ev["crew_line"] else ""
        crew = f'''<div style="display:flex;gap:40px;align-items:center;background:#F7F3EA;border-radius:20px;padding:36px">
<div style="width:220px;height:220px;flex:none;border-radius:110px;overflow:hidden;background:#0B2C5C;border:4px solid #D6B26E;display:flex;align-items:center;justify-content:center">{photo}</div>
<div style="display:flex;flex-direction:column;gap:12px;min-width:0"><div style="{mono};font-size:17px;letter-spacing:3px;color:#6B5A2E">{"YOUR CHAMPIONS" if ev["lead_is_champions"] else "YOUR CAPTAIN"}</div>
<div style="font-family:var(--serif);font-weight:700;font-size:48px;line-height:1.08;color:#041E42">{e(ev["lead"])}</div>{champs}{quote}</div></div>'''
    elif k == "landed":
        crew = (f'<div style="background:#F7F3EA;border-radius:20px;padding:36px;{mono};font-size:40px;color:#041E42">'
                f'{e(score_label(ev) or "Baggage claim · feedback in progress")}</div>')
    else:
        crew = ""
    date_v = ev["date_label"] if (at_least(k, "dated") or ev["is_regional"]) else "Set by your captain"
    cells = [("DATE", f'<span style="{mono};font-weight:600;font-size:28px;color:#041E42">{e(date_v)}</span>'),
             ("DESTINATION", f'<span style="{mono};font-weight:600;font-size:28px;color:#041E42;text-transform:uppercase">{e(ev["city_label"])}</span>'),
             ("GATE", '<span class="chips">' + "".join(
                 f'<span class="chip" style="background:{c["color"]};font-size:18px">{e(c["label"])}</span>' for c in ev["chips_rich"]) + '</span>')]
    pos = track_position(k)
    if k != "landed" and pos + 1 < len(TRACK):
        nxt = STAGE_BY_KEY[TRACK[pos + 1]]
        cells.append(("NEXT STOP", f'<span style="{mono};font-weight:600;font-size:24px;color:#041E42">{e(nxt["label"])}</span>'))
    strip = "".join(
        f'<div style="flex:1;padding:26px 30px;display:flex;flex-direction:column;gap:10px;min-width:0;'
        f'{"border-right:2px dashed #D3CCBB" if n < len(cells) - 1 else ""}">'
        f'<span style="{mono};font-size:15px;letter-spacing:3px;color:#6A7487">{lab}</span>{val}</div>'
        for n, (lab, val) in enumerate(cells))
    poster = f'''<div id="poster" style="width:1080px;height:1350px;box-sizing:border-box;background:#FFFFFF;color:#1B2A44;font-family:var(--sans);display:flex;flex-direction:column;overflow:hidden">
<div style="background:#041E42;color:#F3EEE3;padding:64px 72px 72px;display:flex;flex-direction:column;gap:36px;flex-grow:1;justify-content:space-between">
<div style="display:flex;justify-content:space-between;align-items:center"><img src="/static/logo-h-white.png" alt="YPO Bolivia Integrated" width="300" height="56">
<div style="{mono};text-align:right;line-height:1.7"><div style="font-size:17px;letter-spacing:3px;color:#D6B26E">DEPARTURES {SEASON}</div><div style="font-size:18px;letter-spacing:2px;color:#B9C4D6">{e(ev["code"])}</div></div></div>
<div style="display:flex;flex-direction:column;gap:22px">
<div style="{mono};font-weight:600;font-size:26px;letter-spacing:4px;color:{st["color"]}">● {e(kicker)}</div>
<h1 style="margin:0;font-family:var(--serif);font-weight:700;font-size:88px;line-height:1.04;letter-spacing:-1px;color:#F3EEE3">{e(ev["name"])}</h1></div></div>
<div style="display:flex;padding:0 42px;border-bottom:2px dashed #D3CCBB">{strip}</div>
<div style="padding:44px 72px 56px;display:flex;flex-direction:column;gap:30px">
<div style="font-size:19px;letter-spacing:2px;color:#6B5A2E;text-transform:uppercase">For: {e(ev.get("audience_label"))}</div>
{crew}
<div style="{mono};display:flex;justify-content:space-between;font-size:16px;letter-spacing:3px;color:#6B5A2E"><span>ONLY IN YPO</span><span>YPO BOLIVIA INTEGRATED</span></div></div></div>'''
    body = f'''<div class="wrap">{topbar(role)}
<div class="actions"><a href="/flight/{e(ev["code"])}" style="font-size:14px">← Back to the flight</a>
<button class="btn small" type="button" id="dl">Download poster (PNG)</button>
<span class="help" id="dlmsg" role="status"></span></div>
<div id="frame" style="width:100%;max-width:1080px;overflow:hidden;border-radius:16px"><div id="scaler" style="transform-origin:top left">{poster}</div></div></div>
<script src="https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/dist/html-to-image.js"></script>
<script>
(function(){{
  var frame=document.getElementById('frame'),scaler=document.getElementById('scaler');
  function fit(){{var s=Math.min(1,frame.clientWidth/1080);scaler.style.transform='scale('+s+')';frame.style.height=(1350*s)+'px';}}
  window.addEventListener('resize',fit);fit();
  document.getElementById('dl').addEventListener('click',function(){{
    var msg=document.getElementById('dlmsg');msg.textContent='Preparing…';
    var prev=scaler.style.transform;scaler.style.transform='none';
    htmlToImage.toPng(document.getElementById('poster'),{{pixelRatio:1,width:1080,height:1350}}).then(function(url){{
      scaler.style.transform=prev;var a=document.createElement('a');a.href=url;a.download='{e(ev["code"])}-poster.png';a.click();msg.textContent='';
    }}).catch(function(){{scaler.style.transform=prev;msg.textContent='Could not create the image. Try again or take a screenshot.';}});
  }});
}})();
</script>'''
    return page(f'Poster · {ev["name"]}', body)


# ---------------------------------------------------------------- admin ("control tower")

def admin_page(events, pending, flash="") -> str:
    evs = [enrich(x) for x in events]
    rows = []
    for ev in evs:
        st = ev["stage"]
        lists = ", ".join(x.split("@")[0] + "@" for x in (ev.get("mail_lists") or [])) or "—"
        rows.append(f'''<tr><td class="mono">{e(ev["code"])}</td><td class="mono">{e(ev["date_label"])}</td>
<td><strong>{e(ev["name"])}</strong><div class="help">{e(ev.get("audience_label"))}</div></td>
<td>{e(ev.get("day_chair") or "—")}{f'<div class="help">Champions: {e(ev["champions"])}</div>' if ev.get("champions") else ""}</td>
<td><span style="display:inline-flex;align-items:center;gap:8px;color:{st["color"]}" class="mono">{lamp(st)}{e(st["label"])}</span></td>
<td class="mono help">{e(lists)}</td>
<td><a class="btn small ghost" href="/admin/event/{ev["id"]}">Edit</a></td></tr>''')
    fl = f'<div class="flash" role="status">{e(flash)}</div>' if flash else ""
    badge = f' <span class="badge">{pending}</span>' if pending else ""
    body = f'''<div class="wrap">{topbar("admin")}
<header class="hero"><div><h1>Control tower</h1><p>Move each flight along its journey. Emails never go out until you approve them.</p></div>
<div class="actions"><a class="btn" href="/admin/outbox">Outbox{badge}</a><a class="btn ghost" href="/admin/event/new">New flight</a></div></header>
{fl}<div class="scroll"><table class="atable"><thead><tr><th>FLIGHT</th><th>DATE</th><th>EXPERIENCE</th><th>DAY CHAIR · CHAMPIONS</th><th>STATUS</th><th>EMAILS TO</th><th><span class="sr">Edit</span></th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div></div>'''
    return page("Control tower · Departures", body)


def _opt(value, current, label=None):
    sel = " selected" if value == current else ""
    return f'<option value="{e(value)}"{sel}>{e(label or value)}</option>'


def admin_event_page(ev, flash="", error="", ei_events=None) -> str:
    new = ev is None
    ev = ev or {"status": "scheduled", "scope": "chapter", "chips": [], "tags": [], "mail_lists": []}
    action = "/admin/event/new" if new else f"/admin/event/{ev['id']}"
    statuses = "".join(_opt(s["key"], ev.get("status"), f'{i + 1:02d} · {s["label"]}' + (" ✉" if s["mail"] else ""))
                       for i, s in enumerate(STAGES))
    scope = _opt("chapter", ev.get("scope"), "Chapter (sends emails)") + _opt("regional", ev.get("scope"), "Regional / global (no emails)")
    def d(v): return v.isoformat() if v else ""
    cur = set(ev.get("chips") or ["MEMBERS", "SPOUSES"])
    boxes = "".join(
        f'<label style="flex-direction:row;align-items:center;gap:10px;color:var(--ink)"><input type="checkbox" name="audience" value="{e(k)}"'
        f'{" checked" if k in cur else ""} style="min-height:auto;width:20px;height:20px;accent-color:#D6B26E"> {e(lbl)}</label>'
        for k, lbl in AUDIENCES)
    lists_now = ", ".join(ev.get("mail_lists") or []) or "no emails"
    cur_ei = str(ev.get("ei_event_id") or "")
    ei_opts = '<option value="">Not linked</option>' + "".join(
        _opt(x["id"], cur_ei, f'{x["fy"]} · {x["name"]}' if x["fy"] else x["name"]) for x in (ei_events or []))
    ei_live = ""
    if cur_ei:
        live = (f'{float(ev["score"]):.2f}/5 from {ev["score_n"]} responses' if ev.get("score") is not None and ev.get("ei_name")
                else "no feedback loaded yet")
        ei_live = f'<p class="wide help" style="margin:0;font-size:14px">Live score from Experience Intelligence: <strong class="mono">{e(live)}</strong></p>'
    photo = ""
    if not new:
        cur = (f'<img class="avatar" src="/media/{e(ev["photo_token"])}" alt="Current photo">' if ev.get("photo_token")
               else f'<div class="avatar">{PERSON_ICON.format(s=40)}</div>')
        orig = ev.get("photo_original_token") or ev.get("photo_token")
        repos = (f'<button class="btn small ghost" type="button" id="repos" data-src="/media/{e(orig)}">Reposition current photo</button>'
                 if orig else "")
        photo = f'''<section class="card"><h2 style="font-size:24px">Day Chair photo</h2>
<div class="actions">{cur}<label class="btn small" style="cursor:pointer">Choose a new photo
<input type="file" id="photoFile" accept="image/jpeg,image/png,image/webp" style="position:absolute;width:1px;height:1px;opacity:0"></label>{repos}</div>
<div id="cropBox" hidden style="flex-direction:column;gap:14px">
<div id="stage" style="position:relative;width:320px;height:320px;max-width:100%;overflow:hidden;border-radius:12px;background:#021430;touch-action:none;cursor:grab">
<img id="cropImg" alt="Photo to position" draggable="false" style="position:absolute;left:0;top:0;transform-origin:0 0;max-width:none;user-select:none">
<div aria-hidden="true" style="position:absolute;inset:0;border-radius:50%;box-shadow:0 0 0 400px rgba(2,20,48,.55);outline:2px solid #D6B26E;pointer-events:none"></div></div>
<label style="max-width:320px">Zoom<input type="range" id="zoom" min="1" max="4" step="0.01" value="1" style="padding:0;accent-color:#D6B26E"></label>
<p class="help" style="margin:0">Drag the photo to move it and use the zoom to get closer. The circle is what shows in the emails and on the flight page; the poster uses the whole square.</p>
<div class="actions"><button class="btn small" type="button" id="savePhoto">Save photo</button>
<button class="btn small ghost" type="button" id="cancelCrop">Cancel</button><span class="help" id="photoMsg" role="status"></span></div></div>
<p class="help">JPG, PNG or WebP. It appears on the board, the poster and the emails.</p></section>
<script>
(function(){{
  var box=document.getElementById('cropBox'),stage=document.getElementById('stage'),img=document.getElementById('cropImg');
  var zoom=document.getElementById('zoom'),msg=document.getElementById('photoMsg');
  var action='/admin/event/{ev["id"]}/photo',original=null,S=320,base=1,sc=1,x=0,y=0,drag=null;
  function size(){{S=stage.clientWidth;stage.style.height=S+'px';}}
  function clamp(){{var w=img.naturalWidth*sc,h=img.naturalHeight*sc;x=Math.min(0,Math.max(S-w,x));y=Math.min(0,Math.max(S-h,y));}}
  function draw(){{clamp();img.style.transform='translate('+x+'px,'+y+'px) scale('+sc+')';}}
  function setZoom(z){{var cx=(S/2-x)/sc,cy=(S/2-y)/sc;sc=base*z;x=S/2-cx*sc;y=S/2-cy*sc;draw();}}
  function open(src){{
    box.hidden=false;box.style.display='flex';msg.textContent='';size();
    img.onload=function(){{base=Math.max(S/img.naturalWidth,S/img.naturalHeight);sc=base;zoom.value=1;
      x=(S-img.naturalWidth*sc)/2;y=(S-img.naturalHeight*sc)/2;draw();}};
    img.src=src;
  }}
  stage.addEventListener('pointerdown',function(e){{drag={{px:e.clientX,py:e.clientY,x:x,y:y}};stage.setPointerCapture(e.pointerId);stage.style.cursor='grabbing';}});
  stage.addEventListener('pointermove',function(e){{if(!drag)return;x=drag.x+e.clientX-drag.px;y=drag.y+e.clientY-drag.py;draw();}});
  function end(){{drag=null;stage.style.cursor='grab';}}
  stage.addEventListener('pointerup',end);stage.addEventListener('pointercancel',end);
  stage.addEventListener('wheel',function(e){{e.preventDefault();var z=Math.min(4,Math.max(1,parseFloat(zoom.value)-e.deltaY*0.002));zoom.value=z;setZoom(z);}},{{passive:false}});
  zoom.addEventListener('input',function(){{setZoom(parseFloat(zoom.value));}});
  function shrink(file,cb){{ // keep a lighter copy of the original so it can be repositioned later
    var r=new FileReader();r.onload=function(){{var i=new Image();i.onload=function(){{
      var k=Math.min(1,1600/Math.max(i.width,i.height)),c=document.createElement('canvas');
      c.width=Math.round(i.width*k);c.height=Math.round(i.height*k);c.getContext('2d').drawImage(i,0,0,c.width,c.height);
      c.toBlob(function(b){{cb(b,URL.createObjectURL(b));}},'image/jpeg',0.9);}};i.src=r.result;}};r.readAsDataURL(file);
  }}
  document.getElementById('photoFile').addEventListener('change',function(ev){{
    var f=ev.target.files[0];if(!f)return;shrink(f,function(blob,url){{original=blob;open(url);}});
  }});
  var rp=document.getElementById('repos');
  if(rp)rp.addEventListener('click',function(){{original=null;open(rp.getAttribute('data-src'));}});
  document.getElementById('cancelCrop').addEventListener('click',function(){{box.hidden=true;box.style.display='none';}});
  document.getElementById('savePhoto').addEventListener('click',function(){{
    msg.textContent='Saving…';
    var c=document.createElement('canvas');c.width=800;c.height=800;var g=c.getContext('2d');
    g.fillStyle='#041E42';g.fillRect(0,0,800,800);g.imageSmoothingQuality='high';
    g.drawImage(img,-x/sc,-y/sc,S/sc,S/sc,0,0,800,800);
    c.toBlob(function(b){{
      var fd=new FormData();fd.append('photo',b,'photo.jpg');if(original)fd.append('original',original,'original.jpg');
      fetch(action,{{method:'POST',body:fd,credentials:'same-origin'}}).then(function(r){{
        if(r.ok){{location.reload();}}else{{msg.textContent='Could not save the photo. Try again.';}}
      }}).catch(function(){{msg.textContent='Could not save the photo. Try again.';}});
    }},'image/jpeg',0.9);
  }});
}})();
</script>'''
    fl = f'<div class="flash" role="status">{e(flash)}</div>' if flash else ""
    er = f'<p class="err" role="alert">{e(error)}</p>' if error else ""
    body = f'''<div class="wrap">{topbar("admin")}<a href="/admin" style="font-size:14px">← Control tower</a>
<h1 style="margin:0;font-family:var(--serif);font-size:48px">{"New flight" if new else e(ev.get("name"))}</h1>{fl}{er}
<form method="post" action="{action}" class="card"><div class="form">
<label class="wide">Status<select name="status">{statuses}</select>
<span class="help">Moving to a stage marked ✉ prepares an email in the Outbox for your approval (chapter flights only).</span></label>
<label>Status note<input name="status_note" value="{e(ev.get("status_note"))}" placeholder="e.g. 12 seats left">
<span class="help">Short line under the status. Leave empty for the automatic one.</span></label>
<label>Previous date (when delayed)<input name="previous_date" value="{e(ev.get("previous_date"))}" placeholder="e.g. 20 FEB"></label>
<label class="wide">Experience name<input name="name" required value="{e(ev.get("name"))}"></label>
<label>Start date<input type="date" name="start_date" value="{d(ev.get("start_date"))}"></label>
<label>End date<input type="date" name="end_date" value="{d(ev.get("end_date"))}"></label>
<label>Destination (city)<input name="city" value="{e(ev.get("city"))}" placeholder="TBA"></label>
<label>YPO Connect registration link<input type="url" name="connect_url" value="{e(ev.get("connect_url"))}" placeholder="https://"></label>
<label>Feedback survey link<input type="url" name="survey_url" value="{e(ev.get("survey_url"))}" placeholder="https://">
<span class="help">Goes in the thank-you email when the flight lands.</span></label>
<label>Day Chair<input name="day_chair" value="{e(ev.get("day_chair"))}"></label>
<label>Champions<input name="champions" value="{e(ev.get("champions"))}" placeholder="e.g. Ana Pérez and Luis Rojas"></label>
<label class="wide">Day Chair quote<textarea name="quote" placeholder="Why I created this experience for our community, in one sentence.">{e(ev.get("quote"))}</textarea></label>
<label class="wide">Audience (as it reads in the calendar)<input name="audience_label" required value="{e(ev.get("audience_label"))}">
<span class="help">The exact wording shown to the community, e.g. "Male Members &amp; Male Spouses".</span></label>
<label>Type<select name="scope">{scope}</select></label>
<fieldset class="wide" style="border:1px solid #2C4A78;border-radius:10px;padding:16px 18px;margin:0">
<legend style="padding:0 6px;color:var(--muted);font-size:14px">Who is invited (gate)</legend>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px 18px">{boxes}</div>
<p class="help" style="margin:12px 0 0">Ticks set the board labels, the filters and the mailing list together. Members + Spouses, Families, Men or Women → all@ · Members → members@ · Spouses → spouses.all@ · Families or YNG → + yng@ · Key Associates and Guests have no list of their own: the email goes to the members and/or spouses they come with. Regional flights never send emails.</p>
</fieldset>
<p class="wide help" style="margin:0;font-size:14px">Emails currently go to: <strong class="mono">{lists_now}</strong></p>
<label class="wide">Feedback in Experience Intelligence<select name="ei_event_id">{ei_opts}</select>
<span class="help">Link the flight to its feedback event and the score appears on its own, with two decimals, as soon as the feedback is loaded there.</span></label>
{ei_live}
<label>Score /5, only if not linked<input name="score" inputmode="decimal" value="{e(ev.get("manual_score", ev.get("score")))}" placeholder="e.g. 4.92"></label>
<label>Responses, only if not linked<input name="score_n" inputmode="numeric" value="{e(ev.get("manual_score_n", ev.get("score_n")))}"></label>
</div><div class="actions" style="margin-top:20px"><button class="btn" type="submit">Save</button>
{"" if new else f'<a class="btn ghost" href="/flight/{e(ev.get("code"))}">View flight</a><a class="btn ghost" href="/flight/{e(ev.get("code"))}/poster">Poster</a>'}</div></form>
{photo}</div>'''
    return page("Edit flight · Departures", body)


def outbox_page(items, flash="", sent=None) -> str:
    fl = f'<div class="flash" role="status">{e(flash)}</div>' if flash else ""
    cards = []
    for it in items:
        st = STAGE_BY_KEY.get(it["stage"], STAGE_BY_KEY["scheduled"])
        when = it["created_at"].astimezone(LA_PAZ).strftime("%d %b %H:%M") if it.get("created_at") else ""
        cards.append(f'''<article class="outbox-item"><div class="actions" style="justify-content:space-between">
<div><div class="mono" style="color:{st["color"]};letter-spacing:1px;text-transform:uppercase">{e(st["label"])} · {e(it["code"])}</div>
<div style="font-family:var(--serif);font-size:24px;font-weight:600;margin-top:4px">{e(it["subject"])}</div>
<div class="help mono" style="margin-top:6px">To: {e(", ".join(it["recipients"]))} · Prepared {e(when)}</div></div></div>
{'<p class="err" style="margin:0">This thank-you email has no survey link yet. Add the Feedback survey link in the flight and reopen the Outbox.</p>' if it["stage"] == "landed" and not it.get("survey_url") else ""}
<iframe src="/admin/outbox/{it["id"]}/preview" title="Email preview" loading="lazy"></iframe>
<div class="actions">
<form method="post" action="/admin/outbox/{it["id"]}/approve" onsubmit="return confirm('Send this email to {e(", ".join(it["recipients"]))}?');"><button class="btn" type="submit">Approve &amp; send</button></form>
<form method="post" action="/admin/outbox/{it["id"]}/test"><label style="flex-direction:row;align-items:center;gap:8px"><span class="sr">Test address</span>
<input type="email" name="to" placeholder="send a test to…" required></label><button class="btn small ghost" type="submit">Send test</button></form>
<form method="post" action="/admin/outbox/{it["id"]}/discard"><button class="btn small danger" type="submit">Discard</button></form>
</div>{f'<p class="err">{e(it["error"])}</p>' if it.get("error") else ""}</article>''')
    inner = "".join(cards) or '<div class="card"><div class="who">Nothing waiting. When a flight moves to a stage with ✉, its email appears here.</div></div>'
    rows = []
    for x in (sent or []):
        st = STAGE_BY_KEY.get(x["stage"], STAGE_BY_KEY["scheduled"])
        when = x["decided_at"].astimezone(LA_PAZ).strftime("%d %b %H:%M") if x.get("decided_at") else ""
        auto = " · automatic" if x["stage"] == "in_flight" else ""
        rows.append(f'<tr><td class="mono">{e(when)}</td><td class="mono" style="color:{st["color"]}">{e(st["label"])}{auto}</td>'
                    f'<td>{e(x["subject"])}</td><td class="mono help">{e(", ".join(x["recipients"]))}</td></tr>')
    history = ""
    if rows:
        history = (f'<section class="section"><h2 style="font-size:28px">Recently sent</h2><div class="scroll"><table class="atable">'
                   f'<thead><tr><th>SENT (LA PAZ)</th><th>STAGE</th><th>SUBJECT</th><th>TO</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>')
    body = f'''<div class="wrap">{topbar("admin")}<a href="/admin" style="font-size:14px">← Control tower</a>
<header class="hero"><div><h1>Outbox</h1><p>Every email waits here until you approve it. Sent from events@ypobolivia.com.
The morning-of reminder is the only one that goes out on its own, at 07:30 Eastern.</p></div></header>
{fl}{inner}{history}</div>'''
    return page("Outbox · Departures", body)
