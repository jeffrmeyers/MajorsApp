// ─── Global state ────────────────────────────────────────────────────────────
let autoRefreshTimer = null;
let rawData = null;       // last API response
let donkeyPlayer = null;  // currently selected donkey player object from allPlayers

// Restore saved donkey name across page loads
const DONKEY_KEY = 'donkeyPlayerName';

// ─── Score formatting ─────────────────────────────────────────────────────────
function formatScore(score) {
  if (score === null || score === undefined) return { display: '-', cls: 'score-dash' };
  if (score === 0) return { display: 'E', cls: 'score-even' };
  if (score < 0) return { display: String(score), cls: 'score-under' };
  return { display: `+${score}`, cls: 'score-over' };
}

function roundPillHTML(score, isActive, isDonkey) {
  if (score === null || score === undefined) return `<span class="round-pill">-</span>`;
  const label = score === 0 ? 'E' : score > 0 ? `+${score}` : score;
  if (isDonkey) return `<span class="round-pill donkey" title="Donkey substitution">🫏 ${label}</span>`;
  if (isActive) return `<span class="round-pill active">${label}</span>`;
  const cls = score < 0 ? 'under' : score > 0 ? 'over' : '';
  return `<span class="round-pill ${cls}">${label}</span>`;
}

function buildRoundLabel(currentRound, roundStatuses) {
  if (!roundStatuses || roundStatuses.length === 0) return 'Round 1';
  const activeIdx = roundStatuses.findIndex((s) => s === 'A');
  if (activeIdx !== -1) return `Round ${activeIdx + 1} · In Progress`;
  const lastFinished = roundStatuses.lastIndexOf('F');
  if (lastFinished === 3) return 'Tournament Complete';
  if (lastFinished >= 0) return `Round ${lastFinished + 1} Complete`;
  return 'Round 1';
}

// ─── Donkey substitution ──────────────────────────────────────────────────────
/**
 * Deep-clones teams and, for every CUT player, replaces their
 * R3 and R4 with the donkey player's R3/R4. Re-sorts by new totals.
 */
function applyDonkeySubstitution(teams, donkey) {
  if (!donkey) return teams;

  const result = teams.map((team) => {
    const players = team.players.map((p) => {
      if (!p.cut) return p;

      const sub = { ...p, rounds: [...p.rounds], donkeyRounds: [false, false, false, false] };
      let added = 0;

      if (donkey.rounds[2] !== null && donkey.rounds[2] !== undefined) {
        sub.rounds[2] = donkey.rounds[2];
        sub.donkeyRounds[2] = true;
        added += donkey.rounds[2];
      }
      if (donkey.rounds[3] !== null && donkey.rounds[3] !== undefined) {
        sub.rounds[3] = donkey.rounds[3];
        sub.donkeyRounds[3] = true;
        added += donkey.rounds[3];
      }

      sub.topar = (p.topar || 0) + added;
      sub.toparDisplay =
        sub.topar === 0 ? 'E' : sub.topar > 0 ? `+${sub.topar}` : `${sub.topar}`;
      sub.donkeySubstituted = true;
      return sub;
    });

    const teamTopar = players.reduce(
      (sum, p) => sum + (p.notFound || p.wd ? 0 : p.topar || 0),
      0
    );
    return {
      ...team,
      players,
      teamTopar,
      teamToparDisplay:
        teamTopar === 0 ? 'E' : teamTopar > 0 ? `+${teamTopar}` : `${teamTopar}`,
    };
  });

  // Re-sort and re-rank
  result.sort((a, b) => a.teamTopar - b.teamTopar);
  result.forEach((t, i) => (t.rank = i + 1));
  return result;
}

