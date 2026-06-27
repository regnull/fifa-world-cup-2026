import responses as resp
from scrape.odds import fetch_odds, _parse_odds_row
from scrape.models import MatchOdds

SAMPLE_HTML = """
<html><body>
<table class="table-main">
<thead><tr><th>Match</th><th>1</th><th>X</th><th>2</th></tr></thead>
<tbody>
<tr>
  <td><a href="/football/world-cup/france-brazil/">France - Brazil</a></td>
  <td><span class="best-odds">2.50</span></td>
  <td><span class="best-odds">3.20</span></td>
  <td><span class="best-odds">2.80</span></td>
</tr>
</tbody>
</table>
</body></html>
"""

def test_parse_odds_row():
    home, away, oh, od, oa = _parse_odds_row("France - Brazil", "2.50", "3.20", "2.80")
    assert home == "France"
    assert away == "Brazil"
    assert oh == 2.50
    assert od == 3.20
    assert oa == 2.80

@resp.activate
def test_fetch_odds_returns_dict():
    resp.add(resp.GET, "https://www.betexplorer.com/football/world/fifa-world-cup/",
             body=SAMPLE_HTML, status=200)
    result = fetch_odds(use_cache=False)
    assert isinstance(result, dict)

def test_fetch_odds_returns_empty_on_error():
    # Simulate network failure — should return {} not raise
    import unittest.mock as mock
    import requests
    with mock.patch("requests.get", side_effect=requests.RequestException("timeout")):
        result = fetch_odds(use_cache=False)
    assert result == {}
