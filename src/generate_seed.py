"""Generate realistic 2025-26 NHL team identity seed data."""
import json, random
from datetime import datetime

random.seed(42)

TEAMS = {
    "ANA": {"name": "Anaheim Ducks",        "primary": "#F47A38", "secondary": "#B9975B"},
    "UTA": {"name": "Utah Hockey Club",      "primary": "#6CACE4", "secondary": "#1C4B82"},
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

# Archetype seeds — realistic 2024-25 profiles
# Dimensions: (possession, transition_rush_sf60, finishing_sh_pct, physical, discipline, goaltending, defensive)
# transition is now Rush SF/60 — typical NHL range ~8.0–14.0, stored as raw then normalized
ARCHETYPES = {
    # Fast/transition offenses: EDM, WSH, COL have high rush shot rates
    # Possession/structure teams: CAR, MIN, LAK, DAL generate less off rush
    "FLA": (0.88, 11.2, 0.85, 0.55, 0.70, 0.91, 0.82),
    "WSH": (0.54, 13.4, 0.92, 0.60, 0.65, 0.78, 0.55),
    "DAL": (0.82, 10.1, 0.78, 0.62, 0.80, 0.88, 0.85),
    "EDM": (0.72, 14.1, 0.98, 0.45, 0.55, 0.70, 0.50),
    "TOR": (0.76, 12.0, 0.88, 0.38, 0.72, 0.75, 0.62),
    "CAR": (0.85,  9.5, 0.70, 0.75, 0.85, 0.85, 0.90),
    "COL": (0.79, 13.5, 0.82, 0.50, 0.60, 0.72, 0.65),
    "VGK": (0.80,  9.8, 0.75, 0.65, 0.88, 0.84, 0.80),
    "WPG": (0.83, 11.0, 0.80, 0.70, 0.75, 0.89, 0.78),
    "NYR": (0.74, 11.8, 0.76, 0.58, 0.68, 0.92, 0.75),
    "MIN": (0.78,  8.8, 0.68, 0.80, 0.82, 0.80, 0.88),
    "NJD": (0.71, 12.6, 0.72, 0.55, 0.62, 0.74, 0.70),
    "BOS": (0.75,  9.2, 0.74, 0.82, 0.78, 0.82, 0.82),
    "TBL": (0.73, 12.2, 0.79, 0.48, 0.70, 0.76, 0.68),
    "LAK": (0.80,  8.4, 0.65, 0.72, 0.86, 0.86, 0.87),
    "OTT": (0.68, 11.4, 0.70, 0.60, 0.58, 0.68, 0.62),
    "SEA": (0.70, 10.5, 0.66, 0.65, 0.72, 0.78, 0.72),
    "STL": (0.65,  9.0, 0.65, 0.88, 0.72, 0.75, 0.74),
    "VAN": (0.72, 11.6, 0.74, 0.52, 0.66, 0.80, 0.70),
    "NSH": (0.60,  9.6, 0.62, 0.85, 0.76, 0.72, 0.76),
    "CGY": (0.64, 10.8, 0.68, 0.72, 0.68, 0.70, 0.65),
    "BUF": (0.62, 12.4, 0.72, 0.58, 0.60, 0.65, 0.58),
    "PHI": (0.58, 10.6, 0.60, 0.82, 0.55, 0.68, 0.60),
    "NYI": (0.60,  8.2, 0.58, 0.78, 0.80, 0.76, 0.82),
    "MTL": (0.56, 11.0, 0.64, 0.55, 0.64, 0.66, 0.58),
    "DET": (0.58, 10.2, 0.62, 0.62, 0.65, 0.70, 0.62),
    "PIT": (0.55, 11.3, 0.66, 0.50, 0.60, 0.68, 0.55),
    "UTA": (0.62, 10.0, 0.66, 0.60, 0.66, 0.72, 0.64),
    "CBJ": (0.50,  9.0, 0.54, 0.75, 0.62, 0.62, 0.55),
    "ANA": (0.48,  8.6, 0.50, 0.68, 0.68, 0.60, 0.52),
    "SJS": (0.44,  8.0, 0.48, 0.60, 0.70, 0.55, 0.45),
    "CHI": (0.46,  9.2, 0.52, 0.55, 0.58, 0.58, 0.48),
}

DIMS = ["possession", "transition", "finishing", "physical", "discipline", "goaltending", "defensive"]

def normalize(values):
    lo, hi = min(values.values()), max(values.values())
    rng = hi - lo if hi != lo else 1
    return {k: round((v - lo) / rng, 4) for k, v in values.items()}

def rank_dict(values, higher_is_better=True):
    sorted_teams = sorted(values, key=values.get, reverse=higher_is_better)
    return {t: i + 1 for i, t in enumerate(sorted_teams)}

# Build raw scores — transition is raw rush SF/60, others are 0–1 archetypes
raw = {}
for abbr, arch in ARCHETYPES.items():
    raw[abbr] = {
        "possession":  arch[0] + random.gauss(0, 0.02),
        "transition":  arch[1] + random.gauss(0, 0.15),   # rush SF/60, real units
        "finishing":   arch[2] + random.gauss(0, 0.02),
        "physical":    arch[3] + random.gauss(0, 0.02),
        "discipline":  arch[4] + random.gauss(0, 0.02),
        "goaltending": arch[5] + random.gauss(0, 0.02),
        "defensive":   arch[6] + random.gauss(0, 0.02),
    }

# Normalize each dimension (transition normalizes from its actual rush SF/60 range)
norm = {d: normalize({t: raw[t][d] for t in raw}) for d in DIMS}
ranks = {d: rank_dict(norm[d]) for d in DIMS}

# Raw stat approximations
def raw_stats(abbr):
    r = raw[abbr]
    return {
        "possession_shot_share": round(0.44 + r["possession"] * 0.12, 4),
        "rush_sf60":             round(r["transition"], 2),          # actual rush SF/60
        "shooting_pct":          round(0.07 + r["finishing"] * 0.05, 4),
        "hits_per_gp":           round(15 + r["physical"] * 12, 1),
        "blocks_per_gp":         round(8 + r["physical"] * 8, 1),
        "pim_per_gp":            round(10 - r["discipline"] * 4, 2),
        "save_pct":              round(0.880 + r["goaltending"] * 0.03, 4),
        "shots_against_per_gp":  round(35 - r["defensive"] * 10, 1),
        "pp_pct":                round(14 + r["finishing"] * 10, 1),
        "pk_pct":                round(75 + r["discipline"] * 8, 1),
    }

# Approximate 2025-26 standings ranks (points-based, realistic estimates)
STANDINGS_RANKS = {
    "FLA": {"standings_rank": 1,  "points": 98,  "wins": 46},
    "WPG": {"standings_rank": 2,  "points": 94,  "wins": 44},
    "CAR": {"standings_rank": 3,  "points": 93,  "wins": 43},
    "DAL": {"standings_rank": 4,  "points": 91,  "wins": 42},
    "COL": {"standings_rank": 5,  "points": 89,  "wins": 41},
    "LAK": {"standings_rank": 6,  "points": 87,  "wins": 40},
    "MIN": {"standings_rank": 7,  "points": 86,  "wins": 40},
    "VGK": {"standings_rank": 8,  "points": 85,  "wins": 39},
    "EDM": {"standings_rank": 9,  "points": 84,  "wins": 39},
    "NYR": {"standings_rank": 10, "points": 83,  "wins": 38},
    "TBL": {"standings_rank": 11, "points": 82,  "wins": 38},
    "TOR": {"standings_rank": 12, "points": 81,  "wins": 37},
    "BOS": {"standings_rank": 13, "points": 80,  "wins": 37},
    "VAN": {"standings_rank": 14, "points": 78,  "wins": 36},
    "NJD": {"standings_rank": 15, "points": 76,  "wins": 35},
    "WSH": {"standings_rank": 16, "points": 75,  "wins": 35},
    "OTT": {"standings_rank": 17, "points": 74,  "wins": 34},
    "SEA": {"standings_rank": 18, "points": 72,  "wins": 33},
    "NYI": {"standings_rank": 19, "points": 70,  "wins": 32},
    "STL": {"standings_rank": 20, "points": 68,  "wins": 31},
    "SJS": {"standings_rank": 21, "points": 66,  "wins": 30},
    "CGY": {"standings_rank": 22, "points": 65,  "wins": 30},
    "DET": {"standings_rank": 23, "points": 64,  "wins": 29},
    "UTA": {"standings_rank": 24, "points": 63,  "wins": 29},
    "BUF": {"standings_rank": 25, "points": 61,  "wins": 28},
    "MTL": {"standings_rank": 26, "points": 59,  "wins": 27},
    "NSH": {"standings_rank": 27, "points": 57,  "wins": 26},
    "PIT": {"standings_rank": 28, "points": 55,  "wins": 25},
    "PHI": {"standings_rank": 29, "points": 53,  "wins": 24},
    "CBJ": {"standings_rank": 30, "points": 50,  "wins": 23},
    "ANA": {"standings_rank": 31, "points": 47,  "wins": 21},
    "CHI": {"standings_rank": 32, "points": 44,  "wins": 20},
}

output = {
    "meta": {
        "generated": datetime.utcnow().isoformat() + "Z",
        "season": "2025-26",
        "situation": "All situations",
        "dimensions": DIMS,
        "note": "Scores normalized 0–1 relative to league min/max. Seed data — run fetch_data.py for live stats.",
    },
    "teams": {}
}

for abbr in ARCHETYPES:
    meta = TEAMS[abbr]
    output["teams"][abbr] = {
        "name":      meta["name"],
        "abbr":      abbr,
        "primary":   meta["primary"],
        "secondary": meta["secondary"],
        "scores":    {d: norm[d][abbr] for d in DIMS},
        "raw":       raw_stats(abbr),
        "ranks":     {d: ranks[d][abbr] for d in DIMS},
        "gp":        random.randint(58, 65),
        "standings_rank": STANDINGS_RANKS.get(abbr, {}).get("standings_rank", None),
        "points":         STANDINGS_RANKS.get(abbr, {}).get("points", None),
        "wins":           STANDINGS_RANKS.get(abbr, {}).get("wins", None),
    }

with open("data/team_identity.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"✓ Seed data written for {len(output['teams'])} teams")
