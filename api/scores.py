import json
import urllib.request
from http.server import BaseHTTPRequestHandler

MASTERS_API = 'https://www.masters.com/en_US/scores/feeds/2026/scores.json'

TEAMS = {
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
}

NAME_ALIASES = {
    'Cam Smith': 'Cameron Smith',
    'Ludvig Aberg': 'Ludvig \u00c5berg',
}


def parse_topar(topar):
    if not topar or topar == 'E':
        return 0
    try:
        return int(topar)
    except (ValueError, TypeError):
        return 0


def build_scores_response():
    req = urllib.request.Request(
        MASTERS_API,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.masters.com/',
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = json.loads(resp.read().decode('utf-8'))

    data = raw['data']
    players = data['player']
    current_round = data.get('currentRound', '1')
    status_round = data.get('statusRound', '')
    wall_clock = data.get('wallClockTime', '')

    player_map = {p['full_name']: p for p in players}
    round_statuses = list(status_round) if status_round else []

    team_data = []
    for team_name, roster in TEAMS.items():
        player_results = []
        for player_name in roster:
            api_name = NAME_ALIASES.get(player_name, player_name)
            p = player_map.get(api_name)

            if not p:
                player_results.append({
                    'name': player_name,
                    'pos': 'N/A',
                    'topar': None,
                    'toparDisplay': 'N/A',
                    'total': None,
                    'status': '',
                    'thru': '-',
                    'today': '-',
                    'rounds': [None, None, None, None],
                    'notFound': True,
                    'cut': False,
                    'wd': False,
                    'active': False,
                })
                continue

            rounds = [
                p.get('round1', {}).get('fantasy'),
                p.get('round2', {}).get('fantasy'),
                p.get('round3', {}).get('fantasy'),
                p.get('round4', {}).get('fantasy'),
            ]
            for i, rs in enumerate(round_statuses):
                if rs == 'N':
                    rounds[i] = None

            topar_val = parse_topar(p.get('topar', 'E'))
            player_status = p.get('status', '')

            player_results.append({
                'name': player_name,
                'pos': p.get('pos', '-'),
                'topar': topar_val,
                'toparDisplay': p.get('topar', 'E') or 'E',
                'total': int(p['total']) if p.get('total') else None,
                'status': player_status,
                'thru': p.get('thru', '-'),
                'today': p.get('today', 'E'),
                'rounds': rounds,
                'notFound': False,
                'cut': player_status == 'CUT',
                'wd': player_status == 'WD',
                'active': bool(p.get('active', False)),
            })

        team_topar = sum(
            (r['topar'] or 0)
            for r in player_results
            if not r['notFound'] and not r['wd']
        )
        display = (
            'E' if team_topar == 0
            else f'+{team_topar}' if team_topar > 0
            else str(team_topar)
        )
        team_data.append({
            'name': team_name,
            'players': player_results,
            'teamTopar': team_topar,
            'teamToparDisplay': display,
        })

    team_data.sort(key=lambda t: t['teamTopar'])
    for i, t in enumerate(team_data):
        t['rank'] = i + 1

    try:
        current_round_out = min(int(current_round), 4)
    except (ValueError, TypeError):
        current_round_out = 1

    # Full player list for donkey player lookup
    all_players_out = []
    for p in players:
        p_rounds = [
            p.get('round1', {}).get('fantasy'),
            p.get('round2', {}).get('fantasy'),
            p.get('round3', {}).get('fantasy'),
            p.get('round4', {}).get('fantasy'),
        ]
        for i, rs in enumerate(round_statuses):
            if rs == 'N':
                p_rounds[i] = None
        all_players_out.append({
            'name': p['full_name'],
            'rounds': p_rounds,
            'status': p.get('status', ''),
            'topar': parse_topar(p.get('topar', 'E')),
            'pos': p.get('pos', '-'),
        })
    all_players_out.sort(key=lambda p: p['name'])

    return {
        'teams': team_data,
        'lastUpdated': wall_clock,
        'currentRound': current_round_out,
        'roundStatuses': round_statuses,
        'allPlayers': all_players_out,
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            result = build_scores_response()
            body = json.dumps(result).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            body = json.dumps({'error': str(e)}).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass
