from pipelines.utils.api_client import DEFAULT_TIMEOUT, USER_AGENT, get_json


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, bool]:
        return {"ok": True}


class FakeSession:
    def __init__(self) -> None:
        self.request: tuple[object, ...] | None = None

    def get(self, url, params, timeout):
        self.request = (url, params, timeout)
        return FakeResponse()


def test_get_json_uses_timeout_and_parameters():
    session = FakeSession()

    result = get_json("https://example.test/data", {"page": 1}, session=session)

    assert result == {"ok": True}
    assert session.request == (
        "https://example.test/data",
        {"page": 1},
        DEFAULT_TIMEOUT,
    )


def test_retry_session_has_user_agent_and_retry_policy():
    from pipelines.utils.api_client import create_retry_session

    session = create_retry_session()
    try:
        retry = session.get_adapter("https://").max_retries
        assert session.headers["User-Agent"] == USER_AGENT
        assert retry.total == 3
        assert 429 in retry.status_forcelist
        assert retry.allowed_methods == frozenset({"GET"})
    finally:
        session.close()
