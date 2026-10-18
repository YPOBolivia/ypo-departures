"""Stage emails. Table-based HTML with inline styles so it renders well in Gmail and Outlook."""
from views import enrich, e, score_label

FROM_NAME = "YPO Bolivia"

COPY = {
    "captain": {
        "kicker": "DAY CHAIR ON BOARD",
        "subject": "Day Chair on board: {name}",
        "headline": "We have a captain.",
        "body": ("{captain} will be the Day Chair of <strong>{name}</strong>. The date, the destination and "
                 "every detail are now in their hands, and we will let you know as soon as the date is confirmed."),
    },
    "dated": {
        "kicker": "DATE CONFIRMED",
        "subject": "Date confirmed: {name} · {date}",
        "headline": "Save the date.",
        "body": ("<strong>{name}</strong> takes off on <strong>{date}</strong>{in_city}. "
                 "Registration opens soon on YPO Connect, and we will let you know the moment boarding begins."),
    },
    "boarding": {
        "kicker": "NOW BOARDING",
        "subject": "Now boarding: {name} · {date}",
        "headline": "Now boarding.",
        "body": ("Registration for <strong>{name}</strong> is now open on YPO Connect. {captain_line}"
                 "We would love to have you on board."),
    },
    "final_call": {
        "kicker": "FINAL CALL",
        "subject": "Final call: {name} · {date}",
        "headline": "Final call.",
        "body": ("Registration for <strong>{name}</strong> is closing soon{note}. "
                 "If you are joining us, now is the time to register on YPO Connect."),
    },
    # Prepared when the flight lands (the morning after); waits for approval like the others.
    "landed": {
        "kicker": "LANDED · THANK YOU",
        "subject": "Thank you for flying with us: {name}",
        "headline": "Thank you for flying with us.",
        "body": ("Thank you for being part of <strong>{name}</strong>. {thanks} "
                 "Your feedback shapes the next experience our community creates, and it only takes a couple of minutes."),
    },
    # Sent automatically on the morning of the event (07:30 Eastern), no approval needed.
    "in_flight": {
        "kicker": "IN FLIGHT · TODAY",
        "subject": "Today: {name}",
        "headline": "Today we fly.",
        "body": ("Today is the day. If you are registered for <strong>{name}</strong>, "
                 "we look forward to seeing you{in_city}. {thanks}"),
    },
}

STATUS_COLOR = {"captain": "#D6B26E", "dated": "#82B4FF", "boarding": "#2FA866", "final_call": "#D98E1E",
                "in_flight": "#FFFFFF", "landed": "#9FB0C8"}


def render(ev_raw: dict, stage: str, base_url: str):
    """Returns (subject, html, text) for a stage email."""
    ev = enrich(ev_raw)
    c = COPY[stage]
    name = ev["name"]
    date = ev["date_label"]
    # Day Chair on board comes before the date: the Day Chair sets it, so it is not shown yet.
    if stage == "captain":
        date = "Set by your captain"
    has_captain = bool(ev["lead"])
    fields = {
        "name": e(name),
        "date": e(date),
        "captain": e(ev["lead"] or "Our Day Chair"),
        "in_city": f" in <strong>{e(ev['city'])}</strong>" if ev.get("city") else "",
        "captain_line": ((f"Our champions, {e(ev['lead'])}, have" if ev["lead_is_champions"] else f"Our captain, {e(ev['lead'])}, has")
                         + " prepared this experience for our community. "
                         if has_captain else ""),
        "note": f" ({e(ev['status_note'])})" if ev.get("status_note") else "",
        "thanks": ((f"Thank you to our champions, {e(ev['lead'])}, for" if ev["lead_is_champions"]
                    else f"Thank you to our captain, {e(ev['lead'])}, for")
                   + " creating this experience for our community." if has_captain else ""),
    }
    subject = c["subject"].format(name=name, date=date)
    body_tpl = c["body"]
    if stage == "captain" and ev["lead_is_champions"]:
        body_tpl = ("{captain} will lead <strong>{name}</strong> as Champions. The date, the destination and "
                    "every detail are now in their hands, and we will let you know as soon as the date is confirmed.")
    body_html = body_tpl.format(**fields)
    flight_url = f"{base_url.rstrip('/')}/flight/{ev['code']}"
    if stage in ("boarding", "final_call") and ev.get("connect_url"):
        cta_label, cta_url = "Register on YPO Connect", ev["connect_url"]
    elif stage == "landed" and ev.get("survey_url"):
        cta_label, cta_url = "Share your feedback", ev["survey_url"]
    else:
        cta_label, cta_url = "See this flight", flight_url
    color = STATUS_COLOR[stage]
    footnote = {"landed": "The survey opens on YPO Connect.",
                "in_flight": "See you there."}.get(stage, "Official registration always happens on YPO Connect.")

    captain_block = ""
    if has_captain:
        photo = (f'<img src="{e(base_url.rstrip("/") + ev["photo_url"])}" width="72" height="72" alt="" '
                 f'style="display:block;width:72px;height:72px;border-radius:36px;object-fit:cover;border:2px solid #D6B26E">'
                 if ev.get("photo_url") else
                 '<div style="width:72px;height:72px;border-radius:36px;background:#0B2C5C;border:2px solid #D6B26E"></div>')
        quote = (f'<div style="font-family:Georgia,serif;font-style:italic;font-size:16px;line-height:1.5;color:#4A5568;'
                 f'padding-top:6px">“{e(ev["quote"])}”</div>') if ev.get("quote") else ""
        champs = (f'<div style="font-size:14px;color:#4A5568;padding-top:2px">{e(ev["crew_line"])}</div>'
                  if ev["crew_line"] else "")
        captain_block = f'''<tr><td style="padding:0 40px 24px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F7F3EA;border-radius:12px">
<tr><td width="96" style="padding:18px 0 18px 18px;vertical-align:top">{photo}</td>
<td style="padding:18px;vertical-align:middle;font-family:Arial,Helvetica,sans-serif">
<div style="font-family:'Courier New',monospace;font-size:12px;letter-spacing:2px;color:#6B5A2E">{"YOUR CHAMPIONS" if ev["lead_is_champions"] else "YOUR CAPTAIN"}</div>
<div style="font-family:Georgia,serif;font-weight:bold;font-size:22px;color:#041E42;padding-top:4px">{e(ev["lead"])}</div>{champs}{quote}</td></tr></table></td></tr>'''

    chip_cells = "".join(
        f'<span style="display:inline-block;font-family:\'Courier New\',monospace;font-weight:bold;font-size:13px;'
        f'letter-spacing:1px;padding:4px 9px;border-radius:4px;background:{ch["color"]};color:#041E42;margin:0 4px 4px 0">'
        f'{e(ch["label"])}</span>' for ch in ev["chips_rich"])

    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(subject)}</title></head>
