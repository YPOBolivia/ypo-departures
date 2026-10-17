"""Flight stages, audience chips and date formatting for YPO Bolivia Departures."""
import datetime as dt

# Order matters: this is the journey every flight follows.
STAGES = [
    {"key": "scheduled",  "label": "Scheduled",          "color": "#7C8CA6", "mail": False,
     "desc": "The flight is on this season's plan."},
    {"key": "captain",    "label": "Day Chair on board", "color": "#D6B26E", "mail": True,
     "desc": "We have a captain. They set the date."},
    {"key": "dated",      "label": "Date confirmed",     "color": "#82B4FF", "mail": True,
     "desc": "The Day Chair confirmed when we take off."},
    {"key": "boarding",   "label": "Boarding",           "color": "#4CD08A", "mail": True,
     "desc": "Registration open on YPO Connect."},
    {"key": "final_call", "label": "Final call",         "color": "#F2A93B", "mail": True,
     "desc": "Last seats or registration closing."},
    {"key": "gate_closed", "label": "Gate closed",       "color": "#B9A3F0", "mail": False,
     "desc": "Registration closed. See you on the day."},
    {"key": "delayed",    "label": "Delayed",            "color": "#F08A75", "mail": False,
     "desc": "A new date, shared gracefully."},
    {"key": "in_flight",  "label": "In flight",          "color": "#FFFFFF", "mail": False,
     "desc": "Today is the day."},
    {"key": "landed",     "label": "Landed",             "color": "#9FB0C8", "mail": False,
     "desc": "We close the loop with the /5 score."},
]
STAGE_BY_KEY = {s["key"]: s for s in STAGES}
STAGE_KEYS = [s["key"] for s in STAGES]
MAIL_STAGES = {s["key"] for s in STAGES if s["mail"]}
# The main path (delayed is a detour, not a step).
TRACK = ["scheduled", "captain", "dated", "boarding", "final_call", "gate_closed", "in_flight", "landed"]

CHIP_COLORS = {
    "MEMBERS": "#D6B26E",
    "ALL": "#F3EEE3",
    "SPOUSES": "#E9B9C1",
    "MEN": "#9EC1F0",
    "WOMEN": "#E9B9C1",
    "FAMILIES": "#74D3C9",
    "YNG": "#74D3C9",
}
CHIP_DEFAULT = "#B9C4D6"

# The four chapter mailing lists.
LISTS = {
    "members": "members@ypobolivia.com",
    "spouses": "spouses.all@ypobolivia.com",
    "all": "all@ypobolivia.com",
    "yng": "yng@ypobolivia.com",
}

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

LA_PAZ = dt.timezone(dt.timedelta(hours=-4))


def _d(day: dt.date) -> str:
    return f"{day.day:02d} {MONTHS[day.month - 1]}"


def fmt_dates(start, end=None) -> str:
    """'04 NOV', '05–08 NOV', '30 NOV – 02 DEC'. Empty dates -> '— — —'."""
    if not start:
        return "— — —"
    if not end or end == start:
        return _d(start)
    if start.month == end.month and start.year == end.year:
        return f"{start.day:02d}–{end.day:02d} {MONTHS[start.month - 1]}"
    return f"{_d(start)} – {_d(end)}"


def chip_list(chips):
    return [{"label": c, "color": CHIP_COLORS.get(c, CHIP_DEFAULT)} for c in (chips or [])]


def track_position(status: str) -> int:
    """Index on the main track; delayed sits where 'dated' is (it has a date, just a new one)."""
    if status == "delayed":
        return TRACK.index("dated")
    return TRACK.index(status) if status in TRACK else 0


def at_least(status: str, key: str) -> bool:
    return track_position(status) >= TRACK.index(key)
