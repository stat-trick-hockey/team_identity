# NHL Team Identity Radar

Broadcast-style radar visualization showing every NHL team's identity across 7 dimensions for the 2024–25 season. Built for [stat-trick-hockey](https://github.com/stat-trick-hockey).

## Dimensions

| Dimension | Metric | Source |
|---|---|---|
| **Possession** | Shot share (CF%) proxy | NHL API |
| **Transition** | GF rate / SA rate | NHL API |
| **Finishing** | Shooting % | NHL API |
| **Physical** | Hits + blocks per GP | NHL API |
| **Discipline** | Inverse of PIM/GP | NHL API |
| **Goaltending** | Save % | NHL API |
| **Defensive** | Inverse of shots against/GP | NHL API |

All scores normalized 0–1 relative to league min/max for the current season.

## Usage

### Interactive HTML
Open `radar.html` directly in a browser. No build step needed.
- Toggle between **Single Team** and **Compare** mode
- Hover dots on the radar for tooltips with raw stats and league rank
- Team selector includes all 32 teams

### Data Fetch
```bash
# Live data (requires NHL API access)
python3 src/fetch_data.py

# Seed data (realistic 2024-25 estimates, no network needed)
python3 src/generate_seed.py
```

### Card Generator
```bash
npm install

# Single team card
node src/card_generator.js --team FLA

# Comparison card
node src/card_generator.js --team FLA --compare EDM

# All 32 teams
node src/card_generator.js --all
```

Cards are saved to `cards/` as 1080×1080 PNG files.

### GitHub Actions
The weekly workflow runs every Monday, refreshing `data/team_identity.json` from the NHL API and regenerating all cards. Trigger manually via Actions tab with optional `team` and `compare` inputs.

## Project Structure

```
nhl-team-identity/
├── data/
│   └── team_identity.json      # Normalized team scores (auto-updated)
├── src/
│   ├── fetch_data.py           # NHL API data pull + normalization
│   ├── generate_seed.py        # Realistic seed data (offline)
│   └── card_generator.js       # Puppeteer PNG renderer
├── cards/                      # Generated Instagram cards
├── radar.html                  # Interactive D3 visualization
├── .github/workflows/
│   └── weekly-refresh.yml      # Automated refresh pipeline
└── package.json
```
