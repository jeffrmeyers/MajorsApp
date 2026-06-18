const express = require('express');
const fetch = require('node-fetch');
const path = require('path');

const app = express();
const PORT = 3000;

const MASTERS_API = 'https://www.masters.com/en_US/scores/feeds/2026/scores.json';
const ESPN_SCOREBOARD_API = 'https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard';
const PGA_EVENT_ID = '401811947';
const US_OPEN_EVENT_ID = '401811952';
const MASTERS_LOGO_URL = 'https://upload.wikimedia.org/wikipedia/commons/c/c5/Masters_Tournament.svg';
const PGA_LOGO_URL = 'https://wp.logos-download.com/wp-content/uploads/2023/02/USPGA_2022_PGA_Championship_Logo.svg';
const US_OPEN_LOGO_URL = 'https://filecache.mediaroom.com/mr5mr_usga2/191226/2026-USO_SHINNECOCK_FULL-COLOR%20%281%29.jpg';

const MASTERS_TEAMS = {
  'Team Jeff': [
    'Xander Schauffele',
    'Tommy Fleetwood',
    'Tyrrell Hatton',
    'Ben Griffin',
    'Shane Lowry',
  ],
  'Team Josh': [
    'Rory McIlroy',
    'Matt Fitzpatrick',
    'Min Woo Lee',
    'Sam Burns',
    'Harris English',
  ],
  'Team John': [
    'Cameron Young',
    'Viktor Hovland',
    'Russell Henley',
    'Brooks Koepka',
    'Adam Scott',
  ],
  'Team Ben': [
    'Scottie Scheffler',
    'Robert MacIntyre',
    'Patrick Reed',
    'Akshay Bhatia',
    'Jordan Spieth',
  ],
  'Team Mark': [
    'Jon Rahm',
    'Bryson DeChambeau',
    'Hideki Matsuyama',
    'Corey Conners',
    'Cam Smith',
  ],
  'Team Paul': [
    'Ludvig Aberg',
    'Justin Thomas',
    'Justin Rose',
    'Patrick Cantlay',
    'Chris Gotterup',
  ],
};

const PGA_TEAMS = {
  ...MASTERS_TEAMS,
  'Team Josh': [
    'Rory McIlroy',
    'Matt Fitzpatrick',
    'Collin Morikawa',
    'Sam Burns',
    'Harris English',
  ],
  'Team Ben': [
    'Scottie Scheffler',
    'Robert MacIntyre',
    'Jacob Bridgeman',
    'Akshay Bhatia',
    'Jordan Spieth',
  ],
  'Team Mark': [
    'Jon Rahm',
    'Bryson DeChambeau',
    'Hideki Matsuyama',
    'Corey Conners',
    'Sepp Straka',
  ],
  'Team Paul': [
    'Ludvig Aberg',
    'Justin Thomas',
    'Justin Rose',
    'JJ Spaun',
    'Chris Gotterup',
  ],
};

const PGA_BENCH_PLAYERS = {
  'Team Jeff': ['Maverick McNealy', 'Sahith Theegala'],
  'Team Josh': ['Min Woo Lee', 'Nicolai Hojgaard'],
  'Team John': ['Brian Harman', 'Kurt Kitayama'],
  'Team Ben': ['Jake Knapp', 'Patrick Reed'],
  'Team Mark': ['Cam Smith', 'Gary Woodland'],
  'Team Paul': ['Patrick Cantlay', 'Si Woo Kim'],
};

const US_OPEN_TEAMS = {
  ...PGA_TEAMS,
  'Team John': [
    'Cameron Young',
    'Viktor Hovland',
    'Russell Henley',
    'Brian Harman',
    'Adam Scott',
  ],
  'Team Ben': [
    'Scottie Scheffler',
    'Robert MacIntyre',
    'Patrick Reed',
    'Akshay Bhatia',
    'Jordan Spieth',
  ],
  'Team Paul': [
    'Ludvig Aberg',
    'Justin Thomas',
    'Justin Rose',
    'Patrick Cantlay',
    'Chris Gotterup',
  ],
};

