import time
from collections import defaultdict, deque
from typing import override

from fastapi import Request, Response
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_429_TOO_MANY_REQUESTS
from starlette.middleware.base import BaseHTTPMiddleware


# starlette is installed when fastapi is installed.
# BaseHTTPMiddleware is the class we inherit from to create custom middleware in FastAPI/Starlette.



RATE_LIMIT_REQUESTS = 50
RATE_LIMIT_WINDOW_SECONDS = 3600

# Stores recent request timestamps for each client IP address.
# defaultdict(deque) means a new IP automatically starts with an empty queue.
requests_by_ip: dict[str, deque[float]] = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    @override
    async def dispatch(self, request: Request, call_next):
        # If Starlette cannot identify the client, we stop early instead of putting
        # every unknown client into the same "unknown" rate-limit bucket.
        if request.client is None:
            return Response (content="Client IP address could not be identified",
            status_code = HTTP_400_BAD_REQUEST)

        # At this point request.client exists, so it is safe to read the client IP
        client_ip = request.client.host

        current_time = time.time()
        oldest_allowed_time = current_time - RATE_LIMIT_WINDOW_SECONDS

        request_times = requests_by_ip[client_ip]

        # Remove timestamps that are older than the current rate-limit window.
        # Only recent requests should count toward the client's limit.
        while request_times and request_times[0] < oldest_allowed_time:
            request_times.popleft()
        # If the client has already used all allowed requests in the current window,
        # return 429 instead of passing the request through to the normal route.
        if len(request_times) >= RATE_LIMIT_REQUESTS:
            return Response(
                content="Rate Limit exceeded",
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )
        # Record this request because it is within the allowed limit.
        request_times.append(current_time)

        return await call_next(request)
