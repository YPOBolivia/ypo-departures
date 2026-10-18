"""Builds seed.sql from the FY26-27 Learning Calendar. Run once: python3 make_seed.py > seed.sql"""
A = "all@ypobolivia.com"
M = "members@ypobolivia.com"
Y = "yng@ypobolivia.com"

# Audience presets: (chips, filter tags, mailing lists)
MEMBERS_ONLY = (["MEMBERS"], ["members"], [M])
MEM_SPOUSES = (["MEMBERS", "SPOUSES"], ["members", "spouses"], [A])
MALE = (["MEN"], ["members", "spouses"], [A])
FEMALE = (["WOMEN"], ["members", "spouses"], [A])
FAMILIES = (["FAMILIES"], ["members", "spouses", "families"], [A, Y])
WITH_YNG = (["MEMBERS", "SPOUSES", "YNG"], ["members", "spouses", "families"], [A, Y])

# (start, end, name, audience label, preset, scope, city)
EVENTS = [
    ("2026-07-23", None, "Fishing Retreat 2026 | First Cast", "Male Members & Male Spouses", MALE, "chapter", None),
    ("2026-08-12", None, "Day Chair Training", "Members & Spouses", MEM_SPOUSES, "regional", None),
    ("2026-08-28", None, "Kick Off FY 26-27 | Access the Unexpected", "Members & Spouses", MEM_SPOUSES, "chapter", None),
    ("2026-09-02", "2026-09-04", "Southern Cone Flagship Event: Business Week | Chile is Back", "Members only", MEMBERS_ONLY, "regional", "Chile"),
    ("2026-10-24", "2026-10-28", "Fishing Retreat Series: Paso de la Patria", "Male Members & Male Spouses", MALE, "chapter", "Paso de la Patria"),
    ("2026-11-04", None, "Dine Around #1", "Members only", MEMBERS_ONLY, "chapter", None),
    ("2026-11-05", "2026-11-08", "A New Togetherness 7.0: The Roots of Wellness", "Female Members & Female Spouses", FEMALE, "chapter", None),
    ("2026-11-21", None, "Visita a la Planta de Reciclaje", "Families", FAMILIES, "chapter", None),
    ("2026-11-28", None, "Celebración de Fin de Año", "Families", FAMILIES, "chapter", None),
    ("2026-11-30", None, "Power Breakfast", "Members only", MEMBERS_ONLY, "chapter", None),
    ("2026-12-01", "2026-12-02", "Apeiron Mexico City", "New Members & Spouses", (["NEW MEMBERS"], ["members", "spouses"], []), "regional", "Mexico City"),
    ("2026-12-05", None, "Fishing Retreat 2026 | Closing Gathering", "Male Members & Male Spouses", MALE, "chapter", None),
    ("2026-12-12", None, "Dine Around #2", "Members & Spouses", MEM_SPOUSES, "chapter", None),
    ("2027-01-16", None, "Family Power: Hitbox and Wisdom, Connecting Generations", "Families", FAMILIES, "chapter", None),
    ("2027-01-21", None, "New Years Eve", "Members & Spouses", MEM_SPOUSES, "chapter", None),
    ("2027-02-16", None, "Power Breakfast", "Members only", MEMBERS_ONLY, "chapter", None),
    ("2027-02-19", "2027-02-21", "Viaje Familiar", "Families", FAMILIES, "chapter", None),
    ("2027-02-23", "2027-02-24", "Regional Board Meeting (RBM)", "REX + incoming CCs", (["REX"], ["members"], []), "regional", None),
    ("2027-03-09", "2027-03-10", "Apeiron São Paulo", "New Members & Spouses", (["NEW MEMBERS"], ["members", "spouses"], []), "regional", "São Paulo"),
    ("2027-03-13", None, "Dine Around #3", "Members & Spouses", MEM_SPOUSES, "chapter", None),
    ("2027-03-15", "2027-03-17", "GLC Bangkok", "Elect Officers only", (["OFFICERS"], ["members"], []), "regional", "Bangkok"),
    ("2027-03-23", None, "Presidential Series", "Members, Spouses, YNG Community & Key Associates", WITH_YNG, "chapter", None),
    ("2027-04-15", None, "A Touch of Harvard Series", "Members, Spouses, YNG Community & Key Associates", WITH_YNG, "chapter", None),
    ("2027-05-03", "2027-05-05", "GLC San Diego", "Elect Officers only", (["OFFICERS"], ["members"], []), "regional", "San Diego"),
    ("2027-05-05", "2027-05-07", "EDGE San Diego", "Members only", (["MEMBERS"], ["members"], []), "regional", "San Diego"),
    ("2027-06-04", "2027-06-06", "Beautiful Gems Series: Toro Toro", "Members & Spouses", MEM_SPOUSES, "chapter", "Toro Toro"),
    ("2027-06-11", None, "Dine Around #4", "Members & Spouses", MEM_SPOUSES, "chapter", None),
]

# Already landed, with scores from YPO Experience Intelligence (overall satisfaction, /5).
LANDED = {
    "Fishing Retreat 2026 | First Cast": (4.9, 9),
    "Day Chair Training": (4.9, 15),
    "Kick Off FY 26-27 | Access the Unexpected": (4.9, 19),
    "Southern Cone Flagship Event: Business Week | Chile is Back": (None, None),
}


def q(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def arr(xs):
    return "ARRAY[" + ",".join(q(x) for x in xs) + "]::text[]" if xs else "'{}'::text[]"


def main():
    out = ["SET search_path = departures;"]
    for i, (s, en, name, aud, (chips, tags, lists), scope, city) in enumerate(EVENTS, start=1):
        code = f"YPO{2600 + i}"
        status, score, n = "scheduled", None, None
        if name in LANDED:
            status = "landed"
            score, n = LANDED[name]
        out.append(
            "INSERT INTO events (code,name,scope,audience_label,chips,tags,mail_lists,start_date,end_date,city,status,score,score_n) VALUES "
            f"({q(code)},{q(name)},{q(scope)},{q(aud)},{arr(chips)},{arr(tags)},{arr(lists if scope == 'chapter' else [])},"
            f"{q(s)},{q(en)},{q(city)},{q(status)},{q(score)},{q(n)}) ON CONFLICT (code) DO NOTHING;")
    print("\n".join(out))


if __name__ == "__main__":
    main()
