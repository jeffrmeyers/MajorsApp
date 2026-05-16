import json
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

MASTERS_API = 'https://www.masters.com/en_US/scores/feeds/2026/scores.json'
PGA_SCOREBOARD_API = 'https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard'
PGA_EVENT_API = 'https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/401811947/competitions/401811947?lang=en&region=us'
PGA_EVENT_ID = '401811947'

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


def fetch_json(url, referer=''):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    if referer:
        headers['Referer'] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode('utf-8'))


def format_team_total(score):
    if score == 0:
        return 'E'
    if score > 0:
        return f'+{score}'
    return str(score)


def build_round_statuses_from_state(state, period):
    statuses = ['N', 'N', 'N', 'N']
    if state == 'post':
        return ['F', 'F', 'F', 'F']
    if state == 'in':
        idx = max(0, min((period or 1) - 1, 3))
        for i in range(idx):
            statuses[i] = 'F'
        statuses[idx] = 'A'
    return statuses


def parse_espn_round_value(display):
    if display is None:
        return None
    text = str(display).strip().upper()
    if text == '' or text == '-':
        return None
    if text == 'E':
        return 0
    try:
        return int(text)
    except ValueError:
        return None


def build_empty_response():
    team_data = []
    for i, team_name in enumerate(TEAMS.keys()):
        team_data.append({
            'name': team_name,
            'players': [],
            'teamTopar': 0,
            'teamToparDisplay': 'E',
            'rank': i + 1,
        })

    return {
        'teams': team_data,
        'lastUpdated': '',
        'currentRound': 1,
        'roundStatuses': ['N', 'N', 'N', 'N'],
        'allPlayers': [],
    }


def build_masters_scores_response():
    raw = fetch_json(MASTERS_API, referer='https://www.masters.com/')

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
        'tournament': 'masters',
        'tournamentLabel': 'The Masters',
        'teams': team_data,
        'lastUpdated': wall_clock,
        'currentRound': current_round_out,
        'roundStatuses': round_statuses,
        'allPlayers': all_players_out,
    }


def build_pga_scores_response():
    scoreboard = fetch_json(PGA_SCOREBOARD_API, referer='https://www.espn.com/golf/')
    events = scoreboard.get('events', [])
    event = next((e for e in events if e.get('id') == PGA_EVENT_ID), None)

    if not event:
        out = build_empty_response()
        out['tournament'] = 'pga'
        out['tournamentLabel'] = 'PGA Championship'
        out['message'] = 'PGA Championship has not started yet.'
        try:
            event_meta = fetch_json(PGA_EVENT_API, referer='https://www.espn.com/golf/')
            status_ref = event_meta.get('status', {}).get('$ref')
            if status_ref:
                status = fetch_json(status_ref)
                detail = status.get('type', {}).get('detail', '')
                if detail:
                    out['message'] = f'PGA Championship starts {detail}.'
        except Exception:
            pass
        return out

    competition = (event.get('competitions') or [{}])[0]
    competitors = competition.get('competitors') or []
    status = competition.get('status') or event.get('status', {})
    status_type = status.get('type') or event.get('status', {}).get('type', {})
    state = status_type.get('state', 'pre')
    current_round = max(1, min(4, int(status.get('period') or 1)))
    round_statuses = build_round_statuses_from_state(state, current_round)

    player_map = {}
    for idx, c in enumerate(competitors):
        athlete = c.get('athlete') or {}
        full_name = athlete.get('fullName') or athlete.get('displayName')
        if not full_name:
            continue

        rounds = [None, None, None, None]
        lines = c.get('linescores') or []
        for ls in lines:
            period = ls.get('period')
            if not period or period < 1 or period > 4:
                continue
            rounds[period - 1] = parse_espn_round_value(ls.get('displayValue'))
        for i, rs in enumerate(round_statuses):
            if rs == 'N':
                rounds[i] = None

        today_val = rounds[current_round - 1] if 1 <= current_round <= 4 else None
        round_detail = next((ls for ls in lines if ls.get('period') == current_round), None)
        holes_played = len((round_detail or {}).get('linescores') or [])
        score_display = c.get('score', 'E') or 'E'
        player_status = 'CUT' if str(score_display).upper() == 'CUT' else ''

        player_map[full_name] = {
            'pos': str(idx + 1),
            'topar': parse_topar(score_display),
            'toparDisplay': score_display,
            'total': None,
            'status': player_status,
            'thru': str(holes_played) if holes_played > 0 else '-',
            'today': 'E' if today_val == 0 else (str(today_val) if today_val is not None else '-'),
            'rounds': rounds,
            'notFound': False,
            'cut': player_status == 'CUT',
            'wd': False,
            'active': state == 'in',
        }

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
            else:
                player_results.append({'name': player_name, **p})

        team_topar = sum(
            (r['topar'] or 0)
            for r in player_results
            if not r['notFound'] and not r['wd']
        )
        team_data.append({
            'name': team_name,
            'players': player_results,
            'teamTopar': team_topar,
            'teamToparDisplay': format_team_total(team_topar),
        })

    team_data.sort(key=lambda t: t['teamTopar'])
    for i, t in enumerate(team_data):
        t['rank'] = i + 1

    all_players_out = []
    for full_name, p in player_map.items():
        all_players_out.append({
            'name': full_name,
            'rounds': p['rounds'],
            'status': p['status'],
            'topar': p['topar'],
            'pos': p['pos'],
        })
    all_players_out.sort(key=lambda p: p['name'])

    return {
        'tournament': 'pga',
        'tournamentLabel': 'PGA Championship',
        'teams': team_data,
        'lastUpdated': scoreboard.get('day', {}).get('date', ''),
        'currentRound': current_round,
        'roundStatuses': round_statuses,
        'allPlayers': all_players_out,
    }


def build_scores_response(tournament='masters'):
    tournament_key = (tournament or 'masters').lower()
    if tournament_key == 'pga':
        return build_pga_scores_response()
    return build_masters_scores_response()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            tournament = query.get('tournament', ['masters'])[0]
            result = build_scores_response(tournament)
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
