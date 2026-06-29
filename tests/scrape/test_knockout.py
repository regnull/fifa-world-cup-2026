import responses as resp
from scrape.knockout import fetch_knockout_results

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"


def _knockout_event(home, hg, away, ag, note="FIFA World Cup, Round of 32", completed=True):
    return {
        "competitions": [
            {
                "altGameNote": note,
                "status": {"type": {"completed": completed}},
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": home},
                     "score": str(hg), "winner": hg > ag},
                    {"homeAway": "away", "team": {"displayName": away},
                     "score": str(ag), "winner": ag > hg},
                ],
            }
        ]
    }


@resp.activate
def test_fetch_completed_knockout_result():
    body = {"events": [_knockout_event("Brazil", 2, "Japan", 1)]}
    resp.add(resp.GET, ESPN_URL, json=body, status=200)
    results = fetch_knockout_results(use_cache=False)
    key = frozenset({"Brazil", "Japan"})
    assert key in results
    assert results[key].winner == "Brazil"
    assert results[key].home_goals == 2 and results[key].away_goals == 1


@resp.activate
def test_orientation_independent_key():
    body = {"events": [_knockout_event("South Africa", 0, "Canada", 1)]}
    resp.add(resp.GET, ESPN_URL, json=body, status=200)
    results = fetch_knockout_results(use_cache=False)
    # Lookup works regardless of which team is named first.
    assert results[frozenset({"Canada", "South Africa"})].winner == "Canada"


@resp.activate
def test_incomplete_knockout_game_excluded():
    body = {"events": [_knockout_event("Germany", 0, "Paraguay", 0, completed=False)]}
    resp.add(resp.GET, ESPN_URL, json=body, status=200)
    assert fetch_knockout_results(use_cache=False) == {}


@resp.activate
def test_group_games_excluded():
    body = {"events": [_knockout_event("France", 2, "Poland", 0,
                                       note="FIFA World Cup, Group D")]}
    resp.add(resp.GET, ESPN_URL, json=body, status=200)
    assert fetch_knockout_results(use_cache=False) == {}
