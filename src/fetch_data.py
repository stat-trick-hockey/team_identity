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
import sys
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone

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

def _fetch_endpoint(endpoint, season="20252026"):
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

def fetch_standings(season="20252026"):
    """
    Fetch standings for a given season.
    For current season uses today's date; for prior seasons uses April 18
    (after regular season ends, before playoffs distort standings).
    Returns {abbr: {"standings_rank": int, "points": int, "wins": int}}
    """
    from datetime import date
    current_season = "20252026"
    if season == current_season:
        standings_date = date.today().isoformat()
    else:
        # Use April 18 of the season end year — safely after regular season
        end_year = int(season[4:8])
        standings_date = f"{end_year}-04-18"

    url = f"{NHL_WEB}/standings/{standings_date}"
    try:
        data = fetch_json(url)
        standings = data.get("standings", [])
        result = {}
        for i, row in enumerate(standings):
            abbr = row.get("teamAbbrev", {})
            if isinstance(abbr, dict):
                abbr = abbr.get("default", "")
            if abbr == "ARI":
                abbr = "UTA"
            if abbr not in TEAMS:
                continue
            result[abbr] = {
                "standings_rank": i + 1,
                "points":         row.get("points", 0),
                "wins":           row.get("wins", 0),
                "gp":             row.get("gamesPlayed", 0),
            }
        print(f"  Standings: {len(result)} teams fetched")
        return result
    except Exception as e:
        print(f"  Warning: standings fetch failed ({e})")
        return {}


def fetch_nhl_team_stats(season="20252026"):
    """
    Pull team stats from confirmed-working NHL API endpoints.

    Confirmed fields (2025-26):
      summary:  faceoffWinPct, gamesPlayed, goalsAgainst, goalsAgainstPerGame,
                goalsFor, goalsForPerGame, penaltyKillPct, powerPlayPct,
                shotsAgainstPerGame, shotsForPerGame, points, wins
      realtime: hits, blockedShots, satPct (Corsi% — best possession proxy)
      penalties: penaltyMinutes
      save%:    derived from summary goalsAgainst / shotsAgainstPerGame * gamesPlayed
    """
    stats = {}

    # ── Summary ───────────────────────────────────────────────────────────────
    for row in _fetch_endpoint("summary", season):
        abbr = _abbr_from_row(row)
        if not abbr:
            continue
        gp  = row.get("gamesPlayed", 0)
        ga  = row.get("goalsAgainst", 0)
        sa  = row.get("shotsAgainstPerGame", 0)
        sa_total = sa * gp
        save_pct = round((sa_total - ga) / sa_total, 4) if sa_total > 0 else 0

        stats[abbr] = {
            "gp":                    gp,
            "goals_per_gp":          row.get("goalsForPerGame", 0),
            "goals_against_per_gp":  row.get("goalsAgainstPerGame", 0),
            "shots_per_gp":          row.get("shotsForPerGame", 0),
            "shots_against":         sa,
            "pp_pct":                row.get("powerPlayPct") or 0,
            "pk_pct":                row.get("penaltyKillPct") or 0,
            "faceoff_pct":           row.get("faceoffWinPct") or 0,
            "points":                row.get("points") or 0,
            "wins":                  row.get("wins") or 0,
            # save% computed after /realtime so we can strip empty-net goals
            "save_pct":              0,
            "_ga_total":             ga,        # scratch field, removed before output
            "_sa_total":             sa * gp,   # scratch field
            # filled by /realtime
            "hits_per_gp":           0,
            "blocks_per_gp":         0,
            "corsi_pct":             0,
            "takeaways_per_gp":      0,
            "giveaways_per_gp":      0,
            "turnover_diff":         0,
            "empty_net_goals":       0,
            # filled by /penalties
            "pim_per_gp":            0,
        }

    if not stats:
        print("  Summary endpoint returned 0 teams")
        return stats
    print(f"  Summary: {len(stats)} teams, save% derived from GA/SA")

    # ── Realtime (hits, blockedShots, satPct/Corsi, takeaways, giveaways, ENG) ─
    for row in _fetch_endpoint("realtime", season):
        abbr = _abbr_from_row(row)
        if not abbr or abbr not in stats:
            continue
        gp = stats[abbr]["gp"] or row.get("gamesPlayed", 1)
        stats[abbr]["hits_per_gp"]       = round(row.get("hits", 0) / gp, 2)
        stats[abbr]["blocks_per_gp"]     = round(row.get("blockedShots", 0) / gp, 2)
        stats[abbr]["corsi_pct"]         = row.get("satPct", 0)
        stats[abbr]["takeaways_per_gp"]  = round(row.get("takeaways", 0) / gp, 2)
        stats[abbr]["giveaways_per_gp"]  = round(row.get("giveaways", 0) / gp, 2)
        stats[abbr]["turnover_diff"]     = round(
            (row.get("takeaways", 0) - row.get("giveaways", 0)) / gp, 2
        )
        stats[abbr]["empty_net_goals"]   = row.get("emptyNetGoals", 0)
    rt_filled = sum(1 for s in stats.values() if s["hits_per_gp"] > 0)
    print(f"  Realtime: {rt_filled} teams (hits, blocks, Corsi%, takeaways/giveaways, ENG)")

    # ── Save% — derived from summary GA/SA with empty-net goals stripped ──────
    for abbr, s in stats.items():
        ga_adj   = s["_ga_total"] - s["empty_net_goals"]
        sa_total = s["_sa_total"]
        s["save_pct"] = round((sa_total - ga_adj) / sa_total, 4) if sa_total > 0 else 0
    sv_filled = sum(1 for s in stats.values() if s["save_pct"] > 0)
    print(f"  Save%: {sv_filled} teams (ENG-adjusted from GA/SA)")

    # ── Penalties (PIM) ───────────────────────────────────────────────────────
    for row in _fetch_endpoint("penalties", season):
        abbr = _abbr_from_row(row)
        if not abbr or abbr not in stats:
            continue
        gp  = stats[abbr]["gp"] or row.get("gamesPlayed", 1)
        pim = row.get("penaltyMinutes", 0)
        stats[abbr]["pim_per_gp"] = round(pim / gp, 2) if pim else 0
    pim_filled = sum(1 for s in stats.values() if s["pim_per_gp"] > 0)
    print(f"  Penalties: {pim_filled} teams (PIM/GP)")

    print(f"  Final: {len(stats)} teams merged")
    return stats