const US_OPEN_BENCH_PLAYERS = {
  'Team Jeff': ['Maverick McNealy', 'Sahith Theegala'],
  'Team Josh': ['Min Woo Lee', 'Nicolai Hojgaard'],
  'Team John': ['Brooks Koepka', 'Kurt Kitayama'],
  'Team Ben': ['Jake Knapp', 'Jacob Bridgeman'],
  'Team Mark': ['Cam Smith', 'Gary Woodland'],
  'Team Paul': ['JJ Spaun', 'Si Woo Kim'],
};

// Name aliases to match Masters.com data
const NAME_ALIASES = {
  'Cam Smith': 'Cameron Smith',
  'Ludvig Aberg': 'Ludvig Åberg',
  'Nicolai Hojgaard': 'Nicolai Højgaard',
  'JJ Spaun': 'J.J. Spaun',
};

function parseTopar(topar) {
  if (!topar || topar === 'E') return 0;
  const n = parseInt(topar, 10);
  return isNaN(n) ? 0 : n;
}

function parseRoundScore(fantasy) {
  if (fantasy === null || fantasy === undefined) return null;
  return Number(fantasy);
}

function formatTeamTotal(score) {
  if (score === 0) return 'E';
  return score > 0 ? `+${score}` : `${score}`;
}

function scoreDisplay(score) {
  if (score === null || score === undefined) return '-';
  if (score === 0) return 'E';
  return score > 0 ? `+${score}` : `${score}`;
}

function buildRoundStatusesFromState(state, period) {
  const statuses = ['N', 'N', 'N', 'N'];
  if (state === 'post') return ['F', 'F', 'F', 'F'];
  if (state === 'in') {
    const idx = Math.max(0, Math.min((period || 1) - 1, 3));
    for (let i = 0; i < idx; i += 1) statuses[i] = 'F';
    statuses[idx] = 'A';
  }
  return statuses;
}

function parseEspnRoundValue(display) {
  if (display === null || display === undefined) return null;
  const text = String(display).trim().toUpperCase();
  if (text === '' || text === '-') return null;
  if (text === 'E') return 0;
  const n = parseInt(text, 10);
  return Number.isNaN(n) ? null : n;
}

function emptyTournamentResponse(teamsConfig) {
  return {
    teams: Object.keys(teamsConfig).map((name, idx) => ({
      name,
      players: [],
      benchedPlayers: [],
      teamTopar: 0,
      teamToparDisplay: 'E',
      rank: idx + 1,
    })),
    lastUpdated: '',
    currentRound: 1,
    roundStatuses: ['N', 'N', 'N', 'N'],
    allPlayers: [],
  };
}

function missingPlayer(playerName) {
  return {
    name: playerName,
    pos: 'N/A',
    topar: null,
    toparDisplay: 'N/A',
    total: null,
    status: '',
    thru: '-',
    today: '-',
    rounds: [null, null, null, null],
    notFound: true,
    cut: false,
    wd: false,
    active: false,
  };
}

function buildBenchedPlayers(teamName, playerMap, benchPlayers) {
  return (benchPlayers[teamName] || []).map((playerName) => {
    const apiName = NAME_ALIASES[playerName] || playerName;
    const p = playerMap[apiName];
    return p ? { name: playerName, ...p } : missingPlayer(playerName);
  });
}

function applyEspnDonkeySubstitutions(playerResults, donorPlayers) {
  let cutIdx = 0;
  return playerResults.map((player) => {
    if (!player.cut) return player;

    const donor = donorPlayers[cutIdx];
    if (!donor) {
      cutIdx += 1;
      return player;
    }

    const sub = {
      ...player,
      rounds: [...player.rounds],
      donkeyRoundIdx: [null, null, null, null],
      donkeySubstituted: true,
      donkeyNum: cutIdx + 1,
      donkeyName: donor.name,
    };

    let added = 0;
    [2, 3].forEach((roundIdx) => {
      const donorScore = donor.rounds[roundIdx];
      if (donorScore !== null && donorScore !== undefined) {
        sub.rounds[roundIdx] = donorScore;
        sub.donkeyRoundIdx[roundIdx] = cutIdx;
        added += donorScore;
      }
    });

    sub.topar = (player.topar || 0) + added;
    sub.toparDisplay = formatTeamTotal(sub.topar);
    cutIdx += 1;
    return sub;
  });
}

