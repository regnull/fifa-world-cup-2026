import requests
from scrape.cache import cache_get, cache_set

_URL = "https://www.eloratings.net/World.tsv"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
    "Accept": "text/tab-separated-values,text/plain",
}

# 2-letter eloratings.net country codes → canonical team names
_CODE_TO_NAME: dict[str, str] = {
    "ES": "Spain", "AR": "Argentina", "FR": "France", "EN": "England",
    "BR": "Brazil", "CO": "Colombia", "PT": "Portugal", "NL": "Netherlands",
    "NO": "Norway", "DE": "Germany", "BE": "Belgium", "IT": "Italy",
    "UR": "Uruguay", "MX": "Mexico", "US": "United States", "CR": "Croatia",
    "MA": "Morocco", "JP": "Japan", "SE": "Sweden", "TR": "Turkey",
    "AU": "Australia", "SN": "Senegal", "EG": "Egypt", "GH": "Ghana",
    "NG": "Nigeria", "CM": "Cameroon", "DK": "Denmark", "CH": "Switzerland",
    "AT": "Austria", "CL": "Chile", "PE": "Peru", "EC": "Ecuador",
    "PY": "Paraguay", "VE": "Venezuela", "IR": "IR Iran", "SA": "Saudi Arabia",
    "KR": "Korea Republic", "CA": "Canada", "QA": "Qatar", "TN": "Tunisia",
    "ML": "Mali", "DZ": "Algeria", "CI": "Côte d'Ivoire",
    "GR": "Greece", "CZ": "Czech Republic", "HU": "Hungary", "PL": "Poland",
    "RO": "Romania", "RS": "Serbia", "SK": "Slovakia", "SI": "Slovenia",
    "UA": "Ukraine", "IS": "Iceland", "IE": "Ireland", "FI": "Finland",
    "WA": "Wales", "SC": "Scotland", "NI": "Northern Ireland",
    "NZ": "New Zealand", "ZA": "South Africa", "BA": "Bosnia-Herzegovina",
    "CD": "DR Congo", "TT": "Trinidad and Tobago", "PA": "Panama",
    "ID": "Indonesia", "IQ": "Iraq", "JO": "Jordan", "CV": "Cabo Verde",
    "HT": "Haiti", "CW": "Curaçao", "UZ": "Uzbekistan",
    "CG": "Congo DR",
}


def fetch_elo(use_cache: bool = True) -> dict[str, float]:
    """Return dict of canonical team name → Elo rating from TSV data."""
    try:
        raw = cache_get("elo_world") if use_cache else None
        if raw is None:
            r = requests.get(_URL, headers=_HEADERS, timeout=15)
            r.raise_for_status()
            raw = r.text
            if use_cache:
                cache_set("elo_world", raw)
        return _parse(raw)
    except Exception:
        return {}


def _parse(tsv: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for line in tsv.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        code = parts[2].strip()
        try:
            rating = float(parts[3].strip())
        except ValueError:
            continue
        name = _CODE_TO_NAME.get(code)
        if name:
            result[name] = rating
    return result
