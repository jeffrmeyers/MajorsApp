#!/usr/bin/env python3
"""
Majors Fantasy League Tracker
Run: python3 server.py
Then open http://localhost:3000 in your browser.
"""

import json
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 3000
MASTERS_API = 'https://www.masters.com/en_US/scores/feeds/2026/scores.json'
PGA_SCOREBOARD_API = 'https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard'
PGA_EVENT_API = 'https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/401811947/competitions/401811947?lang=en&region=us'
PGA_EVENT_ID = '401811947'
MASTERS_LOGO_URL = 'https://upload.wikimedia.org/wikipedia/commons/c/c5/Masters_Tournament.svg'
PGA_LOGO_URL = 'https://wp.logos-download.com/wp-content/uploads/2023/02/USPGA_2022_PGA_Championship_Logo.svg'
PUBLIC_DIR = Path(__file__).parent / 'public'

MASTERS_TEAMS = {
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

PGA_TEAMS = {
    **MASTERS_TEAMS,
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
}

PGA_BENCH_PLAYERS = {
    'Team Jeff': ['Maverick McNealy', 'Sahith Theegala'],
    'Team Josh': ['Min Woo Lee', 'Nicolai Hojgaard'],
    'Team John': ['Brian Harman', 'Kurt Kitayama'],
    'Team Ben': ['Jake Knapp', 'Patrick Reed'],
    'Team Mark': ['Cam Smith', 'Gary Woodland'],
    'Team Paul': ['Patrick Cantlay', 'Si Woo Kim'],
}

# Name aliases: display name -> masters.com full_name
NAME_ALIASES = {
    'Cam Smith': 'Cameron Smith',
    'Ludvig Aberg': 'Ludvig \u00c5berg',
    'Nicolai Hojgaard': 'Nicolai Højgaard',
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


def score_display(score):
    if score is None:
        return '-'
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


def build_empty_response(teams):
    team_data = []
    for i, team_name in enumerate(teams.keys()):
        team_data.append({
            'name': team_name,
            'players': [],
            'benchedPlayers': [],
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


def missing_player(player_name):
    return {
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
    }


def leader_from_players(players, name_key):
    scored_players = [
        p for p in players
        if p.get('topar') not in (None, '') and str(p.get('topar')).upper() != 'CUT'
    ]
    if not scored_players:
        return {'name': 'TBD', 'score': '-'}
    leader = min(scored_players, key=lambda p: parse_topar(p.get('topar')))
    return {
        'name': leader.get(name_key) or 'TBD',
        'score': score_display(parse_topar(leader.get('topar'))),
    }


def projected_cut_from_rounds(players, round_keys, made_cut_count):
    two_round_scores = []
    for p in players:
        total = 0
        has_score = False
        for key in round_keys:
            value = p.get(key, {}).get('fantasy')
            if value is not None:
                total += value
                has_score = True
        if has_score:
            two_round_scores.append(total)
    if len(two_round_scores) < made_cut_count:
        return '-'
    two_round_scores.sort()
    return score_display(two_round_scores[made_cut_count - 1])


def build_masters_tournament_info(players):
    cut_players = [p for p in players if p.get('status') in ('C', 'CUT')]
    if cut_players:
        cut_line = score_display(min(parse_topar(p.get('topar')) for p in cut_players))
        cut_label = 'Actual cut'
    else:
        cut_line = projected_cut_from_rounds(players, ['round1', 'round2'], 50)
        cut_label = 'Projected cut'
    return {
        'logoUrl': MASTERS_LOGO_URL,
        'logoAlt': 'Masters Tournament logo',
        'cutLine': cut_line,
        'cutLineLabel': cut_label,
        'leader': leader_from_players(players, 'full_name'),
    }


def projected_cut_from_espn_competitors(competitors, made_cut_count):
    two_round_scores = []
    for c in competitors:
        total = 0
        has_score = False
        for ls in c.get('linescores') or []:
            if ls.get('period') not in (1, 2):
                continue
            value = parse_espn_round_value(ls.get('displayValue'))
            if value is not None:
                total += value
                has_score = True
        if has_score:
            two_round_scores.append(total)
    if len(two_round_scores) < made_cut_count:
        return '-'
    two_round_scores.sort()
    return score_display(two_round_scores[made_cut_count - 1])


def build_pga_tournament_info(competitors, current_round):
    cut_label = 'Actual cut' if current_round > 2 else 'Projected cut'
    return {
        'logoUrl': PGA_LOGO_URL,
        'logoAlt': 'PGA Championship logo',
        'cutLine': projected_cut_from_espn_competitors(competitors, 70),
        'cutLineLabel': cut_label,
        'leader': leader_from_players(
            [
                {
                    'name': (c.get('athlete') or {}).get('fullName'),
                    'topar': c.get('score'),
                }
                for c in competitors
            ],
            'name',
        ),
    }


def build_benched_players(team_name, player_map):
    bench = []
    for player_name in PGA_BENCH_PLAYERS.get(team_name, []):
        api_name = NAME_ALIASES.get(player_name, player_name)
        p = player_map.get(api_name)
        bench.append({'name': player_name, **p} if p else missing_player(player_name))
    return bench


def apply_pga_donkey_substitutions(player_results, donor_players):
    substituted_players = []
    cut_idx = 0
    for player in player_results:
        if not player.get('cut'):
            substituted_players.append(player)
            continue

        donor = donor_players[cut_idx] if cut_idx < len(donor_players) else None
        if not donor:
            substituted_players.append(player)
            cut_idx += 1
            continue

        sub = {
            **player,
            'rounds': [*player['rounds']],
            'donkeyRoundIdx': [None, None, None, None],
            'donkeySubstituted': True,
            'donkeyNum': cut_idx + 1,
            'donkeyName': donor['name'],
        }

        added = 0
        for round_idx in (2, 3):
            donor_score = donor['rounds'][round_idx]
            if donor_score is not None:
                sub['rounds'][round_idx] = donor_score
                sub['donkeyRoundIdx'][round_idx] = cut_idx
                added += donor_score

        sub['topar'] = (player.get('topar') or 0) + added
        sub['toparDisplay'] = format_team_total(sub['topar'])
        substituted_players.append(sub)
        cut_idx += 1

    return substituted_players


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
    for team_name, roster in MASTERS_TEAMS.items():
        player_results = []
        for player_name in roster:
            api_name = NAME_ALIASES.get(player_name, player_name)
            p = player_map.get(api_name)

            if not p:
                player_results.append(missing_player(player_name))
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
            'benchedPlayers': [],
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
        'tournamentInfo': build_masters_tournament_info(players),
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
        out = build_empty_response(PGA_TEAMS)
        for team in out['teams']:
            team['benchedPlayers'] = [missing_player(name) for name in PGA_BENCH_PLAYERS.get(team['name'], [])]
        out['tournament'] = 'pga'
        out['tournamentLabel'] = 'PGA Championship'
        out['tournamentInfo'] = {
            'logoUrl': PGA_LOGO_URL,
            'logoAlt': 'PGA Championship logo',
            'cutLine': '-',
            'cutLineLabel': 'Projected cut',
            'leader': {'name': 'TBD', 'score': '-'},
        }
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
        has_round_3 = any(ls.get('period') == 3 for ls in lines)
        missed_cut = current_round > 2 and not has_round_3
        player_status = 'CUT' if str(score_display).upper() == 'CUT' or missed_cut else ''
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

    donor_players = sorted(
        (
            {'name': full_name, **p}
            for full_name, p in player_map.items()
            if not p['cut'] and not p['wd'] and not p['notFound']
        ),
        key=lambda p: p['topar'],
        reverse=True,
    )

    team_data = []
    for team_name, roster in PGA_TEAMS.items():
        player_results = []
        for player_name in roster:
            api_name = NAME_ALIASES.get(player_name, player_name)
            p = player_map.get(api_name)
            if not p:
                player_results.append(missing_player(player_name))
            else:
                player_results.append({'name': player_name, **p})

        player_results = apply_pga_donkey_substitutions(player_results, donor_players)
        team_topar = sum(
            (r['topar'] or 0)
            for r in player_results
            if not r['notFound'] and not r['wd']
        )
        team_data.append({
            'name': team_name,
            'players': player_results,
            'benchedPlayers': build_benched_players(team_name, player_map),
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
        'tournamentInfo': build_pga_tournament_info(competitors, current_round),
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
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/scores':
            try:
                query = parse_qs(parsed.query)
                tournament = query.get('tournament', ['masters'])[0]
                result = build_scores_response(tournament)
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