function leaderFromPlayers(players, nameKey) {
  const scoredPlayers = players.filter(
    (player) =>
      player.topar !== null &&
      player.topar !== undefined &&
      player.topar !== '' &&
      String(player.topar).toUpperCase() !== 'CUT'
  );
  if (scoredPlayers.length === 0) return { name: 'TBD', score: '-' };
  const leader = scoredPlayers.reduce((best, player) =>
    parseTopar(player.topar) < parseTopar(best.topar) ? player : best
  );
  return {
    name: leader[nameKey] || 'TBD',
    score: scoreDisplay(parseTopar(leader.topar)),
  };
}

function projectedCutFromMastersRounds(players, roundKeys, madeCutCount) {
  const twoRoundScores = players
    .map((player) => {
      let hasScore = false;
      const total = roundKeys.reduce((sum, key) => {
        const value = player[key]?.fantasy;
        if (value === null || value === undefined) return sum;
        hasScore = true;
        return sum + value;
      }, 0);
      return hasScore ? total : null;
    })
    .filter((score) => score !== null)
    .sort((a, b) => a - b);

  return twoRoundScores.length >= madeCutCount
    ? scoreDisplay(twoRoundScores[madeCutCount - 1])
    : '-';
}

function buildMastersTournamentInfo(players) {
  const cutPlayers = players.filter((player) => ['C', 'CUT'].includes(player.status));
  const cutLine = cutPlayers.length > 0
    ? scoreDisplay(Math.min(...cutPlayers.map((player) => parseTopar(player.topar))))
    : projectedCutFromMastersRounds(players, ['round1', 'round2'], 50);

  return {
    logoUrl: MASTERS_LOGO_URL,
    logoAlt: 'Masters Tournament logo',
    cutLine,
    cutLineLabel: cutPlayers.length > 0 ? 'Actual cut' : 'Projected cut',
    leader: leaderFromPlayers(players, 'full_name'),
  };
}

function projectedCutFromEspnCompetitors(competitors, madeCutCount) {
  const twoRoundScores = competitors
    .map((competitor) => {
      let hasScore = false;
      const total = (competitor.linescores || []).reduce((sum, line) => {
        if (line.period !== 1 && line.period !== 2) return sum;
        const value = parseEspnRoundValue(line.displayValue);
        if (value === null || value === undefined) return sum;
        hasScore = true;
        return sum + value;
      }, 0);
      return hasScore ? total : null;
    })
    .filter((score) => score !== null)
    .sort((a, b) => a - b);

  return twoRoundScores.length >= madeCutCount
    ? scoreDisplay(twoRoundScores[madeCutCount - 1])
    : '-';
}

function buildEspnTournamentInfo(competitors, currentRound, logoUrl, logoAlt, madeCutCount) {
  return {
    logoUrl,
    logoAlt,
    cutLine: projectedCutFromEspnCompetitors(competitors, madeCutCount),
    cutLineLabel: currentRound > 2 ? 'Actual cut' : 'Projected cut',
    leader: leaderFromPlayers(
      competitors.map((competitor) => ({
        name: competitor.athlete?.fullName,
        topar: competitor.score,
      })),
      'name'
    ),
  };
}

app.use(express.static(path.join(__dirname, 'public')));

async function fetchJson(url, referer) {
  const response = await fetch(url, {
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      ...(referer ? { Referer: referer } : {}),
    },
  });
  if (!response.ok) throw new Error(`${url} returned ${response.status}`);
  return response.json();
}

