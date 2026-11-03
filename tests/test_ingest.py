import asyncio

import pytest

from scripts.ingest import fetch_movies
from scripts.ingest.fetch_movies import get_json, ids_from_pages, read_checkpoint, read_jsonl


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status = status
        self.payload = payload
        self.headers = {}

    async def json(self):
        return self.payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    """Renvoie les réponses prévues, une par appel."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, url, params=None):
        self.calls += 1
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def instant(_):
        pass
    monkeypatch.setattr(fetch_movies.asyncio, "sleep", instant)


def call(session, tries=5):
    return asyncio.run(get_json(session, asyncio.Semaphore(1), "/movie/1", {}, tries=tries))


def test_get_json_retries_then_succeeds():
    session = FakeSession([FakeResponse(429), FakeResponse(503), FakeResponse(200, {"id": 1})])
    assert call(session) == {"id": 1}
    assert session.calls == 3


def test_get_json_returns_none_on_404():
    assert call(FakeSession([FakeResponse(404)])) is None


def test_get_json_does_not_retry_on_401():
    session = FakeSession([FakeResponse(401)])
    with pytest.raises(RuntimeError, match="HTTP 401"):
        call(session)
    assert session.calls == 1


def test_get_json_gives_up_after_max_tries():
    session = FakeSession([FakeResponse(500)] * 3)
    with pytest.raises(RuntimeError, match="3 essais"):
        call(session, tries=3)


def test_ids_from_pages_keeps_page_order_and_removes_duplicates():
    pages = [
        {"page": 2, "results": [{"id": 3}, {"id": 1}]},
        {"page": 1, "results": [{"id": 1}, {"id": 2}]},
    ]
    assert ids_from_pages(pages) == [1, 2, 3]


def test_read_checkpoint(tmp_path):
    path = tmp_path / "movies_2010.txt"
    assert read_checkpoint(path) == set()
    path.write_text("27205\n10138\n\n")
    assert read_checkpoint(path) == {27205, 10138}


def test_read_jsonl_skips_truncated_last_line(tmp_path):
    path = tmp_path / "year=2010.jsonl"
    path.write_text('{"id": 1}\n{"id": 2}\n{"id": 3, "tit', encoding="utf-8")
    assert read_jsonl(path) == [{"id": 1}, {"id": 2}]
