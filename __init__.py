"""Hermes entrypoint. Registration performs no network or storage operations."""

from .spoonmaster.plugin import CANDIDATES_SCHEMA, VERIFY_SCHEMA, candidates, verify_hours


def register(ctx):
    ctx.register_tool(
        name="spoon_candidates",
        toolset="spoonmaster",
        schema=CANDIDATES_SCHEMA,
        handler=candidates,
    )
    ctx.register_tool(
        name="spoon_verify_hours",
        toolset="spoonmaster",
        schema=VERIFY_SCHEMA,
        handler=verify_hours,
    )