// ─── Rendering ────────────────────────────────────────────────────────────────
function renderLeaderboard(teams, roundStatuses) {
  const tbody = document.getElementById('leaderboard-body');
  const activeRound = roundStatuses ? roundStatuses.findIndex((s) => s === 'A') : -1;

  tbody.innerHTML = teams
    .map((team) => {
      const { rank, name, players, teamTopar, teamToparDisplay } = team;
      const totalFmt = formatScore(teamTopar);

      const roundTotals = [0, 1, 2, 3].map((ri) => {
        let sum = null;
        for (const p of players) {
          const r = p.rounds[ri];
          if (r !== null && r !== undefined) sum = (sum || 0) + r;
        }
        return sum;
      });

      const roundCells = roundTotals
        .map((rt, ri) => {
          if (rt === null) return `<td class="round-cell score-dash">-</td>`;
          const fmt = formatScore(rt);
          const isActive = ri === activeRound;
          // Show donkey icon on R3/R4 team totals if substitution is active and relevant
          const hasDonkeyInRound = donkeyPlayer && (ri === 2 || ri === 3) &&
            players.some((p) => p.donkeyRounds && p.donkeyRounds[ri]);
          const donkeyIcon = hasDonkeyInRound ? ' 🫏' : '';
          return `<td class="round-cell ${isActive ? 'score-even' : fmt.cls}">${fmt.display}${donkeyIcon}</td>`;
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
          const donkeyBadge = p.donkeySubstituted
            ? `<span class="status-badge status-donkey">🫏 SUB</span>`
            : '';

          const rounds = p.rounds
            .map((r, ri) =>
              roundPillHTML(r, ri === activeRound, p.donkeyRounds && p.donkeyRounds[ri])
            )
            .join('');

          const thruDisplay = p.thru === 'F' ? 'F' : p.thru === '-' ? '-' : `${p.thru}`;
          const todayFmt = p.notFound
            ? { display: '-', cls: 'score-dash' }
            : formatScore(p.today === 'E' ? 0 : parseInt(p.today) || 0);

          const rowClass = p.donkeySubstituted ? 'donkey-row' : '';

          return `
            <tr class="${rowClass}">
              <td>
                <div class="player-name">${p.name}${statusBadge}${donkeyBadge}</div>
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
          <div class="table-scroll">
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
          </div>
        </div>`;
    })
    .join('');
}

function renderDonkeyInfo(donkey) {
  const infoEl = document.getElementById('donkey-info');
  if (!donkey) {
    infoEl.classList.add('hidden');
    infoEl.innerHTML = '';
    return;
  }

  // Count how many fantasy players are CUT
  const cutCount = rawData
    ? rawData.teams.flatMap((t) => t.players).filter((p) => p.cut).length
    : 0;

  const r3Fmt = formatScore(donkey.rounds[2]);
  const r4Fmt = formatScore(donkey.rounds[3]);

  const r3Display =
    donkey.rounds[2] !== null && donkey.rounds[2] !== undefined
      ? `<span class="donkey-round-val ${r3Fmt.cls}">${r3Fmt.display}</span>`
      : `<span class="donkey-round-val score-dash">—</span>`;
  const r4Display =
    donkey.rounds[3] !== null && donkey.rounds[3] !== undefined
      ? `<span class="donkey-round-val ${r4Fmt.cls}">${r4Fmt.display}</span>`
      : `<span class="donkey-round-val score-dash">—</span>`;

  const statusCls = donkey.status === 'CUT' ? 'score-over' : 'score-even';
  const statusLabel =
    donkey.status === 'CUT' ? 'Missed cut' : donkey.status === 'WD' ? 'Withdrawn' : `${donkey.pos}`;

  infoEl.innerHTML = `
    <div class="donkey-info-inner">
      <div class="donkey-player-name">${donkey.name}
        <span class="donkey-player-pos ${statusCls}">${statusLabel}</span>
      </div>
      <div class="donkey-scores">
        <div class="donkey-score-item">
          <span class="donkey-score-label">R3</span>
          ${r3Display}
        </div>
        <div class="donkey-score-item">
          <span class="donkey-score-label">R4</span>
          ${r4Display}
        </div>
        <div class="donkey-score-item">
          <span class="donkey-score-label">Applied to</span>
          <span class="donkey-round-val">${cutCount} player${cutCount !== 1 ? 's' : ''}</span>
        </div>
      </div>
      ${donkey.status === 'CUT' ? `<p class="donkey-warning">⚠️ This player also missed the cut — R3 &amp; R4 scores will be applied once available.</p>` : ''}
    </div>`;
  infoEl.classList.remove('hidden');
}

// ─── Donkey autocomplete ──────────────────────────────────────────────────────
function initDonkeyInput() {
  const input = document.getElementById('donkey-input');
  const clearBtn = document.getElementById('donkey-clear');
  const suggestions = document.getElementById('donkey-suggestions');

  input.addEventListener('input', () => {
    const query = input.value.trim().toLowerCase();
    if (query.length < 2 || !rawData?.allPlayers) {
      suggestions.classList.add('hidden');
      suggestions.innerHTML = '';
      return;
    }

    const matches = rawData.allPlayers.filter((p) =>
      p.name.toLowerCase().includes(query)
    );

    if (matches.length === 0) {
      suggestions.innerHTML = `<div class="donkey-suggestion-item no-match">No players found</div>`;
      suggestions.classList.remove('hidden');
      return;
    }

    suggestions.innerHTML = matches
      .slice(0, 8)
      .map(
        (p) => `
        <div class="donkey-suggestion-item" data-name="${p.name}">
          <span class="suggestion-name">${p.name}</span>
          <span class="suggestion-meta ${p.status === 'CUT' ? 'score-over' : 'score-even'}">
            ${p.status === 'CUT' ? 'CUT' : p.pos || ''}
          </span>
        </div>`
      )
      .join('');
    suggestions.classList.remove('hidden');

    suggestions.querySelectorAll('.donkey-suggestion-item[data-name]').forEach((el) => {
      el.addEventListener('mousedown', (e) => {
        e.preventDefault();
        selectDonkeyPlayer(el.dataset.name);
      });
    });
  });

  // Hide suggestions on blur
  input.addEventListener('blur', () => {
    setTimeout(() => suggestions.classList.add('hidden'), 150);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      suggestions.classList.add('hidden');
      input.blur();
    }
    if (e.key === 'Enter') {
      const first = suggestions.querySelector('.donkey-suggestion-item[data-name]');
      if (first) {
        e.preventDefault();
        selectDonkeyPlayer(first.dataset.name);
      }
    }
  });

  clearBtn.addEventListener('click', () => {
    clearDonkeyPlayer();
  });
}

function selectDonkeyPlayer(name) {
  if (!rawData?.allPlayers) return;
  const player = rawData.allPlayers.find((p) => p.name === name);
  if (!player) return;

  donkeyPlayer = player;
  localStorage.setItem(DONKEY_KEY, name);

  const input = document.getElementById('donkey-input');
  const clearBtn = document.getElementById('donkey-clear');
  const suggestions = document.getElementById('donkey-suggestions');

  input.value = name;
  input.blur();
  clearBtn.classList.remove('hidden');
  suggestions.classList.add('hidden');

  rerenderWithDonkey();
}

function clearDonkeyPlayer() {
  donkeyPlayer = null;
  localStorage.removeItem(DONKEY_KEY);

  const input = document.getElementById('donkey-input');
  const clearBtn = document.getElementById('donkey-clear');

  input.value = '';
  clearBtn.classList.add('hidden');
  document.getElementById('donkey-info').classList.add('hidden');

  rerenderWithDonkey();
}

function restoreDonkeyFromStorage() {
  const saved = localStorage.getItem(DONKEY_KEY);
  if (saved && rawData?.allPlayers) {
    const player = rawData.allPlayers.find((p) => p.name === saved);
    if (player) {
      donkeyPlayer = player;
      const input = document.getElementById('donkey-input');
      const clearBtn = document.getElementById('donkey-clear');
      input.value = saved;
      clearBtn.classList.remove('hidden');
    }
  }
}

// ─── Render cycle ─────────────────────────────────────────────────────────────
function rerenderWithDonkey() {
  if (!rawData) return;
  const { roundStatuses } = rawData;
  const effectiveTeams = applyDonkeySubstitution(rawData.teams, donkeyPlayer);
  renderLeaderboard(effectiveTeams, roundStatuses);
  renderTeamCards(effectiveTeams, roundStatuses);
  renderDonkeyInfo(donkeyPlayer);
}

// ─── Data loading ─────────────────────────────────────────────────────────────
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

    rawData = data;

    roundBadge.textContent = buildRoundLabel(data.currentRound, data.roundStatuses);
    const now = new Date();
    lastUpdatedEl.textContent = `Updated ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

    // Restore donkey player from storage now that allPlayers is available
    restoreDonkeyFromStorage();

    rerenderWithDonkey();

    loading.classList.add('hidden');
    table.classList.remove('hidden');

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
      errBox.textContent = `Could not load scores: ${err.message}. Retrying in 60 seconds...`;
      wrap.prepend(errBox);
    }
  }

  if (autoRefreshTimer) clearTimeout(autoRefreshTimer);
  autoRefreshTimer = setTimeout(loadScores, 60_000);
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

document.addEventListener('DOMContentLoaded', () => {
  initDonkeyInput();
  loadScores();
});
