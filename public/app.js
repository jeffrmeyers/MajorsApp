// ─── Global state ─────────────────────────────────────────────────────────────
let autoRefreshTimer = null;
let rawData = null;
let donkeyPlayers = [null, null]; // [donkey1, donkey2]

const DONKEY_KEYS = ['donkeyPlayer1Name', 'donkeyPlayer2Name'];

// ─── Score formatting ─────────────────────────────────────────────────────────
function formatScore(score) {
  if (score === null || score === undefined) return { display: '-', cls: 'score-dash' };
  if (score === 0) return { display: 'E', cls: 'score-even' };
  if (score < 0) return { display: String(score), cls: 'score-under' };
  return { display: `+${score}`, cls: 'score-over' };
}

function roundPillHTML(score, isActive, donkeyIdx) {
  if (score === null || score === undefined) return `<span class="round-pill">-</span>`;
  const label = score === 0 ? 'E' : score > 0 ? `+${score}` : score;
  if (donkeyIdx !== null && donkeyIdx !== undefined) {
    const num = donkeyIdx + 1;
    return `<span class="round-pill donkey donkey-${num}" title="Donkey ${num} substitution">🫏${num} ${label}</span>`;
  }
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
 * For each team, cut players are assigned donkeys in roster order:
 *   1st cut player → donkeys[0], 2nd cut player → donkeys[1]
 * Each assigned player's R3/R4 are replaced with their donkey's scores.
 */
function applyDonkeySubstitution(teams, donkeys) {
  const anyDonkey = donkeys.some(Boolean);
  if (!anyDonkey) return teams;

  const result = teams.map((team) => {
    // Collect cut players in roster order and pair with a donkey
    const cutQueue = team.players
      .map((p, i) => (p.cut ? i : null))
      .filter((i) => i !== null);

    // Build a map: player index → donkey
    const assignments = new Map();
    cutQueue.forEach((playerIdx, queuePos) => {
      const donkey = donkeys[queuePos] ?? null;
      if (donkey) assignments.set(playerIdx, { donkey, donkeyIdx: queuePos });
    });

    const players = team.players.map((p, i) => {
      const assignment = assignments.get(i);
      if (!assignment) return p;

      const { donkey, donkeyIdx } = assignment;
      const sub = {
        ...p,
        rounds: [...p.rounds],
        // track which round indices were donkey-substituted and which donkey
        donkeyRoundIdx: [null, null, null, null],
        donkeySubstituted: true,
        donkeyNum: donkeyIdx + 1,
      };

      let added = 0;
      if (donkey.rounds[2] !== null && donkey.rounds[2] !== undefined) {
        sub.rounds[2] = donkey.rounds[2];
        sub.donkeyRoundIdx[2] = donkeyIdx;
        added += donkey.rounds[2];
      }
      if (donkey.rounds[3] !== null && donkey.rounds[3] !== undefined) {
        sub.rounds[3] = donkey.rounds[3];
        sub.donkeyRoundIdx[3] = donkeyIdx;
        added += donkey.rounds[3];
      }

      sub.topar = (p.topar || 0) + added;
      sub.toparDisplay =
        sub.topar === 0 ? 'E' : sub.topar > 0 ? `+${sub.topar}` : `${sub.topar}`;
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
          const donkeyIcon = (ri === 2 || ri === 3) &&
            players.some((p) => p.donkeyRoundIdx && p.donkeyRoundIdx[ri] !== null)
            ? ' 🫏' : '';
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
            ? `<span class="status-badge status-donkey donkey-${p.donkeyNum}">🫏${p.donkeyNum}</span>`
            : '';

          const rounds = p.rounds
            .map((r, ri) =>
              roundPillHTML(
                r,
                ri === activeRound,
                p.donkeyRoundIdx ? p.donkeyRoundIdx[ri] : null
              )
            )
            .join('');

          const thruDisplay = p.thru === 'F' ? 'F' : p.thru === '-' ? '-' : `${p.thru}`;
          const todayFmt = p.notFound
            ? { display: '-', cls: 'score-dash' }
            : formatScore(p.today === 'E' ? 0 : parseInt(p.today) || 0);

          const rowClass = p.donkeySubstituted ? `donkey-row donkey-row-${p.donkeyNum}` : '';

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

function renderDonkeyInfo() {
  const infoEl = document.getElementById('donkey-info');
  const activeDonkeys = donkeyPlayers.filter(Boolean);

  if (activeDonkeys.length === 0) {
    infoEl.classList.add('hidden');
    infoEl.innerHTML = '';
    return;
  }

  const cards = donkeyPlayers
    .map((donkey, idx) => {
      if (!donkey) return '';

      // Count how many fantasy players are assigned this donkey
      const appliedCount = rawData
        ? rawData.teams.reduce((total, team) => {
            const cutPlayers = team.players.filter((p) => p.cut);
            return total + (cutPlayers[idx] ? 1 : 0);
          }, 0)
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
        donkey.status === 'CUT' ? 'Missed cut' : donkey.status === 'WD' ? 'Withdrawn' : donkey.pos || '';

      const warning = donkey.status === 'CUT'
        ? `<p class="donkey-warning">⚠️ This player also missed the cut — scores apply once available.</p>`
        : '';

      return `
        <div class="donkey-info-card donkey-info-card-${idx + 1}">
          <div class="donkey-info-card-header">
            <span class="donkey-info-num">🫏${idx + 1}</span>
            <span class="donkey-info-card-name">${donkey.name}</span>
            <span class="donkey-player-pos ${statusCls}">${statusLabel}</span>
          </div>
          <div class="donkey-scores">
            <div class="donkey-score-item">
              <span class="donkey-score-label">R3</span>${r3Display}
            </div>
            <div class="donkey-score-item">
              <span class="donkey-score-label">R4</span>${r4Display}
            </div>
            <div class="donkey-score-item">
              <span class="donkey-score-label">Applied to</span>
              <span class="donkey-round-val">${appliedCount} player${appliedCount !== 1 ? 's' : ''}</span>
            </div>
          </div>
          ${warning}
        </div>`;
    })
    .join('');

  infoEl.innerHTML = `<div class="donkey-info-cards">${cards}</div>`;
  infoEl.classList.remove('hidden');
}

// ─── Donkey autocomplete ──────────────────────────────────────────────────────
function initDonkeyInput() {
  [0, 1].forEach((idx) => {
    const input = document.getElementById(`donkey-input-${idx}`);
    const clearBtn = document.getElementById(`donkey-clear-${idx}`);
    const suggestions = document.getElementById(`donkey-suggestions-${idx}`);

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
          selectDonkeyPlayer(el.dataset.name, idx);
        });
      });
    });

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
          selectDonkeyPlayer(first.dataset.name, idx);
        }
      }
    });

    clearBtn.addEventListener('click', () => clearDonkeyPlayer(idx));
  });
}

