import json
import responses as resp
from scrape.standings import fetch_standings
from scrape.models import TeamStanding

SAMPLE_STANDINGS = {
    "standings": {
        "groups": [
            {
                "name": "Group A",
                "standings": {
                    "entries": [
                        {
                            "team": {"displayName": "Brazil"},
                            "stats": [
                                {"name": "gamesPlayed", "value": 2.0},
                                {"name": "wins", "value": 2.0},
                                {"name": "ties", "value": 0.0},
                                {"name": "losses", "value": 0.0},
                                {"name": "pointsFor", "value": 5.0},
                                {"name": "pointsAgainst", "value": 1.0},
                                {"name": "pointDifferential", "value": 4.0},
                                {"name": "points", "value": 6.0},
                            ],
                        }
                    ]
                },
            }
        ]
    }
}

ESPN_URL = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"

@resp.activate
def test_fetch_standings_returns_list():
    resp.add(resp.GET, ESPN_URL, json=SAMPLE_STANDINGS, status=200)
    result = fetch_standings(use_cache=False)
    assert isinstance(result, list)
    assert len(result) == 1

@resp.activate
def test_fetch_standings_parses_fields():
    resp.add(resp.GET, ESPN_URL, json=SAMPLE_STANDINGS, status=200)
    result = fetch_standings(use_cache=False)
    s = result[0]
    assert s.group == "A"
    assert s.team == "Brazil"
    assert s.played == 2
    assert s.won == 2
    assert s.drawn == 0
    assert s.lost == 0
    assert s.gf == 5
    assert s.ga == 1
    assert s.gd == 4
    assert s.points == 6
