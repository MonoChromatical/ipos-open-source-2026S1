import time
from collections import defaultdict, deque
from typing import override

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

"""
Request - represents the incoming HTTP request
Response - lets us manually send a response back
starlette is installed when fastapi is installed.
BaseHTTPMiddleware is the class we inherit from to create custom middleware in FastAPI/Starlette.
"""


RATE_LIMIT_REQUESTS = 50
RATE_LIMIT_WINDOW_SECONDS = 3600

"""
requests_by_ip is a dictionary /string -> [IP ADDRESS]and a double-ended queue /float -> [timestamps] of when the request was
made.
If an IP address has not been seen before, defaultdict automatically creates an empty deque for that IP.
etc, "127.0.0.2": deque([])
"""

requests_by_ip: dict[str, deque[float]] = defaultdict(deque)

"""
Create a rate limit middleware.

For every incoming request:

    Check if the request has client information.

    If client information exists:
        Get the client's IP address.

    Otherwise:
        Use "unknown" as the client identifier.

    Get the current time.

    Work out the oldest request time that should still count:
        oldest allowed time = current time - rate limit window

    Get the saved request times for this client IP.

    While this client has saved request times
    and the oldest saved request time is older than the allowed window:
        Remove that old request time.

    Check how many recent request times are left.

    If the number of recent requests is greater than or equal to the allowed limit:
        Stop the request.
        Return a "Too Many Requests" response.
        Tell the client how long to wait before trying again.

    Otherwise:
        Save the current request time.

        Continue the request to the normal FastAPI route.
"""


class RateLimitMiddleware(BaseHTTPMiddleware):
    @override
    async def dispatch(self, request: Request, call_next):
        if request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown"
        current_time = time.time()
        oldest_allowed_time = current_time - RATE_LIMIT_WINDOW_SECONDS

        request_times = requests_by_ip[client_ip]

        while request_times and request_times[0] < oldest_allowed_time:
            request_times.popleft()
        if len(request_times) >= RATE_LIMIT_REQUESTS:
            return Response(
                content="Rate Limit exceeded",
                status_code=429,
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )

        request_times.append(current_time)

        return await call_next(request)
