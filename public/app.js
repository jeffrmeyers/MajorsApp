let autoRefreshTimer = null;

function formatScore(score) {
  if (score === null || score === undefined) return { display: '-', cls: 'score-dash' };
  if (score === 0) return { display: 'E', cls: 'score-even' };
  if (score < 0) return { display: String(score), cls: 'score-under' };
  return { display: `+${score}`, cls: 'score-over' };
}

function roundPillHTML(score, isActive) {
  if (score === null || score === undefined) return `<span class="round-pill">-</span>`;
  if (isActive) return `<span class="round-pill active">${score === 0 ? 'E' : score > 0 ? '+' + score : score}</span>`;
  const cls = score < 0 ? 'under' : score > 0 ? 'over' : '';
  const label = score === 0 ? 'E' : score > 0 ? `+${score}` : score;
  return `<span class="round-pill ${cls}">${label}</span>`;
}

function buildRoundLabel(currentRound, roundStatuses) {
  const statusMap = { F: 'Final', A: 'In Progress', N: 'Not Started' };
  if (!roundStatuses || roundStatuses.length === 0) return 'Round 1';
  const activeIdx = roundStatuses.findIndex((s) => s === 'A');
  if (activeIdx !== -1) return `Round ${activeIdx + 1} · In Progress`;
  const lastFinished = roundStatuses.lastIndexOf('F');
  if (lastFinished === 3) return 'Tournament Complete';
  if (lastFinished >= 0) return `Round ${lastFinished + 1} Complete`;
  return 'Round 1';
}

function renderLeaderboard(teams, roundStatuses) {
  const tbody = document.getElementById('leaderboard-body');
  const activeRound = roundStatuses ? roundStatuses.findIndex((s) => s === 'A') : -1;

  tbody.innerHTML = teams
    .map((team) => {
      const { rank, name, players, teamTopar, teamToparDisplay } = team;
      const totalFmt = formatScore(teamTopar);

      // Calculate per-round team totals
      const roundTotals = [0, 1, 2, 3].map((ri) => {
        let sum = null;
        for (const p of players) {
          const r = p.rounds[ri];
          if (r !== null && r !== undefined) {
            sum = (sum || 0) + r;
          }
        }
        return sum;
      });

      const roundCells = roundTotals
        .map((rt, ri) => {
          if (rt === null) return `<td class="round-cell score-dash">-</td>`;
          const fmt = formatScore(rt);
          const isActive = ri === activeRound;
          return `<td class="round-cell ${isActive ? 'score-even' : fmt.cls}">${fmt.display}</td>`;
        })
        .join('');

      const rankIcon =
        rank === 1
          ? `<span class="rank-1-icon">🏆</span>`
          : `<span class="rank-num">${rank}</span>`;

      return `
        <tr class="${rank === 1 ? 'rank-1' : ''}" onclick="scrollToTeam('${name}')">
          <td class="rank-cell">${rankIcon}</td>
          <td class="team-name-cell">${name}</td>
          ${roundCells}
          <td class="total-cell ${totalFmt.cls}">${teamToparDisplay}</td>
        </tr>`;
    })
    .join('');
}

