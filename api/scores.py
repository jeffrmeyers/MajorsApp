import json
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

MASTERS_API = 'https://www.masters.com/en_US/scores/feeds/2026/scores.json'
ESPN_SCOREBOARD_API = 'https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard'
PGA_EVENT_API = 'https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/401811947/competitions/401811947?lang=en&region=us'
PGA_EVENT_ID = '401811947'
US_OPEN_EVENT_API = 'https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/401811952/competitions/401811952?lang=en&region=us'
US_OPEN_EVENT_ID = '401811952'
MASTERS_LOGO_URL = 'https://upload.wikimedia.org/wikipedia/commons/c/c5/Masters_Tournament.svg'
PGA_LOGO_URL = 'https://wp.logos-download.com/wp-content/uploads/2023/02/USPGA_2022_PGA_Championship_Logo.svg'
US_OPEN_LOGO_URL = 'https://filecache.mediaroom.com/mr5mr_usga2/191226/2026-USO_SHINNECOCK_FULL-COLOR%20%281%29.jpg'

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
    'Team Paul': [
        'Ludvig Aberg',
        'Justin Thomas',
        'Justin Rose',
        'JJ Spaun',
        'Chris Gotterup',
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

US_OPEN_TEAMS = {
    **PGA_TEAMS,
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
}

US_OPEN_BENCH_PLAYERS = {
    'Team Jeff': ['Maverick McNealy', 'Sahith Theegala'],
    'Team Josh': ['Min Woo Lee', 'Nicolai Hojgaard'],
    'Team John': ['Brooks Koepka', 'Kurt Kitayama'],
    'Team Ben': ['Jake Knapp', 'Jacob Bridgeman'],
    'Team Mark': ['Cam Smith', 'Gary Woodland'],
    'Team Paul': ['JJ Spaun', 'Si Woo Kim'],
}

US_OPEN_DONKEY_PLAYERS = ['Neal Shipley', 'Marek Flemming', 'Erik Lee']

NAME_ALIASES = {
    'Cam Smith': 'Cameron Smith',
    'Ludvig Aberg': 'Ludvig \u00c5berg',
    'Nicolai Hojgaard': 'Nicolai Højgaard',
    'JJ Spaun': 'J.J. Spaun',
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


def scoreboard_date_param(iso_date):
    if not iso_date:
        return None
    return iso_date[:10].replace('-', '')


def fetch_espn_event(event_id, event_api):
    referer = 'https://www.espn.com/golf/'
    scoreboard = fetch_json(ESPN_SCOREBOARD_API, referer=referer)
    event = next((e for e in scoreboard.get('events', []) if e.get('id') == event_id), None)
    if event:
        return event, scoreboard

    try:
        event_meta = fetch_json(event_api, referer=referer)
        for date_field in ('endDate', 'date'):
            date_param = scoreboard_date_param(event_meta.get(date_field))
            if not date_param:
                continue
            dated_scoreboard = fetch_json(
                f'{ESPN_SCOREBOARD_API}?dates={date_param}',
                referer=referer,
            )
            event = next(
                (e for e in dated_scoreboard.get('events', []) if e.get('id') == event_id),
                None,
            )
            if event:
                return event, dated_scoreboard
    except Exception:
        pass

    return None, scoreboard


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
        finished = max(1, min(4, int(period or 1)))
        for i in range(finished):
            statuses[i] = 'F'
        return statuses
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


def competitor_has_completed_round(lines, period):
    line = next((ls for ls in lines if ls.get('period') == period), None)
    if not line:
        return False
    return parse_espn_round_value(line.get('displayValue')) is not None


def competitor_started_round(lines, period):
    line = next((ls for ls in lines if ls.get('period') == period), None)
    if not line:
        return False
    if parse_espn_round_value(line.get('displayValue')) is not None:
        return True
    return len((line.get('linescores') or [])) > 0


def espn_cut_line_value(competitors, made_cut_count):
    scores = []
    for c in competitors:
        score_display = c.get('score', 'E') or 'E'
        if str(score_display).upper() == 'CUT':
            continue
        lines = c.get('linescores') or []
        if not competitor_has_completed_round(lines, 1):
            continue
        if not competitor_has_completed_round(lines, 2):
            continue
        scores.append(parse_topar(score_display))
    if len(scores) < made_cut_count:
        return None
    scores.sort()
    return scores[made_cut_count - 1]


def espn_cut_is_known(state, current_round, competitors):
    if current_round > 2:
        return True
    if current_round == 2 and state == 'post':
        return True
    if current_round == 2 and state == 'in':
        return any(
            competitor_started_round(c.get('linescores') or [], 3)
            for c in competitors
        )
    return False


def espn_player_missed_cut(competitor, cut_line, cut_is_known):
    score_display = competitor.get('score', 'E') or 'E'
    if str(score_display).upper() == 'CUT':
        return True
    if not cut_is_known or cut_line is None:
        return False
    lines = competitor.get('linescores') or []
    if competitor_started_round(lines, 3) or competitor_started_round(lines, 4):
        return False
    return parse_topar(score_display) > cut_line


def build_espn_tournament_info(competitors, current_round, logo_url, logo_alt, made_cut_count, cut_is_known):
    cut_label = 'Actual cut' if cut_is_known else 'Projected cut'
    return {
        'logoUrl': logo_url,
        'logoAlt': logo_alt,
        'cutLine': projected_cut_from_espn_competitors(competitors, made_cut_count),
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


def build_benched_players(team_name, player_map, bench_players):
    bench = []
    for player_name in bench_players.get(team_name, []):
        api_name = NAME_ALIASES.get(player_name, player_name)
        p = player_map.get(api_name)
        bench.append({'name': player_name, **p} if p else missing_player(player_name))
    return bench


def apply_espn_donkey_substitutions(player_results, donor_players):
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
            'benchedPlayers': [],
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
        'tournamentInfo': build_masters_tournament_info(players),
        'teams': team_data,
        'lastUpdated': wall_clock,
        'currentRound': current_round_out,
        'roundStatuses': round_statuses,
        'allPlayers': all_players_out,
    }


def build_espn_scores_response(
    event_id,
    event_api,
    teams,
    bench_players,
    tournament_key,
    tournament_label,
    logo_url,
    logo_alt,
    made_cut_count=70,
    preset_donkey_players=None,
):
    event, scoreboard = fetch_espn_event(event_id, event_api)

    if not event:
        out = build_empty_response(teams)
        for team in out['teams']:
            team['benchedPlayers'] = [
                missing_player(name) for name in bench_players.get(team['name'], [])
            ]
        out['tournament'] = tournament_key
        out['tournamentLabel'] = tournament_label
        out['tournamentInfo'] = {
            'logoUrl': logo_url,
            'logoAlt': logo_alt,
            'cutLine': '-',
            'cutLineLabel': 'Projected cut',
            'leader': {'name': 'TBD', 'score': '-'},
        }
        out['message'] = f'{tournament_label} has not started yet.'
        try:
            event_meta = fetch_json(event_api, referer='https://www.espn.com/golf/')
            status_ref = event_meta.get('status', {}).get('$ref')
            if status_ref:
                status = fetch_json(status_ref)
                detail = status.get('type', {}).get('detail', '')
                if detail:
                    out['message'] = f'{tournament_label} starts {detail}.'
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
    cut_is_known = espn_cut_is_known(state, current_round, competitors)
    cut_line = espn_cut_line_value(competitors, made_cut_count)

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
        missed_cut = espn_player_missed_cut(c, cut_line, cut_is_known)
        player_status = 'CUT' if missed_cut else ''

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

    if preset_donkey_players:
        donor_players = []
        for name in preset_donkey_players:
            api_name = NAME_ALIASES.get(name, name)
            p = player_map.get(api_name)
            donor_players.append({'name': name, **p} if p else missing_player(name))
    else:
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
    for team_name, roster in teams.items():
        player_results = []
        for player_name in roster:
            api_name = NAME_ALIASES.get(player_name, player_name)
            p = player_map.get(api_name)
            if not p:
                player_results.append(missing_player(player_name))
            else:
                player_results.append({'name': player_name, **p})

        player_results = apply_espn_donkey_substitutions(player_results, donor_players)
        team_topar = sum(
            (r['topar'] or 0)
            for r in player_results
            if not r['notFound'] and not r['wd']
        )
        team_data.append({
            'name': team_name,
            'players': player_results,
            'benchedPlayers': build_benched_players(team_name, player_map, bench_players),
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

    donkey_players_info = None
    if preset_donkey_players:
        donkey_players_info = []
        for i, d in enumerate(donor_players):
            donkey_players_info.append({
                'num': i + 1,
                'name': d['name'],
                'pos': d.get('pos', '-'),
                'topar': d.get('topar'),
                'toparDisplay': d.get('toparDisplay', 'N/A'),
                'status': d.get('status', ''),
                'rounds': d.get('rounds', [None, None, None, None]),
            })

    return {
        'tournament': tournament_key,
        'tournamentLabel': tournament_label,
        'tournamentInfo': build_espn_tournament_info(
            competitors, current_round, logo_url, logo_alt, made_cut_count, cut_is_known
        ),
        'teams': team_data,
        'lastUpdated': scoreboard.get('day', {}).get('date', ''),
        'currentRound': current_round,
        'roundStatuses': round_statuses,
        'allPlayers': all_players_out,
        'donkeyPlayersInfo': donkey_players_info,
    }


def build_pga_scores_response():
    return build_espn_scores_response(
        PGA_EVENT_ID,
        PGA_EVENT_API,
        PGA_TEAMS,
        PGA_BENCH_PLAYERS,
        'pga',
        'PGA Championship',
        PGA_LOGO_URL,
        'PGA Championship logo',
        made_cut_count=70,
    )


def build_us_open_scores_response():
    return build_espn_scores_response(
        US_OPEN_EVENT_ID,
        US_OPEN_EVENT_API,
        US_OPEN_TEAMS,
        US_OPEN_BENCH_PLAYERS,
        'usopen',
        'U.S. Open',
        US_OPEN_LOGO_URL,
        'U.S. Open at Shinnecock Hills logo',
        made_cut_count=60,
        preset_donkey_players=US_OPEN_DONKEY_PLAYERS,
    )


def build_season_scores_response():
    TOURNAMENT_KEYS = ['masters', 'pga', 'usopen', 'theopen']
    TOURNAMENT_LABELS = {
        'masters': 'Masters',
        'pga': 'PGA Champ.',
        'usopen': 'U.S. Open',
        'theopen': 'The Open',
    }

    builders = {
        'masters': build_masters_scores_response,
        'pga': build_pga_scores_response,
        'usopen': build_us_open_scores_response,
    }

    tournament_results = {}
    for key, builder in builders.items():
        try:
            result = builder()
            tournament_results[key] = {team['name']: team['teamTopar'] for team in result.get('teams', [])}
        except Exception:
            tournament_results[key] = {}

    team_names = list(MASTERS_TEAMS.keys())
    season_data = []
    for team_name in team_names:
        scores = {key: tournament_results.get(key, {}).get(team_name) for key in TOURNAMENT_KEYS}
        played = [s for s in scores.values() if s is not None]
        season_total = sum(played) if played else None

        season_data.append({
            'name': team_name,
            **{key: scores[key] for key in TOURNAMENT_KEYS},
            **{f'{key}Display': score_display(scores[key]) if scores[key] is not None else '-' for key in TOURNAMENT_KEYS},
            'seasonTotal': season_total,
            'seasonTotalDisplay': score_display(season_total) if season_total is not None else '-',
        })

    season_data.sort(key=lambda t: (t['seasonTotal'] is None, t['seasonTotal'] or 0))

    leader_total = season_data[0]['seasonTotal'] if season_data and season_data[0]['seasonTotal'] is not None else None
    for i, team in enumerate(season_data):
        team['rank'] = i + 1
        if leader_total is not None and team['seasonTotal'] is not None:
            back = team['seasonTotal'] - leader_total
            team['back'] = back
            team['backDisplay'] = '-' if back == 0 else f'+{back}'
        else:
            team['back'] = None
            team['backDisplay'] = '-'

    return {
        'tournament': 'season',
        'tournamentLabel': '2026 Season Standings',
        'tournamentKeys': TOURNAMENT_KEYS,
        'tournamentLabels': TOURNAMENT_LABELS,
        'teams': season_data,
    }


def build_scores_response(tournament='masters'):
    tournament_key = (tournament or 'masters').lower()
    if tournament_key == 'pga':
        return build_pga_scores_response()
    if tournament_key == 'usopen':
        return build_us_open_scores_response()
    if tournament_key == 'season':
        return build_season_scores_response()
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
