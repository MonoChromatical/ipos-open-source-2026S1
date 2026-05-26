from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.status import HTTP_200_OK, HTTP_429_TOO_MANY_REQUESTS

from app.security import rate_limit
from app.security.rate_limit import RateLimitMiddleware


# Uses a small test FastAPI app so the middleware logic can be tested without starting the real server.
def test_rate_limit_blocks_after_limit(monkeypatch):
    rate_limit.requests_by_ip.clear()

    # monkeypatch changes these values only for this test, then pytest restores them afterward.
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_REQUESTS", 2)
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_WINDOW_SECONDS", 60)

    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware)

    # Just creates a fake route similar to /health just for the testing case without needing the server to actually provide responses.
    # it sends a GET request to /test, so then it can return a successful JSON response.
    @test_app.get("/test")
    def test_route():
        return {"status": "ok"}

    client = TestClient(test_app)

    response_1 = client.get("/test")
    response_2 = client.get("/test")
    response_3 = client.get("/test")

    assert response_1.status_code == HTTP_200_OK
    assert response_2.status_code == HTTP_200_OK
    assert response_3.status_code == HTTP_429_TOO_MANY_REQUESTS