function renderTeamCards(teams, roundStatuses) {
  const grid = document.getElementById('cards-grid');
  const activeRound = roundStatuses ? roundStatuses.findIndex((s) => s === 'A') : -1;

  grid.innerHTML = teams
    .map((team) => {
      const { rank, name, players, teamTopar, teamToparDisplay } = team;
      const totalFmt = formatScore(teamTopar);
      const headerClass = rank === 1 ? 'rank-1' : '';

      const playerRows = players
        .map((p) => {
          const toparFmt = p.notFound ? { display: 'N/A', cls: 'score-dash' } : formatScore(p.topar);
          const statusBadge = p.cut
            ? `<span class="status-badge status-cut">CUT</span>`
            : p.wd
            ? `<span class="status-badge status-wd">WD</span>`
            : '';

          const rounds = p.rounds
            .map((r, ri) => roundPillHTML(r, ri === activeRound))
            .join('');

          const thruDisplay = p.thru === 'F' ? 'F' : p.thru === '-' ? '-' : `${p.thru}`;
          const todayFmt = p.notFound ? { display: '-', cls: 'score-dash' } : formatScore(
            p.today === 'E' ? 0 : parseInt(p.today) || 0
          );

          return `
            <tr>
              <td>
                <div class="player-name">${p.name}${statusBadge}</div>
                <div class="player-pos">${p.pos !== 'N/A' ? p.pos : ''}</div>
              </td>
              <td class="player-thru">${thruDisplay}</td>
              <td class="player-today ${todayFmt.cls}">${p.notFound ? '-' : p.today}</td>
              <td class="player-total ${toparFmt.cls}">${toparFmt.display}</td>
              <td style="text-align:right;padding-right:12px">
                <div class="player-rounds">${rounds}</div>
              </td>
            </tr>`;
        })
        .join('');

      return `
        <div class="team-card" id="card-${name.replace(/\s+/g, '-')}">
          <div class="team-card-header ${headerClass}">
            <div class="team-card-name">${name}</div>
            <div class="team-card-meta">
              <span class="team-card-rank">RANK ${rank}</span>
              <span class="team-card-total ${totalFmt.cls}">${teamToparDisplay}</span>
            </div>
          </div>
          <table class="player-table">
            <thead>
              <tr>
                <th>Player</th>
                <th class="right" style="text-align:center">Thru</th>
                <th class="right">Today</th>
                <th class="right">Total</th>
                <th class="right" style="padding-right:12px">Rounds</th>
              </tr>
            </thead>
            <tbody>${playerRows}</tbody>
          </table>
        </div>`;
    })
    .join('');
}

function scrollToTeam(name) {
  const id = `card-${name.replace(/\s+/g, '-')}`;
  const el = document.getElementById(id);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.style.boxShadow = '0 0 0 3px #c9a84c, 0 8px 32px rgba(0,0,0,0.15)';
    setTimeout(() => (el.style.boxShadow = ''), 1800);
  }
}

async function loadScores() {
  const loading = document.getElementById('loading');
  const table = document.getElementById('leaderboard-table');
  const lastUpdatedEl = document.getElementById('last-updated');
  const roundBadge = document.getElementById('round-badge');

  loading.classList.remove('hidden');
  table.classList.add('hidden');

  try {
    const res = await fetch('/api/scores');
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();

    if (data.error) throw new Error(data.error);

    const { teams, lastUpdated, roundStatuses } = data;

    roundBadge.textContent = buildRoundLabel(data.currentRound, roundStatuses);

    const now = new Date();
    lastUpdatedEl.textContent = `Updated ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

    renderLeaderboard(teams, roundStatuses);
    renderTeamCards(teams, roundStatuses);

    loading.classList.add('hidden');
    table.classList.remove('hidden');

    // Clear existing error if any
    const existing = document.querySelector('.error-box');
    if (existing) existing.remove();
  } catch (err) {
    console.error(err);
    loading.classList.add('hidden');
    table.classList.remove('hidden');
    lastUpdatedEl.textContent = 'Failed to load scores';

    const wrap = document.getElementById('leaderboard-table-wrap');
    const existing = wrap.querySelector('.error-box');
    if (!existing) {
      const errBox = document.createElement('div');
      errBox.className = 'error-box';
      errBox.textContent = `Could not load scores: ${err.message}. Retrying in 30 seconds...`;
      wrap.prepend(errBox);
    }
  }

  // Schedule next refresh
  if (autoRefreshTimer) clearTimeout(autoRefreshTimer);
  autoRefreshTimer = setTimeout(loadScores, 60_000);
}

document.addEventListener('DOMContentLoaded', loadScores);
