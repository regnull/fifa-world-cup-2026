import unittest.mock as mock
import requests
import responses as resp
from scrape.odds import fetch_odds, _parse_odds_row

ESPN_ODDS_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

SAMPLE_SCOREBOARD = {
    "events": [
        {
            "competitions": [
                {
                    "competitors": [
                        {"homeAway": "home", "team": {"displayName": "Croatia"}},
                        {"homeAway": "away", "team": {"displayName": "Ghana"}},
                    ],
                    "status": {"type": {"completed": False}},
                    "altGameNote": "FIFA World Cup, Group L",
                    "odds": [
                        {
                            "moneyline": {
                                "home": {"close": {"odds": "-110"}},
                                "away": {"close": {"odds": "+425"}},
                                "draw": {"close": {"odds": "+210"}},
                            }
                        }
                    ],
                }
            ]
        }
    ]
}


def test_parse_odds_row():
    home, away, oh, od, oa = _parse_odds_row("France - Brazil", "2.50", "3.20", "2.80")
    assert home == "France"
    assert away == "Brazil"
    assert oh == 2.50
    assert od == 3.20
    assert oa == 2.80


@resp.activate
def test_fetch_odds_returns_dict_with_correct_values():
    resp.add(resp.GET, ESPN_ODDS_URL, json=SAMPLE_SCOREBOARD, status=200)
    result = fetch_odds(use_cache=False)
    assert isinstance(result, dict)
    assert len(result) == 1
    key = ("Croatia", "Ghana")
    assert key in result
    odds = result[key]
    assert odds.home == "Croatia"
    assert odds.away == "Ghana"
    # -110 American → 100/110 + 1 ≈ 1.909
    assert abs(odds.odds_home - (100 / 110 + 1)) < 0.01
    # +425 American → 4.25 + 1 = 5.25
    assert abs(odds.odds_away - (425 / 100 + 1)) < 0.01
    # +210 American → 2.10 + 1 = 3.10
    assert abs(odds.odds_draw - (210 / 100 + 1)) < 0.01


def test_fetch_odds_returns_empty_on_error():
    with mock.patch("requests.get", side_effect=requests.RequestException("timeout")):
        result = fetch_odds(use_cache=False)
    assert result == {}
