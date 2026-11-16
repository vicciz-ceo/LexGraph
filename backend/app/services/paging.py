"""Bounds shared by every paged endpoint and the agent interfaces.

An `offset` reaches SQLite as a bound integer. A value beyond SQLite's 64-bit
range made the driver raise OverflowError, which surfaced as HTTP 500 on
every paged route (finding XREQ-28: `?offset=99999999999999999999`). Capping
it at the 32-bit range keeps each route's 422 for bad paging; a real walk
through a matter never comes near it, and an offset past the last row is
still an empty page.
"""

from __future__ import annotations

#: Largest `offset` a paged endpoint, the agent CLI or MCP accepts.
MAX_OFFSET = 2**31 - 1
