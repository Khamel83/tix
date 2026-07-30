import httpx

import pytest

from ticket_sniper.argus import client as argus_client_module
from ticket_sniper.argus.client import ArgusClient
from ticket_sniper.argus.models import FetchRawRequest


@pytest.mark.asyncio
async def test_fetch_raw_sends_api_key_and_preserves_structured_argus_failure(monkeypatch):
    captured = {}

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, *, json, headers):
            captured.update(url=url, json=json, headers=headers)
            return httpx.Response(
                503,
                json={"status": "error", "http_status": 429},
            )

    monkeypatch.setattr(argus_client_module.httpx, "AsyncClient", FakeAsyncClient)
    client = ArgusClient()
    client.headers = {"X-API-Key": "tix-scoped-token"}

    response = await client.fetch_raw(
        FetchRawRequest(url="https://seatgeek.com/example-event", timeout_seconds=20)
    )

    assert captured["url"] == "http://argus.test/api/fetch-raw"
    assert captured["headers"] == {"X-API-Key": "tix-scoped-token"}
    assert response.status == "error"
    assert response.http_status == 429
