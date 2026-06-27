from scrape.names import normalize


def test_normalize_known_aliases():
    assert normalize("USA") == "United States"
    assert normalize("South Korea") == "Korea Republic"
    assert normalize("Iran") == "IR Iran"
    assert normalize("Brazil") == "Brazil"


def test_normalize_strips_whitespace():
    assert normalize("  Brazil  ") == "Brazil"


def test_normalize_case_insensitive():
    assert normalize("brazil") == "Brazil"
    assert normalize("FRANCE") == "France"
