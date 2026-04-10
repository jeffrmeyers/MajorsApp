const express = require('express');
const fetch = require('node-fetch');
const path = require('path');

const app = express();
const PORT = 3000;

const MASTERS_API = 'https://www.masters.com/en_US/scores/feeds/2026/scores.json';

const TEAMS = {
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

// Name aliases to match Masters.com data
const NAME_ALIASES = {
  'Cam Smith': 'Cameron Smith',
  'Ludvig Aberg': 'Ludvig Åberg',
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

app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/scores', async (req, res) => {
  try {
    const response = await fetch(MASTERS_API, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        Referer: 'https://www.masters.com/',
      },
    });

    if (!response.ok) {
      throw new Error(`Masters API returned ${response.status}`);
    }

    const json = await response.json();
    const { player: players, currentRound, statusRound, wallClockTime } = json.data;

    // Build player lookup by full name
    const playerMap = {};
    for (const p of players) {
      playerMap[p.full_name] = p;
    }

    // Determine active rounds from statusRound (F=Finished, A=Active, N=Not started)
    const roundStatuses = statusRound ? statusRound.split('') : [];
    const activeRoundIndex = roundStatuses.findIndex((s) => s === 'A');
    const lastFinishedRound = roundStatuses.lastIndexOf('F');

    const teamData = {};

    for (const [teamName, roster] of Object.entries(TEAMS)) {
      const playerResults = roster.map((playerName) => {
        const apiName = NAME_ALIASES[playerName] || playerName;
        const p = playerMap[apiName];

        if (!p) {
          return {
            name: playerName,
            pos: 'N/A',
            topar: null,
            total: null,
            status: 'WD',
            thru: '-',
            rounds: [null, null, null, null],
            notFound: true,
          };
        }

        const rounds = [
          parseRoundScore(p.round1?.fantasy),
          parseRoundScore(p.round2?.fantasy),
          parseRoundScore(p.round3?.fantasy),
          parseRoundScore(p.round4?.fantasy),
        ];

        return {
          name: playerName,
          pos: p.pos || '-',
          topar: parseTopar(p.topar),
          toparDisplay: p.topar || 'E',
          total: p.total ? parseInt(p.total) : null,
          status: p.status || '',
          thru: p.thru || '-',
          today: p.today || 'E',
          rounds,
          active: p.active || false,
          cut: p.status === 'CUT',
          wd: p.status === 'WD',
        };
      });

      const teamTopar = playerResults.reduce((sum, p) => {
        if (p.notFound || p.wd) return sum;
        return sum + (p.topar || 0);
      }, 0);

      teamData[teamName] = {
        players: playerResults,
        teamTopar,
        teamToparDisplay: teamTopar === 0 ? 'E' : teamTopar > 0 ? `+${teamTopar}` : `${teamTopar}`,
      };
    }

    // Sort teams by topar
    const sortedTeams = Object.entries(teamData)
      .sort((a, b) => a[1].teamTopar - b[1].teamTopar)
      .map(([name, data], idx) => ({ rank: idx + 1, name, ...data }));

    res.json({
      teams: sortedTeams,
      lastUpdated: wallClockTime || new Date().toISOString(),
      currentRound: parseInt(currentRound) > 4 ? 4 : parseInt(currentRound),
      roundStatuses,
    });
  } catch (err) {
    console.error('Error fetching Masters data:', err.message);
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Masters Fantasy Tracker running at http://localhost:${PORT}`);
});
