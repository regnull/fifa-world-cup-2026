import responses as resp
from scrape.schedule import fetch_fixtures
from scrape.models import Fixture

SAMPLE_SCOREBOARD = {
    "events": [
        {
            "date": "2026-06-28T18:00Z",
            "competitions": [
                {
                    "competitors": [
                        {"homeAway": "home", "team": {"displayName": "France"}},
                        {"homeAway": "away", "team": {"displayName": "Poland"}},
                    ],
                    "status": {"type": {"completed": False}},
                    "notes": [{"headline": "Group D"}],
                }
            ],
        }
    ]
}

ESPN_SCHED_URL = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/scoreboard"

@resp.activate
def test_fetch_fixtures_returns_unplayed():
    resp.add(resp.GET, ESPN_SCHED_URL, json=SAMPLE_SCOREBOARD, status=200)
    result = fetch_fixtures(use_cache=False)
    assert len(result) == 1
    f = result[0]
    assert f.home == "France"
    assert f.away == "Poland"
    assert f.completed is False

@resp.activate
def test_fetch_fixtures_filters_completed():
    data = dict(SAMPLE_SCOREBOARD)
    data["events"][0]["competitions"][0]["status"]["type"]["completed"] = True
    resp.add(resp.GET, ESPN_SCHED_URL, json=data, status=200)
    result = fetch_fixtures(use_cache=False)
    assert len(result) == 0
