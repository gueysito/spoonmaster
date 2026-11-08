"""Hermes entrypoint. Registration performs no network or storage operations."""

from .spoonmaster.plugin import CANDIDATES_SCHEMA, candidates


def register(ctx):
    ctx.register_tool(
        name="spoon_candidates",
        toolset="spoonmaster",
        schema=CANDIDATES_SCHEMA,
        handler=candidates,
    )