function buildTeamData(teamsConfig, playerMap, allPlayers, roundStatuses, options = {}) {
  const {
    donorPlayers = [],
    benchPlayers = null,
    applyDonkey = false,
  } = options;

  const teams = Object.entries(teamsConfig).map(([teamName, roster]) => {
    let playerResults = roster.map((playerName) => {
      const apiName = NAME_ALIASES[playerName] || playerName;
      const p = playerMap[apiName];

      if (!p) {
        return missingPlayer(playerName);
      }

      return { name: playerName, ...p };
    });
    if (applyDonkey) {
      playerResults = applyEspnDonkeySubstitutions(playerResults, donorPlayers);
    }

    const teamTopar = playerResults.reduce((sum, p) => {
      if (p.notFound || p.wd) return sum;
      return sum + (p.topar || 0);
    }, 0);

    return {
      name: teamName,
      players: playerResults,
      benchedPlayers: benchPlayers ? buildBenchedPlayers(teamName, playerMap, benchPlayers) : [],
      teamTopar,
      teamToparDisplay: formatTeamTotal(teamTopar),
    };
  });

  teams.sort((a, b) => a.teamTopar - b.teamTopar);
  teams.forEach((team, idx) => {
    team.rank = idx + 1;
  });

  allPlayers.sort((a, b) => a.name.localeCompare(b.name));
  return { teams, allPlayers, roundStatuses };
}

async function buildMastersScoresResponse() {
  const json = await fetchJson(MASTERS_API, 'https://www.masters.com/');
  const { player: players, currentRound, statusRound, wallClockTime } = json.data;
  const roundStatuses = statusRound ? statusRound.split('') : [];
  const playerMap = {};
  const allPlayers = [];

  for (const p of players) {
    const rounds = [
      parseRoundScore(p.round1?.fantasy),
      parseRoundScore(p.round2?.fantasy),
      parseRoundScore(p.round3?.fantasy),
      parseRoundScore(p.round4?.fantasy),
    ];
    roundStatuses.forEach((status, idx) => {
      if (status === 'N') rounds[idx] = null;
    });

    const parsedPlayer = {
      pos: p.pos || '-',
      topar: parseTopar(p.topar),
      toparDisplay: p.topar || 'E',
      total: p.total ? parseInt(p.total, 10) : null,
      status: p.status || '',
      thru: p.thru || '-',
      today: p.today || 'E',
      rounds,
      notFound: false,
      cut: p.status === 'CUT',
      wd: p.status === 'WD',
      active: p.active || false,
    };
    playerMap[p.full_name] = parsedPlayer;
    allPlayers.push({
      name: p.full_name,
      rounds,
      status: p.status || '',
      topar: parseTopar(p.topar),
      pos: p.pos || '-',
    });
  }

  const data = buildTeamData(MASTERS_TEAMS, playerMap, allPlayers, roundStatuses);
  return {
    tournament: 'masters',
    tournamentLabel: 'The Masters',
    tournamentInfo: buildMastersTournamentInfo(players),
    ...data,
    lastUpdated: wallClockTime || new Date().toISOString(),
    currentRound: Math.min(parseInt(currentRound, 10) || 1, 4),
  };
}

