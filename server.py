#!/usr/bin/env python3
"""
Masters Fantasy League Tracker
Run: python3 server.py
Then open http://localhost:3000 in your browser.
"""

import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 3000
MASTERS_API = 'https://www.masters.com/en_US/scores/feeds/2026/scores.json'
PUBLIC_DIR = Path(__file__).parent / 'public'

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

# Name aliases: display name -> masters.com full_name
NAME_ALIASES = {
    'Cam Smith': 'Cameron Smith',
    'Ludvig Aberg': 'Ludvig \u00c5berg',
}

MIME_TYPES = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.ico': 'image/x-icon',
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
            # Convert 0-value rounds that are pre-tournament to None
            for i, (r, rs) in enumerate(zip(rounds, round_statuses)):
                if rs == 'N':
                    rounds[i] = None

            topar_val = parse_topar(p.get('topar', 'E'))
            player_status = p.get('status', '')
            is_cut = player_status == 'CUT'
            is_wd = player_status == 'WD'

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
                'cut': is_cut,
                'wd': is_wd,
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
        cr = int(current_round)
        current_round_out = min(cr, 4)
    except (ValueError, TypeError):
        current_round_out = 1

    return {
        'teams': team_data,
        'lastUpdated': wall_clock,
        'currentRound': current_round_out,
        'roundStatuses': round_statuses,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f'  {self.address_string()} - {fmt % args}')

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        suffix = path.suffix.lower()
        mime = MIME_TYPES.get(suffix, 'application/octet-stream')
        data = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split('?')[0]

        if path == '/api/scores':
            try:
                result = build_scores_response()
                self.send_json(result)
            except Exception as e:
                print(f'  ERROR: {e}')
                self.send_json({'error': str(e)}, 500)
            return

        # Serve static files
        if path == '/' or path == '':
            path = '/index.html'

        file_path = PUBLIC_DIR / path.lstrip('/')
        if file_path.exists() and file_path.is_file():
            self.send_file(file_path)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')


if __name__ == '__main__':
    server = HTTPServer(('', PORT), Handler)
    print(f'\n  Masters Fantasy League Tracker')
    print(f'  ================================')
    print(f'  Open http://localhost:{PORT} in your browser')
    print(f'  Press Ctrl+C to stop\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  Server stopped.')
