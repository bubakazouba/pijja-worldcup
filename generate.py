"""Generate data.json for the Pijja-Palace x World-Cup booking site.

For each WC-2026 weekend (Fri/Sat/Sun) match day, fetch Pijja Palace's REAL
bookable (instant, type="book") 4-top reservation slots from SevenRooms and map
each slot to the game window it falls in, so the site shows "book at X to watch
the Y game." Times are US Pacific (PT).

Run locally or via the daily GitHub Action. Pure stdlib + requests.
"""
import json, time
from datetime import date
import requests

VENUE = "pijjapalacemrktingcrm"
PARTY = 4
API = "https://www.sevenrooms.com/api-yoa/availability/ng/widget/range"
BOOK_URL = "https://www.sevenrooms.com/explore/pijjapalacemrktingcrm/reservations/create/search"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json", "Referer": BOOK_URL}

# WC-2026 weekend match days. Kickoffs in PT. Teams shown where known (R32);
# later rounds are TBD until earlier results are in. 6/27 has no match (excluded).
GAMES = {
    "2026-06-28": {"round": "Round of 32", "windows": [{"ko": "12:00", "teams": "South Africa vs Canada"}]},
    "2026-07-03": {"round": "Round of 32",
                   "windows": [{"ko": "11:00", "teams": "Round of 32"},
                               {"ko": "15:00", "teams": "Round of 32"},
                               {"ko": "18:30", "teams": "Round of 32"}],
                   "day_matches": ["Australia vs Egypt", "Argentina vs Cabo Verde", "Colombia vs Ghana"]},
    "2026-07-04": {"round": "Round of 16", "windows": [{"ko": "10:00", "teams": "TBD"}, {"ko": "14:00", "teams": "TBD"}]},
    "2026-07-05": {"round": "Round of 16", "windows": [{"ko": "13:00", "teams": "TBD"}, {"ko": "17:00", "teams": "TBD"}]},
    "2026-07-10": {"round": "Quarter-final", "windows": [{"ko": "12:00", "teams": "TBD"}]},
    "2026-07-11": {"round": "Quarter-final", "windows": [{"ko": "14:00", "teams": "TBD"}, {"ko": "18:00", "teams": "TBD"}]},
    "2026-07-18": {"round": "Third-place play-off", "windows": [{"ko": "14:00", "teams": "TBD"}]},
    "2026-07-19": {"round": "FINAL", "windows": [{"ko": "12:00", "teams": "TBD"}]},
}
BEFORE_MIN, AFTER_MIN = 90, 30  # bookable window relative to kickoff


def to_min(t):
    t = t.strip()
    if t[-2:].upper() in ("AM", "PM"):
        hm, ap = t[:-2].strip(), t[-2:].upper()
        h, m = map(int, hm.split(":"))
        if ap == "PM" and h != 12: h += 12
        if ap == "AM" and h == 12: h = 0
        return h * 60 + m
    h, m = map(int, t.split(":"))
    return h * 60 + m


def pretty(ko):
    h, m = map(int, ko.split(":"))
    ap = "AM" if h < 12 else "PM"; hh = h % 12 or 12
    return f"{hh}:{m:02d} {ap}"


def bookable(day):
    p = {"venue": VENUE, "party_size": str(PARTY), "halo_size_interval": "100",
         "start_date": day, "num_days": "1", "channel": "SEVENROOMS_WIDGET", "exclude_pdr": "true"}
    try:
        j = requests.get(API, headers=H, params=p, timeout=25).json()
    except Exception:
        return None
    av = (j.get("data") or {}).get("availability") or {}
    out = []
    for _d, shifts in av.items():
        for sh in (shifts if isinstance(shifts, list) else []):
            for t in (sh.get("times") or []):
                if isinstance(t, dict) and t.get("time") and (t.get("type") == "book" or t.get("access_persistent_id")):
                    out.append(t["time"])
    seen = set(); ded = []
    for x in out:
        if x not in seen:
            seen.add(x); ded.append(x)
    return ded


def main():
    today = date.today().isoformat()
    dates_out = []
    for day, info in GAMES.items():
        if day < today:
            continue
        slots = bookable(day)
        wins = []
        for w in info["windows"]:
            km = to_min(w["ko"])
            if slots is None:
                bk = None
            else:
                bk = [s for s in slots if km - BEFORE_MIN <= to_min(s) <= km + AFTER_MIN]
            wins.append({"kickoff": pretty(w["ko"]), "teams": w["teams"], "bookable": bk})
        dates_out.append({
            "date": day,
            "weekday": date.fromisoformat(day).strftime("%A"),
            "pretty_date": date.fromisoformat(day).strftime("%b ") + str(date.fromisoformat(day).day),
            "round": info["round"],
            "day_matches": info.get("day_matches", []),
            "windows": wins,
        })
    data = {
        "venue": "Pijja Palace",
        "blurb": "Indian-Italian sports bar, Silver Lake",
        "address": "2711 W Sunset Blvd, Los Angeles, CA 90026",
        "book_url": BOOK_URL,
        "party_size": PARTY,
        "tz": "Pacific (PT)",
        "window_note": f"Bookable slots shown are within {BEFORE_MIN} min before to {AFTER_MIN} min after kickoff.",
        "generated_at": time.strftime("%Y-%m-%d %H:%M") + " PT",
        "dates": dates_out,
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    n = sum(len([w for w in d["windows"] if w["bookable"]]) for d in dates_out)
    print(f"wrote data.json: {len(dates_out)} dates, {n} game-windows with bookable tables")


if __name__ == "__main__":
    main()