async function buildEspnScoresResponse(config) {
  const {
    eventId,
    teams,
    benchPlayers,
    tournamentKey,
    tournamentLabel,
    logoUrl,
    logoAlt,
    madeCutCount,
  } = config;

  const scoreboard = await fetchJson(ESPN_SCOREBOARD_API, 'https://www.espn.com/golf/');
  const event = (scoreboard.events || []).find((e) => e.id === eventId);

  if (!event) {
    const out = {
      ...emptyTournamentResponse(teams),
      tournament: tournamentKey,
      tournamentLabel,
      tournamentInfo: {
        logoUrl,
        logoAlt,
        cutLine: '-',
        cutLineLabel: 'Projected cut',
        leader: { name: 'TBD', score: '-' },
      },
      message: `${tournamentLabel} has not started yet.`,
    };
    out.teams.forEach((team) => {
      team.benchedPlayers = (benchPlayers[team.name] || []).map(missingPlayer);
    });
    return out;
  }

  const competition = (event.competitions || [{}])[0];
  const competitors = competition.competitors || [];
  const status = competition.status || event.status || {};
  const state = status.type?.state || event.status?.type?.state || 'pre';
  const currentRound = Math.max(1, Math.min(4, parseInt(status.period, 10) || 1));
  const roundStatuses = buildRoundStatusesFromState(state, currentRound);
  const playerMap = {};
  const allPlayers = [];

  competitors.forEach((competitor, idx) => {
    const athlete = competitor.athlete || {};
    const fullName = athlete.fullName || athlete.displayName;
    if (!fullName) return;

    const rounds = [null, null, null, null];
    const lines = competitor.linescores || [];
    lines.forEach((line) => {
      if (!line.period || line.period < 1 || line.period > 4) return;
      rounds[line.period - 1] = parseEspnRoundValue(line.displayValue);
    });
    roundStatuses.forEach((status, roundIdx) => {
      if (status === 'N') rounds[roundIdx] = null;
    });

    const todayVal = rounds[currentRound - 1];
    const roundDetail = lines.find((line) => line.period === currentRound);
    const holesPlayed = (roundDetail?.linescores || []).length;
    const scoreDisplay = competitor.score || 'E';
    const hasRound3 = lines.some((line) => line.period === 3);
    const missedCut = currentRound > 2 && !hasRound3;
    const playerStatus = String(scoreDisplay).toUpperCase() === 'CUT' || missedCut ? 'CUT' : '';

    const parsedPlayer = {
      pos: String(idx + 1),
      topar: parseTopar(scoreDisplay),
      toparDisplay: scoreDisplay,
      total: null,
      status: playerStatus,
      thru: holesPlayed > 0 ? String(holesPlayed) : '-',
      today: todayVal === 0 ? 'E' : todayVal !== null && todayVal !== undefined ? String(todayVal) : '-',
      rounds,
      notFound: false,
      cut: playerStatus === 'CUT',
      wd: false,
      active: state === 'in',
    };
    playerMap[fullName] = parsedPlayer;
    allPlayers.push({
      name: fullName,
      rounds,
      status: playerStatus,
      topar: parsedPlayer.topar,
      pos: parsedPlayer.pos,
    });
  });

  const donorPlayers = Object.entries(playerMap)
    .map(([name, player]) => ({ name, ...player }))
    .filter((player) => !player.cut && !player.wd && !player.notFound)
    .sort((a, b) => b.topar - a.topar);

  const data = buildTeamData(teams, playerMap, allPlayers, roundStatuses, {
    donorPlayers,
    benchPlayers,
    applyDonkey: true,
  });
  return {
    tournament: tournamentKey,
    tournamentLabel,
    tournamentInfo: buildEspnTournamentInfo(competitors, currentRound, logoUrl, logoAlt, madeCutCount),
    ...data,
    lastUpdated: scoreboard.day?.date || new Date().toISOString(),
    currentRound,
  };
}

async function buildPgaScoresResponse() {
  return buildEspnScoresResponse({
    eventId: PGA_EVENT_ID,
    teams: PGA_TEAMS,
    benchPlayers: PGA_BENCH_PLAYERS,
    tournamentKey: 'pga',
    tournamentLabel: 'PGA Championship',
    logoUrl: PGA_LOGO_URL,
    logoAlt: 'PGA Championship logo',
    madeCutCount: 70,
  });
}

async function buildUsOpenScoresResponse() {
  return buildEspnScoresResponse({
    eventId: US_OPEN_EVENT_ID,
    teams: US_OPEN_TEAMS,
    benchPlayers: US_OPEN_BENCH_PLAYERS,
    tournamentKey: 'usopen',
    tournamentLabel: 'U.S. Open',
    logoUrl: US_OPEN_LOGO_URL,
    logoAlt: 'U.S. Open at Shinnecock Hills logo',
    madeCutCount: 60,
  });
}

app.get('/api/scores', async (req, res) => {
  try {
    const tournament = String(req.query.tournament || 'masters').toLowerCase();
    const data = tournament === 'pga'
      ? await buildPgaScoresResponse()
      : tournament === 'usopen'
      ? await buildUsOpenScoresResponse()
      : await buildMastersScoresResponse();
    res.json(data);
  } catch (err) {
    console.error('Error fetching scores:', err.message);
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Masters Fantasy Tracker running at http://localhost:${PORT}`);
});
