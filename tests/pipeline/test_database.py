from pipelines.utils.database import get_engine


def test_database_url_supports_special_characters(monkeypatch):
    monkeypatch.setenv("MYSQL_USER", "analyst")
    monkeypatch.setenv("MYSQL_PASSWORD", "strong:p@ss/word#1")
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_DATABASE", "economic_intelligence")

    engine = get_engine()

    assert engine.url.username == "analyst"
    assert engine.url.password == "strong:p@ss/word#1"
    assert engine.url.port == 3306