<body style="margin:0;padding:0;background:#E9E4D8">
<div style="display:none;max-height:0;overflow:hidden">{e(c["headline"])} {e(name)} · {e(date)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#E9E4D8"><tr><td align="center" style="padding:28px 12px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px">
<tr><td style="background:#041E42;border-radius:14px 14px 0 0;padding:30px 40px;color:#F3EEE3;font-family:Arial,Helvetica,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
<td style="vertical-align:middle"><img src="{e(base_url.rstrip('/'))}/static/logo-h-white.png" width="188" height="35" alt="YPO Bolivia Integrated" style="display:block;border:0;width:188px;height:35px;color:#F3EEE3;font-family:Arial,Helvetica,sans-serif;font-size:16px;font-weight:bold"></td>
<td align="right" style="vertical-align:middle;font-family:'Courier New',monospace;font-size:12px;letter-spacing:2px;color:#D6B26E;line-height:1.6">DEPARTURES FY26-27<br><span style="color:#B9C4D6;letter-spacing:1px;font-size:13px">{e(ev["code"])}</span></td></tr></table>
<div style="padding-top:24px;font-family:'Courier New',monospace;font-weight:bold;font-size:15px;letter-spacing:2px;color:{color}">● {e(c["kicker"])}</div>
<div style="padding-top:12px;font-family:Georgia,serif;font-size:40px;line-height:1.12;font-weight:bold;color:#F3EEE3">{e(name)}</div></td></tr>
<tr><td style="background:#FFFFFF;border-left:1px solid #D3CCBB;border-right:1px solid #D3CCBB">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-family:'Courier New',monospace"><tr>
<td width="33%" style="padding:18px 22px;border-right:1px dashed #D3CCBB;vertical-align:top"><div style="font-size:12px;letter-spacing:2px;color:#6A7487">DATE</div><div style="font-weight:bold;font-size:18px;color:#041E42;padding-top:6px">{e(date)}</div></td>
<td width="33%" style="padding:18px 22px;border-right:1px dashed #D3CCBB;vertical-align:top"><div style="font-size:12px;letter-spacing:2px;color:#6A7487">DESTINATION</div><div style="font-weight:bold;font-size:18px;color:#041E42;padding-top:6px">{e((ev.get("city") or "TBA").upper())}</div></td>
<td width="34%" style="padding:18px 22px;vertical-align:top"><div style="font-size:12px;letter-spacing:2px;color:#6A7487;padding-bottom:6px">GATE</div>{chip_cells}</td>
</tr></table></td></tr>
<tr><td style="background:#FFFFFF;border:1px solid #D3CCBB;border-top:1px dashed #D3CCBB;border-radius:0 0 14px 14px;padding:0">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:32px 40px 8px;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:1px;color:#6B5A2E;text-transform:uppercase">For: {e(ev.get("audience_label"))}</td></tr>
<tr><td style="padding:8px 40px 24px;font-family:Arial,Helvetica,sans-serif;font-size:17px;line-height:1.6;color:#1B2A44">Dear community: {body_html}</td></tr>
{captain_block}
<tr><td style="padding:0 40px 16px" align="center"><a href="{e(cta_url)}" style="display:block;background:#D6B26E;color:#041E42;font-family:Arial,Helvetica,sans-serif;font-weight:bold;font-size:17px;text-decoration:none;padding:17px 20px;border-radius:10px;text-align:center">{e(cta_label)}</a></td></tr>
<tr><td style="padding:0 40px 32px;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#6A7487;text-align:center">{footnote}</td></tr>
</table></td></tr>
<tr><td align="center" style="padding:24px 12px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:1.6;color:#6A7487">
<div style="font-family:'Courier New',monospace;letter-spacing:3px;color:#6B5A2E">ONLY IN YPO</div>
You are receiving this because you are part of YPO Bolivia Integrated.<br>
<a href="{e(base_url.rstrip('/'))}/" style="color:#041E42">See all departures this season</a></td></tr>
</table></td></tr></table></body></html>'''

    import re
    text_body = re.sub(r"<[^>]+>", "", body_html)
    import html as _h
    text = (f"{c['kicker']} · {name}\n{date} · {ev.get('city') or 'TBA'}\nFor: {ev.get('audience_label')}\n\n"
            f"Dear community: {_h.unescape(text_body)}\n\n{cta_label}: {cta_url}\n\n"
            f"See all departures: {base_url.rstrip('/')}/\nONLY IN YPO")
    return subject, html, text