def fetch_nst_team_stats():
    """
    Pull Natural Stat Trick team data.
    - Possession: shot share from NHL API
    - Transition: rush shot attempts for per 60 scraped from NST teamtable
    - Finishing: shooting % from NHL API
    
    NST teamtable URL (all situations, current season, regular season):
    https://www.naturalstattrick.com/teamtable.php?fromseason=20252026&thruseason=20252026&stype=2&sit=all&score=all&rate=y&team=all&loc=B&gpf=410&fd=&td=
    
    The table is HTML — we parse the Rush SF/60 column (column index varies by
    sort; we locate it by header text).
    """
    import html
    import re

    # ── NHL API for possession + finishing ───────────────────────────────────
    sat_url = (f"{NHL_API}/team/summary?isAggregate=false&isGame=false"
               f"&sort=teamFullName&start=0&limit=50"
               f"&cayenneExp=gameTypeId=2%20and%20seasonId=20252026")
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
        "?fromseason=20252026&thruseason=20252026&stype=2&sit=all"
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
            # Log what we actually got to diagnose the failure
            print(f"  NST response length: {len(body)} chars")
            print(f"  NST first 300 chars: {body[:300]!r}")
            all_table_ids = re.findall(r'<table[^>]*id=["\']([^"\']+)["\']', body, re.IGNORECASE)
            print(f"  NST table IDs found: {all_table_ids}")
            for kw in ["cloudflare", "captcha", "blocked", "login", "sign in", "javascript"]:
                if kw.lower() in body.lower():
                    print(f"  NST ⚠ keyword in response: '{kw}'")
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

        # Possession: use Corsi% (satPct) from /realtime — best available proxy.
        # Falls back to shots-for share if corsi unavailable.
        corsi = n.get("corsi_pct", 0)
        if not corsi and n.get("shots_per_gp") and n.get("shots_against"):
            sf = n.get("shots_per_gp", 0)
            sa = n.get("shots_against", 0)
            corsi = sf / (sf + sa) if (sf + sa) > 0 else 0.5

        # Shooting%: goals-for / shots-for
        gf  = n.get("goals_per_gp", 0)
        sf  = n.get("shots_per_gp", 1)
        shooting_pct = s.get("shooting_pct") or (gf / sf if sf else 0)

        dims[abbr] = {
            # 1. Possession — Corsi% (shot attempt share all-sit) from /realtime
            "possession":     corsi,
            # 2. Transition — takeaways per GP from /realtime.
            #    Direct measure of puck-winning; always positive, no asymmetry issues.
            "transition":     n.get("takeaways_per_gp", 0),
            # 3. Finishing — shooting %
            "finishing":      shooting_pct,
            # 4. Physical — hits + blocked shots per GP
            "physical":       n.get("hits_per_gp", 0) * 0.6 + n.get("blocks_per_gp", 0) * 0.4,
            # 5. Discipline — PIM/GP (70%) + giveaways/GP (30%), both inverted.
            #    Captures both penalty-taking and puck-management carelessness.
            "discipline_raw": n.get("pim_per_gp", 0) * 0.7 + n.get("giveaways_per_gp", 0) * 0.3,
            # 6. Goaltending — ENG-adjusted save% (empty net goals stripped from GA)
            "goaltending":    n.get("save_pct", 0),
            # 7. Defensive — raw shots against/GP (inverted after normalization)
            "defensive_raw":  n.get("shots_against", 0),
        }
    return dims