function selectDonkeyPlayer(name, idx) {
  if (!rawData?.allPlayers) return;
  const player = rawData.allPlayers.find((p) => p.name === name);
  if (!player) return;

  donkeyPlayers[idx] = player;
  localStorage.setItem(DONKEY_KEYS[idx], name);

  document.getElementById(`donkey-input-${idx}`).value = name;
  document.getElementById(`donkey-input-${idx}`).blur();
  document.getElementById(`donkey-clear-${idx}`).classList.remove('hidden');
  document.getElementById(`donkey-suggestions-${idx}`).classList.add('hidden');

  rerenderWithDonkey();
}

function clearDonkeyPlayer(idx) {
  donkeyPlayers[idx] = null;
  localStorage.removeItem(DONKEY_KEYS[idx]);

  document.getElementById(`donkey-input-${idx}`).value = '';
  document.getElementById(`donkey-clear-${idx}`).classList.add('hidden');

  rerenderWithDonkey();
}

function restoreDonkeyFromStorage() {
  DONKEY_KEYS.forEach((key, idx) => {
    const saved = localStorage.getItem(key);
    if (saved && rawData?.allPlayers) {
      const player = rawData.allPlayers.find((p) => p.name === saved);
      if (player) {
        donkeyPlayers[idx] = player;
        document.getElementById(`donkey-input-${idx}`).value = saved;
        document.getElementById(`donkey-clear-${idx}`).classList.remove('hidden');
      }
    }
  });
}

// ─── Render cycle ─────────────────────────────────────────────────────────────
function rerenderWithDonkey() {
  if (!rawData) return;
  const effectiveTeams = applyDonkeySubstitution(rawData.teams, donkeyPlayers);
  renderLeaderboard(effectiveTeams, rawData.roundStatuses);
  renderTeamCards(effectiveTeams, rawData.roundStatuses);
  renderDonkeyInfo();
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
