"""Strawberry GraphQL schema for Nakama.

Exposes the top-level Query type with the following fields:

    search(query: String!, kind: ContentKind!, source: String): [SearchResult!]!
    detail(slug: String!, kind: ContentKind!, source: String!): JSON
    home(kind: ContentKind!, source: String): [HomeResult!]!
    sources: [SourceInfo!]!
"""

from __future__ import annotations

from typing import List, Optional

import strawberry

from .resolvers import resolve_detail, resolve_home, resolve_search, resolve_sources
from .types import ContentKind, HomeResult, SearchResult, SourceInfo


@strawberry.type
class Query:
    """Root query type for Nakama GraphQL API."""

    search: List[SearchResult] = strawberry.field(
        resolver=resolve_search,
        description="Search across anime/comic/novel sources. Optionally scoped to a single source.",
    )

    detail: Optional[strawberry.scalars.JSON] = strawberry.field(
        resolver=resolve_detail,
        description="Fetch detail for a single item from a specific source.",
    )

    home: List[HomeResult] = strawberry.field(
        resolver=resolve_home,
        description="Fetch home page listing for one or all sources of a given kind.",
    )

    sources: List[SourceInfo] = strawberry.field(
        resolver=resolve_sources,
        description="List all registered sources with their content kind.",
    )


schema = strawberry.Schema(query=Query)