# ── Season config ─────────────────────────────────────────────────────────────
SEASON_CONFIG = {
    "20252026": {"label": "2025-26", "out": "data/team_identity.json"},
    "20242025": {"label": "2024-25", "out": "data/team_identity_2425.json"},
}

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="20252026",
                        help="NHL season ID e.g. 20252026 (default) or 20242025")
    args = parser.parse_args()
    season = args.season

    cfg = SEASON_CONFIG.get(season)
    if not cfg:
        raise ValueError(f"Unknown season '{season}'. Add it to SEASON_CONFIG.")

    print(f"Fetching NHL API team stats for {cfg['label']}...")
    nhl = fetch_nhl_team_stats(season)
    time.sleep(0.5)

    print("Fetching standings...")
    standings = fetch_standings(season)
    time.sleep(0.5)

    print("Fetching possession/finishing stats...")
    nst = fetch_nst_team_stats()

    print(f"  Got data for {len(nhl)} teams (NHL API), {len(nst)} teams (NST proxy)")

    if len(nhl) < 20:
        raise RuntimeError(
            f"NHL API returned only {len(nhl)} teams (expected ~32). "
            "Not writing output — check API availability."
        )

    raw = build_dimensions(nhl, nst)

    # Strip internal scratch fields before output
    for s in nhl.values():
        s.pop("_ga_total", None)
        s.pop("_sa_total", None)
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
            "generated": datetime.now(timezone.utc).isoformat(),
            "season": cfg["label"],
            "season_id": season,
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
                "corsi_pct":             round(r["possession"], 4),
                "turnover_diff":         round(nhl.get(abbr, {}).get("turnover_diff", 0), 2),
                "takeaways_per_gp":      round(nhl.get(abbr, {}).get("takeaways_per_gp", 0), 2),
                "giveaways_per_gp":      round(nhl.get(abbr, {}).get("giveaways_per_gp", 0), 2),
                "empty_net_goals":       nhl.get(abbr, {}).get("empty_net_goals", 0),
                "shooting_pct":          round(r["finishing"], 4),
                "hits_per_gp":           round(nhl.get(abbr, {}).get("hits_per_gp", 0), 2),
                "blocks_per_gp":         round(nhl.get(abbr, {}).get("blocks_per_gp", 0), 2),
                "pim_per_gp":            round(nhl.get(abbr, {}).get("pim_per_gp", 0), 2),
                "save_pct":              round(r["goaltending"], 4),
                "shots_against_per_gp":  round(r["defensive_raw"], 2),
                "pp_pct":                round(nhl.get(abbr, {}).get("pp_pct", 0), 2),
                "pk_pct":                round(nhl.get(abbr, {}).get("pk_pct", 0), 2),
            },
            "ranks": ranks[abbr],
            "gp": nhl.get(abbr, {}).get("gp", 0),
            "standings_rank": standings.get(abbr, {}).get("standings_rank", None),
            "points":         standings.get(abbr, {}).get("points", None),
            "wins":           standings.get(abbr, {}).get("wins", None),
        }

    out_path = cfg["out"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Written to {out_path} ({len(output['teams'])} teams)")
    print(f"  Season: {output['meta']['season']}")
    print(f"  Generated: {output['meta']['generated']}")

if __name__ == "__main__":
    main()
