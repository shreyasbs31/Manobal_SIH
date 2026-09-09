"""Cursor pagination for all collection endpoints (SDD §6.6).

Cursor rather than offset, for two reasons that both matter here.

Operationally, ``LIMIT 50 OFFSET 20000`` makes PostgreSQL walk and discard
twenty thousand rows; an officer paging through a long queue degrades steadily
until the request times out.

More importantly, offsets leak. A caller who can vary an offset and observe
where results shift can infer the size and composition of a result set they are
not permitted to enumerate — which is the same differencing attack that
k-anonymity suppression closes on the aggregate side. A cursor exposes no
position, so there is nothing to difference.
"""

from __future__ import annotations

from rest_framework.pagination import CursorPagination as DRFCursorPagination


class CursorPagination(DRFCursorPagination):
    """Opaque, stably ordered pagination.

    Ordering is by ``-id`` rather than a timestamp because two rows written in
    the same millisecond under a non-unique ordering can be returned twice or
    skipped entirely as a caller pages. A missed row in an officer's queue is a
    person nobody looked at.
    """

    page_size = 50
    max_page_size = 200
    page_size_query_param = "page_size"
    ordering = "-id"
    cursor_query_param = "cursor"
