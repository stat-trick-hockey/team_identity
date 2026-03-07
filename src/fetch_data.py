"""
NHL Team Identity — Data Fetch & Normalization
Pulls 5v5 team stats from Natural Stat Trick and NHL API,
normalizes each dimension to 0–1 relative to league min/max,
and writes data/team_identity.json.

Sources:
  - Natural Stat Trick (NST) team summary: 5v5 CF%, xGF%, HDCF%
  - NHL API: hits, blocked shots, PIM, power play, penalty kill, save%
"""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime

# ── Team metadata ────────────────────────────────────────────────────────────
TEAMS = {
    "ANA": {"name": "Anaheim Ducks",        "primary": "#F47A38", "secondary": "#B9975B"},
    "ARI": {"name": "Utah Hockey Club",      "primary": "#6CACE4", "secondary": "#1C4B82"},
    "BOS": {"name": "Boston Bruins",         "primary": "#FFB81C", "secondary": "#000000"},
    "BUF": {"name": "Buffalo Sabres",        "primary": "#003087", "secondary": "#FFB81C"},
    "CGY": {"name": "Calgary Flames",        "primary": "#C8102E", "secondary": "#F1BE48"},
    "CAR": {"name": "Carolina Hurricanes",   "primary": "#CC0000", "secondary": "#000000"},
    "CHI": {"name": "Chicago Blackhawks",    "primary": "#CF0A2C", "secondary": "#000000"},
    "COL": {"name": "Colorado Avalanche",    "primary": "#6F263D", "secondary": "#236192"},
    "CBJ": {"name": "Columbus Blue Jackets", "primary": "#002654", "secondary": "#CE1126"},
    "DAL": {"name": "Dallas Stars",          "primary": "#006847", "secondary": "#8F8F8C"},
    "DET": {"name": "Detroit Red Wings",     "primary": "#CE1126", "secondary": "#FFFFFF"},
    "EDM": {"name": "Edmonton Oilers",       "primary": "#FF4C00", "secondary": "#041E42"},
    "FLA": {"name": "Florida Panthers",      "primary": "#041E42", "secondary": "#C8102E"},
    "LAK": {"name": "Los Angeles Kings",     "primary": "#111111", "secondary": "#A2AAAD"},
    "MIN": {"name": "Minnesota Wild",        "primary": "#154734", "secondary": "#A6192E"},
    "MTL": {"name": "Montreal Canadiens",    "primary": "#AF1E2D", "secondary": "#192168"},
    "NSH": {"name": "Nashville Predators",   "primary": "#FFB81C", "secondary": "#041E42"},
    "NJD": {"name": "New Jersey Devils",     "primary": "#CE1126", "secondary": "#000000"},
    "NYI": {"name": "New York Islanders",    "primary": "#003087", "secondary": "#FC4C02"},
    "NYR": {"name": "New York Rangers",      "primary": "#0038A8", "secondary": "#CE1126"},
    "OTT": {"name": "Ottawa Senators",       "primary": "#C8102E", "secondary": "#C69214"},
    "PHI": {"name": "Philadelphia Flyers",   "primary": "#F74902", "secondary": "#000000"},
    "PIT": {"name": "Pittsburgh Penguins",   "primary": "#FCB514", "secondary": "#000000"},
    "SEA": {"name": "Seattle Kraken",        "primary": "#001628", "secondary": "#99D9D9"},
    "SJS": {"name": "San Jose Sharks",       "primary": "#006D75", "secondary": "#EA7200"},
    "STL": {"name": "St. Louis Blues",       "primary": "#002F87", "secondary": "#FCB514"},
    "TBL": {"name": "Tampa Bay Lightning",   "primary": "#002868", "secondary": "#FFFFFF"},
    "TOR": {"name": "Toronto Maple Leafs",   "primary": "#003E7E", "secondary": "#FFFFFF"},
    "VAN": {"name": "Vancouver Canucks",     "primary": "#00205B", "secondary": "#00843D"},
    "VGK": {"name": "Vegas Golden Knights",  "primary": "#B4975A", "secondary": "#333F48"},
    "WSH": {"name": "Washington Capitals",   "primary": "#041E42", "secondary": "#C8102E"},
    "WPG": {"name": "Winnipeg Jets",         "primary": "#041E42", "secondary": "#004C97"},
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "nhl-team-identity/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def normalize(values: dict) -> dict:
    """Min-max normalize a dict of {key: float} → {key: 0–1 float}."""
    lo, hi = min(values.values()), max(values.values())
    rng = hi - lo if hi != lo else 1
    return {k: round((v - lo) / rng, 4) for k, v in values.items()}

def rank(values: dict, higher_is_better=True) -> dict:
    """Return 1-based rank for each team (1 = best)."""
    sorted_teams = sorted(values, key=values.get, reverse=higher_is_better)
    return {t: i + 1 for i, t in enumerate(sorted_teams)}

# ── NHL Stats API ─────────────────────────────────────────────────────────────
NHL_API = "https://api.nhle.com/stats/rest/en"
NHL_WEB = "https://api-web.nhle.com/v1"

# Map full team names (as returned by NHL API) to our abbrevs
NHL_NAME_TO_ABBR = {
    "Anaheim Ducks": "ANA", "Utah Hockey Club": "UTA", "Boston Bruins": "BOS",
    "Buffalo Sabres": "BUF", "Calgary Flames": "CGY", "Carolina Hurricanes": "CAR",
    "Chicago Blackhawks": "CHI", "Colorado Avalanche": "COL",
    "Columbus Blue Jackets": "CBJ", "Dallas Stars": "DAL", "Detroit Red Wings": "DET",
    "Edmonton Oilers": "EDM", "Florida Panthers": "FLA", "Los Angeles Kings": "LAK",
    "Minnesota Wild": "MIN", "Montréal Canadiens": "MTL", "Montreal Canadiens": "MTL",
    "Nashville Predators": "NSH", "New Jersey Devils": "NJD",
    "New York Islanders": "NYI", "New York Rangers": "NYR", "Ottawa Senators": "OTT",
    "Philadelphia Flyers": "PHI", "Pittsburgh Penguins": "PIT", "Seattle Kraken": "SEA",
    "San Jose Sharks": "SJS", "St. Louis Blues": "STL", "Tampa Bay Lightning": "TBL",
    "Toronto Maple Leafs": "TOR", "Vancouver Canucks": "VAN",
    "Vegas Golden Knights": "VGK", "Washington Capitals": "WSH", "Winnipeg Jets": "WPG",
    # Legacy / alternate spellings
    "Arizona Coyotes": "UTA",
}

def _fetch_endpoint(endpoint, season="20242025"):
    """Fetch a /team/<endpoint> stats page, return list of rows."""
    url = (f"{NHL_API}/team/{endpoint}?isAggregate=false&isGame=false"
           f"&sort=teamFullName&start=0&limit=50"
           f"&cayenneExp=gameTypeId=2%20and%20seasonId={season}")
    try:
        data = fetch_json(url)
        return data.get("data", [])
    except Exception as e:
        print(f"  Warning: failed to fetch /team/{endpoint}: {e}")
        return []

def _abbr_from_row(row):
    """Extract our team abbrev from an API row using name or triCode fields."""
    # Try direct abbrev fields first
    for key in ("teamAbbrev", "triCode", "teamTricode"):
        val = row.get(key)
        if val:
            if val == "ARI":
                val = "UTA"
            if val in TEAMS:
                return val
    # Fall back to full name lookup
    for key in ("teamFullName", "teamName", "fullName"):
        name = row.get(key, "")
        abbr = NHL_NAME_TO_ABBR.get(name)
        if abbr:
            return abbr
    return None

def fetch_nhl_team_stats(season="20242025"):
    """
    Pull team stats from multiple NHL API endpoints and merge by team.
    Endpoints used:
      summary   — GP, goals, PP%, PK%
      hits      — hits per game
      blockshots — blocked shots per game
      penalties  — PIM per game
      goalie    — team save %
    """
    stats = {}

    # ── Summary (GP, goals, PP, PK) ──────────────────────────────────────────
    for row in _fetch_endpoint("summary", season):
        abbr = _abbr_from_row(row)
        if not abbr:
            continue
        stats[abbr] = {
            "gp":           row.get("gamesPlayed", 0),
            "goals_per_gp": row.get("goalsForPerGame", 0),
            "goals_against_per_gp": row.get("goalsAgainstPerGame", 0),
            "shots_per_gp": row.get("shotsForPerGame", 0),
            "shots_against": row.get("shotsAgainstPerGame", 0),
            "pp_pct":       row.get("penaltyKillPct", 0),   # note: field swap below
            "pk_pct":       row.get("penaltyKillPct", 0),
            # will be filled by other endpoints
            "hits_per_gp":   0,
            "blocks_per_gp": 0,
            "pim_per_gp":    0,
            "save_pct":      0,
        }
        # PP% and PK% live in separate fields
        stats[abbr]["pp_pct"] = row.get("powerPlayPct") or row.get("ppPct") or 0
        stats[abbr]["pk_pct"] = row.get("penaltyKillPct") or row.get("pkPct") or 0

    if stats:
        sample = list(stats.values())[0]
        print(f"  Summary: {len(stats)} teams, sample GP={sample['gp']}")
    else:
        print("  Summary endpoint returned 0 teams — printing raw sample")
        rows = _fetch_endpoint("summary", season)
        if rows:
            print(f"  Raw row keys: {list(rows[0].keys())}")
            print(f"  Raw row sample: {rows[0]}")
        return stats

    # ── Hits ─────────────────────────────────────────────────────────────────
    for row in _fetch_endpoint("hits", season):
        abbr = _abbr_from_row(row)
        if abbr and abbr in stats:
            gp = stats[abbr]["gp"] or row.get("gamesPlayed", 1)
            hits = row.get("hits", 0) or row.get("hitsPerGame", 0)
            # If value looks like a total (>100), convert to per-game
            stats[abbr]["hits_per_gp"] = hits / gp if hits > 10 else hits

    # ── Blocked shots ─────────────────────────────────────────────────────────
    for row in _fetch_endpoint("blockshots", season):
        abbr = _abbr_from_row(row)
        if abbr and abbr in stats:
            gp = stats[abbr]["gp"] or row.get("gamesPlayed", 1)
            blocks = row.get("blockedShots", 0) or row.get("blockedShotsPerGame", 0)
            stats[abbr]["blocks_per_gp"] = blocks / gp if blocks > 10 else blocks

    # ── Penalties ─────────────────────────────────────────────────────────────
    for row in _fetch_endpoint("penalties", season):
        abbr = _abbr_from_row(row)
        if abbr and abbr in stats:
            gp = stats[abbr]["gp"] or row.get("gamesPlayed", 1)
            pim = row.get("penaltyMinutes", 0) or row.get("pim", 0) or row.get("penaltyMinutesPerGame", 0)
            stats[abbr]["pim_per_gp"] = pim / gp if pim > 10 else pim

    # ── Save % (goalie summary — team totals) ─────────────────────────────────
    for row in _fetch_endpoint("goaliestats", season):
        abbr = _abbr_from_row(row)
        if abbr and abbr in stats:
            sv = row.get("savePct") or row.get("savePctg") or row.get("savePercentage") or 0
            if sv and stats[abbr]["save_pct"] == 0:
                stats[abbr]["save_pct"] = sv

    # Fallback save% from shots if goaliestats didn't populate
    for abbr, s in stats.items():
        if s["save_pct"] == 0 and s.get("shots_against", 0) > 0:
            # Approximate: (SA - GA) / SA
            ga_total = s["goals_against_per_gp"] * s["gp"]
            sa_total = s["shots_against"] * s["gp"]
            if sa_total > 0:
                s["save_pct"] = round((sa_total - ga_total) / sa_total, 4)

    print(f"  Final: {len(stats)} teams merged across endpoints")
    return stats

def fetch_nst_team_stats():
    """
    Pull Natural Stat Trick team data.
    - Possession: shot share from NHL API
    - Transition: rush shot attempts for per 60 scraped from NST teamtable
    - Finishing: shooting % from NHL API
    
    NST teamtable URL (all situations, current season, regular season):
    https://www.naturalstattrick.com/teamtable.php?fromseason=20242025&thruseason=20242025&stype=2&sit=all&score=all&rate=y&team=all&loc=B&gpf=410&fd=&td=
    
    The table is HTML — we parse the Rush SF/60 column (column index varies by
    sort; we locate it by header text).
    """
    import html
    import re

    # ── NHL API for possession + finishing ───────────────────────────────────
    sat_url = (f"{NHL_API}/team/summary?isAggregate=false&isGame=false"
               f"&sort=teamFullName&start=0&limit=50"
               f"&cayenneExp=gameTypeId=2%20and%20seasonId=20242025")
    data = fetch_json(sat_url)

    stats = {}
    for row in data.get("data", []):
        abbr = row.get("teamAbbrev")
        if abbr and abbr in TEAMS:
            gf = row.get("goalsForPerGame", 0)
            sf = row.get("shotsForPerGame", 0)
            sa = row.get("shotsAgainstPerGame", 1)
            possession    = sf / (sf + sa) if (sf + sa) > 0 else 0.5
            shooting_pct  = gf / sf if sf > 0 else 0
            stats[abbr] = {
                "possession_proxy":  possession,
                "shooting_pct":      shooting_pct,
                "rush_sf60":         None,   # filled below
                "gf_per_gp":         gf,
                "sf_per_gp":         sf,
                "sa_per_gp":         sa,
            }

    # ── NST teamtable: Rush SF/60 ─────────────────────────────────────────────
    # NST team abbreviations differ slightly from NHL API — map the ones that
    # diverge (NST uses full names in some columns; we match on team name).
    NST_URL = (
        "https://www.naturalstattrick.com/teamtable.php"
        "?fromseason=20242025&thruseason=20242025&stype=2&sit=all"
        "&score=all&rate=y&team=all&loc=B&gpf=410&fd=&td="
    )
    try:
        req = urllib.request.Request(
            NST_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; nhl-team-identity/1.0)",
                "Accept": "text/html",
            }
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode("utf-8", errors="replace")

        # Find the data table — NST renders it with id="teams"
        table_match = re.search(r'<table[^>]*id=["\']teams["\'][^>]*>(.*?)</table>',
                                body, re.DOTALL | re.IGNORECASE)
        if not table_match:
            raise ValueError("NST team table not found in response")

        table_html = table_match.group(1)

        # Parse header row to locate "Rush SF/60" column index
        header_match = re.search(r'<thead>(.*?)</thead>', table_html, re.DOTALL | re.IGNORECASE)
        if not header_match:
            raise ValueError("NST table header not found")

        headers = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', 
                             header_match.group(1), re.DOTALL | re.IGNORECASE)
        headers = [re.sub(r'<[^>]+>', '', h).strip() for h in headers]

        # Column names to try (NST has changed these over the years)
        rush_col_candidates = ["Rush SF/60", "Rush SA/60", "Rush CF/60", "RSF/60", "Rush Sh/60"]
        rush_col_idx = None
        for candidate in rush_col_candidates:
            for i, h in enumerate(headers):
                if candidate.lower() in h.lower():
                    rush_col_idx = i
                    break
            if rush_col_idx is not None:
                break

        if rush_col_idx is None:
            raise ValueError(f"Rush SF/60 column not found. Headers: {headers}")

        # Team name column — NST uses full names, index 0 or 1
        team_col_idx = next((i for i, h in enumerate(headers)
                             if "team" in h.lower()), 1)

        # Parse data rows
        tbody_match = re.search(r'<tbody>(.*?)</tbody>', table_html, re.DOTALL | re.IGNORECASE)
        if not tbody_match:
            raise ValueError("NST table body not found")

        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_match.group(1),
                          re.DOTALL | re.IGNORECASE)

        # Build a name→abbr lookup
        name_to_abbr = {v["name"].lower(): k for k, v in TEAMS.items()}

        for row_html in rows:
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row_html,
                               re.DOTALL | re.IGNORECASE)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            if len(cells) <= max(team_col_idx, rush_col_idx):
                continue

            team_name = html.unescape(cells[team_col_idx]).strip().lower()
            rush_val_str = html.unescape(cells[rush_col_idx]).strip()

            # Match team name to abbr
            abbr = name_to_abbr.get(team_name)
            if abbr is None:
                # Fuzzy: try contains match
                abbr = next((a for n, a in name_to_abbr.items()
                             if n in team_name or team_name in n), None)
            if abbr is None or abbr not in stats:
                continue

            try:
                stats[abbr]["rush_sf60"] = float(rush_val_str)
            except ValueError:
                pass

        fetched = sum(1 for v in stats.values() if v.get("rush_sf60") is not None)
        print(f"  NST rush SF/60: fetched for {fetched}/{len(stats)} teams")

    except Exception as e:
        print(f"  Warning: NST scrape failed ({e}). Transition will use GF/SA proxy.")

    return stats

