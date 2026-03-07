#!/usr/bin/env node
/**
 * NHL Team Identity — Instagram Card Generator
 * Renders a 1080x1080 PNG card using Puppeteer.
 *
 * Usage:
 *   node src/card_generator.js --team FLA
 *   node src/card_generator.js --team FLA --compare EDM
 *   node src/card_generator.js --all          (generates all 32 teams)
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const getArg = (flag) => { const i = args.indexOf(flag); return i !== -1 ? args[i+1] : null; };
const hasFlag = (flag) => args.includes(flag);

const DATA_PATH = path.join(__dirname, '../data/team_identity.json');
const OUT_DIR   = path.join(__dirname, '../cards');

if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

const { teams, meta } = JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));

const DIMS = [
  { key: 'possession',  label: 'POSSESSION' },
  { key: 'transition',  label: 'TRANSITION' },
  { key: 'finishing',   label: 'FINISHING'  },
  { key: 'physical',    label: 'PHYSICAL'   },
  { key: 'discipline',  label: 'DISCIPLINE' },
  { key: 'goaltending', label: 'GOALTENDING'},
  { key: 'defensive',   label: 'DEFENSIVE'  },
];

function generateCardHTML(teamA, teamB = null) {
  const isCompare = !!teamB;
  const COLOR_A = '#4a9eff';
  const COLOR_B = '#ff6b6b';

  function polarPts(scores, R, cx, cy) {
    const n = scores.length;
    return scores.map((s, i) => {
      const a = (2 * Math.PI / n) * i;
      const x = cx + R * s * Math.sin(a);
      const y = cy - R * s * Math.cos(a);
      return `${x},${y}`;
    }).join(' ');
  }

  function gridPts(t, R, cx, cy, n) {
    return Array.from({length: n}, (_, i) => {
      const a = (2 * Math.PI / n) * i;
      return `${cx + R * t * Math.sin(a)},${cy - R * t * Math.cos(a)}`;
    }).join(' ');
  }

  const W = 480, H = 480, cx = W/2, cy = H/2, R = 160, n = 7;
  const scoresA = DIMS.map(d => teamA.scores[d.key]);
  const scoresB = isCompare ? DIMS.map(d => teamB.scores[d.key]) : [];

  const axisLines = DIMS.map((d, i) => {
    const a = (2 * Math.PI / n) * i;
    const x2 = cx + R * Math.sin(a), y2 = cy - R * Math.cos(a);
    const lx = cx + (R+32) * Math.sin(a), ly = cy - (R+32) * Math.cos(a);
    const anchor = lx < cx - 5 ? 'end' : lx > cx + 5 ? 'start' : 'middle';
    return `<line x1="${cx}" y1="${cy}" x2="${x2}" y2="${y2}" stroke="#1e2d42" stroke-width="1"/>
      <text x="${lx}" y="${ly+4}" text-anchor="${anchor}" fill="#6a8aaa" font-family="Barlow Condensed" font-weight="700" font-size="12" letter-spacing="0.5">${d.label}</text>`;
  }).join('');

  const rings = [0.25, 0.5, 0.75, 1.0].map(t =>
    `<polygon points="${gridPts(t, R, cx, cy, n)}" fill="none" stroke="#1e2d42" stroke-width="1"/>`
  ).join('');
  const avgRing = `<polygon points="${gridPts(0.5, R, cx, cy, n)}" fill="none" stroke="#2a3d58" stroke-width="1" stroke-dasharray="4,3"/>`;

  const polyA = `<polygon points="${polarPts(scoresA, R, cx, cy)}" fill="url(#gradA)" stroke="none"/>
    <polygon points="${polarPts(scoresA, R, cx, cy)}" fill="none" stroke="${COLOR_A}" stroke-width="2.5" stroke-linejoin="round"/>`;
  const dotsA = scoresA.map((s, i) => {
    const a = (2 * Math.PI / n) * i;
    const x = cx + R * s * Math.sin(a), y = cy - R * s * Math.cos(a);
    return `<circle cx="${x}" cy="${y}" r="4" fill="${COLOR_A}" stroke="#0e1520" stroke-width="2"/>`;
  }).join('');

  const polyB = isCompare ? `<polygon points="${polarPts(scoresB, R, cx, cy)}" fill="url(#gradB)" stroke="none"/>
    <polygon points="${polarPts(scoresB, R, cx, cy)}" fill="none" stroke="${COLOR_B}" stroke-width="2.5" stroke-linejoin="round"/>` : '';
  const dotsB = isCompare ? scoresB.map((s, i) => {
    const a = (2 * Math.PI / n) * i;
    const x = cx + R * s * Math.sin(a), y = cy - R * s * Math.cos(a);
    return `<circle cx="${x}" cy="${y}" r="4" fill="${COLOR_B}" stroke="#0e1520" stroke-width="2"/>`;
  }).join('') : '';

  // Stat bars for side panel
  const statBars = DIMS.map(d => {
    const sA = teamA.scores[d.key];
    const rA = teamA.ranks[d.key];
    if (isCompare) {
      const sB = teamB.scores[d.key];
      const rB = teamB.ranks[d.key];
      return `<div style="margin-bottom:10px">
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;letter-spacing:.1em;color:#5a6e87;margin-bottom:4px">${d.label}</div>
        <div style="height:5px;background:#141d2b;margin-bottom:2px;position:relative">
          <div style="height:100%;width:${sA*100}%;background:${COLOR_A}"></div>
        </div>
        <div style="height:5px;background:#141d2b;margin-bottom:3px;position:relative">
          <div style="height:100%;width:${sB*100}%;background:${COLOR_B}"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-family:'Barlow Condensed',sans-serif;font-size:10px;color:#5a6e87">
          <span style="color:${COLOR_A}">#${rA}</span><span style="color:${COLOR_B}">#${rB}</span>
        </div>
      </div>`;
    }
    return `<div style="margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;letter-spacing:.1em;color:#5a6e87">${d.label}</span>
        <span style="font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:600;color:#8aa4c0">#${rA}</span>
      </div>
      <div style="height:5px;background:#141d2b;position:relative">
        <div style="height:100%;width:${sA*100}%;background:linear-gradient(90deg,${teamA.primary},${teamA.secondary || COLOR_A})"></div>
      </div>
    </div>`;
  }).join('');

  const title = isCompare
    ? `<span style="color:${COLOR_A}">${teamA.abbr}</span> <span style="color:#2e4060">vs</span> <span style="color:${COLOR_B}">${teamB.abbr}</span>`
    : `<span style="color:${COLOR_A}">${teamA.abbr}</span>`;

  const subtitle = isCompare
    ? `${teamA.name} · ${teamB.name}`
    : teamA.name;

  return `<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;400;600;700;800&family=Barlow:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  body { width:1080px; height:1080px; background:#080c12; overflow:hidden; position:relative; }
  body::before {
    content:''; position:absolute; inset:0;
    background: radial-gradient(ellipse 100% 60% at 50% 0%, rgba(74,158,255,0.06) 0%, transparent 70%);
    pointer-events:none;
  }
</style></head><body>
<div style="width:1080px;height:1080px;display:flex;flex-direction:column;padding:56px;position:relative;z-index:1">

  <!-- Header -->
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:48px;border-bottom:1px solid #1e2d42;padding-bottom:32px">
    <div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:600;letter-spacing:.2em;color:#3a5570;text-transform:uppercase;margin-bottom:6px">stat-trick-hockey</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:56px;font-weight:800;line-height:1;color:#e8edf5;letter-spacing:-.01em">${title}</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:400;color:#5a6e87;margin-top:6px;letter-spacing:.02em">${subtitle}</div>
    </div>
    <div style="text-align:right">
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:600;letter-spacing:.15em;color:#4a9eff;background:rgba(74,158,255,.1);border:1px solid rgba(74,158,255,.2);padding:5px 12px;margin-bottom:8px">2025–26 SEASON</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:11px;color:#3a5570;letter-spacing:.06em">TEAM IDENTITY RADAR</div>
    </div>
  </div>

  <!-- Body -->
  <div style="flex:1;display:flex;gap:48px;align-items:center">

    <!-- Radar -->
    <div style="flex:1">
      <svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" style="display:block;margin:0 auto">
        <defs>
          <radialGradient id="gradA" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="${COLOR_A}" stop-opacity=".3"/>
            <stop offset="100%" stop-color="${COLOR_A}" stop-opacity=".05"/>
          </radialGradient>
          ${isCompare ? `<radialGradient id="gradB" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="${COLOR_B}" stop-opacity=".25"/>
            <stop offset="100%" stop-color="${COLOR_B}" stop-opacity=".05"/>
          </radialGradient>` : ''}
        </defs>
        ${rings}${avgRing}${axisLines}
        ${isCompare ? polyB + dotsB : ''}
        ${polyA}${dotsA}
        <circle cx="${cx}" cy="${cy}" r="3" fill="#2e4060"/>
      </svg>
    </div>

    <!-- Stats -->
    <div style="width:280px">
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;letter-spacing:.15em;color:#3a5570;text-transform:uppercase;margin-bottom:20px;border-bottom:1px solid #1e2d42;padding-bottom:10px">
        DIMENSION SCORES
        ${isCompare ? `<span style="float:right"><span style="color:${COLOR_A}">■ ${teamA.abbr}</span> <span style="color:${COLOR_B}">■ ${teamB.abbr}</span></span>` : ''}
      </div>
      ${statBars}
    </div>

  </div>

  <!-- Footer -->
  <div style="border-top:1px solid #1e2d42;padding-top:20px;margin-top:32px;display:flex;justify-content:space-between;align-items:center">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:11px;color:#2e4060;letter-spacing:.06em">
      Scores normalized 0–100 relative to league range · All situations
    </div>
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:11px;color:#2e4060;letter-spacing:.06em">
      @stat_trick_hockey
    </div>
  </div>

</div>
</body></html>`;
}

async function renderCard(teamAbbr, teamBAbbr = null) {
  const teamA = teams[teamAbbr];
  if (!teamA) { console.error(`Team not found: ${teamAbbr}`); return; }
  const teamB = teamBAbbr ? teams[teamBAbbr] : null;

  const html = generateCardHTML(teamA, teamB);
  const slug = teamBAbbr ? `${teamAbbr}-vs-${teamBAbbr}` : teamAbbr;
  const outPath = path.join(OUT_DIR, `${slug}.png`);

  const browser = await puppeteer.launch({ args: ['--no-sandbox','--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1080 });
  await page.setContent(html, { waitUntil: 'networkidle0' });
  await page.screenshot({ path: outPath, type: 'png' });
  await browser.close();

  console.log(`✓ ${outPath}`);
  return outPath;
}

async function main() {
  if (hasFlag('--all')) {
    console.log(`Generating cards for all ${Object.keys(teams).length} teams...`);
    for (const abbr of Object.keys(teams)) {
      await renderCard(abbr);
    }
  } else {
    const teamArg = getArg('--team');
    const compareArg = getArg('--compare');
    if (!teamArg) {
      console.log('Usage: node src/card_generator.js --team <ABBR> [--compare <ABBR>] [--all]');
      console.log('Teams:', Object.keys(teams).join(', '));
      process.exit(1);
    }
    await renderCard(teamArg.toUpperCase(), compareArg ? compareArg.toUpperCase() : null);
  }
}

main().catch(console.error);