# ── Dimension builders ────────────────────────────────────────────────────────
def build_dimensions(nhl: dict, nst: dict) -> dict:
    """
    Combine raw stats into 7 identity dimensions per team.
    Returns {abbr: {dim: raw_value}} before normalization.
    """
    dims = {}
    for abbr in TEAMS:
        n = nhl.get(abbr, {})
        s = nst.get(abbr, {})
        if not n and not s:
            continue
        dims[abbr] = {
            # 1. Possession — shot share proxy
            "possession":   s.get("possession_proxy", 0.5),
            # 2. Transition — rush shot attempts for per 60 (NST); falls back to
            #    GF/SA rate proxy if NST scrape failed
            "transition":   (s.get("rush_sf60") if s.get("rush_sf60") is not None
                             else (s.get("gf_per_gp", 0) / max(s.get("sa_per_gp", 30), 1)) * 10),
            # 3. Finishing — shooting percentage (goals / shots on goal)
            "finishing":    s.get("shooting_pct", 0),
            # 4. Physical — hits + blocked shots per gp combined
            "physical":     n.get("hits_per_gp", 0) * 0.6 + n.get("blocks_per_gp", 0) * 0.4,
            # 5. Discipline — inverse of PIM (lower PIM = more disciplined)
            #    We'll invert after normalization
            "discipline_raw": n.get("pim_per_gp", 0),
            # 6. Goaltending — save %
            "goaltending":  n.get("save_pct", 0),
            # 7. Defensive structure — inverse of shots against per gp
            "defensive_raw": n.get("shots_against", 0),
        }
    return dims

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("Fetching NHL API team stats...")
    nhl = fetch_nhl_team_stats()
    time.sleep(0.5)

    print("Fetching possession/finishing stats...")
    nst = fetch_nst_team_stats()

    print(f"  Got data for {len(nhl)} teams (NHL API), {len(nst)} teams (NST proxy)")

    if len(nhl) < 20:
        print(f"  NHL API returned only {len(nhl)} teams (expected ~32) — falling back to seed file.")
        seed_path = "data/team_identity.json"
        if os.path.exists(seed_path):
            print(f"  Seed file found, keeping existing data.")
            return
        else:
            raise RuntimeError(
                f"NHL API returned {len(nhl)} teams and no seed file exists. "
                "Run src/generate_seed.py first to create data/team_identity.json."
            )

    raw = build_dimensions(nhl, nst)
    teams_with_data = list(raw.keys())

    # Extract per-dimension raw dicts for normalization
    def dim_vals(key):
        return {t: raw[t][key] for t in teams_with_data}

    possession_n   = normalize(dim_vals("possession"))
    transition_n   = normalize(dim_vals("transition"))
    finishing_n    = normalize(dim_vals("finishing"))
    physical_n     = normalize(dim_vals("physical"))
    goaltending_n  = normalize(dim_vals("goaltending"))

    # Discipline: invert (lower PIM = more disciplined = higher score)
    disc_raw = dim_vals("discipline_raw")
    disc_inverted = {t: -v for t, v in disc_raw.items()}
    discipline_n = normalize(disc_inverted)

    # Defensive structure: invert shots against (fewer = better structure)
    def_raw = dim_vals("defensive_raw")
    def_inverted = {t: -v for t, v in def_raw.items()}
    defensive_n = normalize(def_inverted)

    # Ranks (1 = best in league)
    ranks = {t: {
        "possession":  rank(possession_n)[t],
        "transition":  rank(transition_n)[t],
        "finishing":   rank(finishing_n)[t],
        "physical":    rank(physical_n)[t],
        "discipline":  rank(discipline_n)[t],
        "goaltending": rank(goaltending_n)[t],
        "defensive":   rank(defensive_n)[t],
    } for t in teams_with_data}

    # Assemble final output
    output = {
        "meta": {
            "generated": datetime.utcnow().isoformat() + "Z",
            "season": "2024-25",
            "situation": "All situations (NHL API)",
            "dimensions": ["possession", "transition", "finishing", "physical",
                           "discipline", "goaltending", "defensive"],
            "note": "Scores normalized 0–1 relative to league min/max this season."
        },
        "teams": {}
    }

    for abbr in teams_with_data:
        meta = TEAMS[abbr]
        r = raw[abbr]
        output["teams"][abbr] = {
            "name":      meta["name"],
            "abbr":      abbr,
            "primary":   meta["primary"],
            "secondary": meta["secondary"],
            "scores": {
                "possession":  possession_n.get(abbr, 0),
                "transition":  transition_n.get(abbr, 0),
                "finishing":   finishing_n.get(abbr, 0),
                "physical":    physical_n.get(abbr, 0),
                "discipline":  discipline_n.get(abbr, 0),
                "goaltending": goaltending_n.get(abbr, 0),
                "defensive":   defensive_n.get(abbr, 0),
            },
            "raw": {
                "possession_shot_share": round(r["possession"], 4),
                "rush_sf60":             round(nst.get(abbr, {}).get("rush_sf60") or 0, 2),
                "shooting_pct":          round(r["finishing"], 4),
                "hits_per_gp":           round(nhl.get(abbr, {}).get("hits_per_gp", 0), 2),
                "blocks_per_gp":         round(nhl.get(abbr, {}).get("blocks_per_gp", 0), 2),
                "pim_per_gp":            round(r["discipline_raw"], 2),
                "save_pct":              round(r["goaltending"], 4),
                "shots_against_per_gp":  round(r["defensive_raw"], 2),
                "pp_pct":                round(nhl.get(abbr, {}).get("pp_pct", 0), 2),
                "pk_pct":                round(nhl.get(abbr, {}).get("pk_pct", 0), 2),
            },
            "ranks": ranks[abbr],
            "gp": nhl.get(abbr, {}).get("gp", 0),
        }

    out_path = "data/team_identity.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Written to {out_path} ({len(output['teams'])} teams)")
    print(f"  Season: {output['meta']['season']}")
    print(f"  Generated: {output['meta']['generated']}")

if __name__ == "__main__":
    main()
