"""Hermes entrypoint. Registration performs no network or storage operations."""

from functools import partial

from .spoonmaster.ledger import LedgerStore
from .spoonmaster.plugin import (
    CANDIDATES_SCHEMA,
    EVALUATE_SCHEMA,
    LEDGER_SCHEMA,
    VERIFY_SCHEMA,
    candidates,
    evaluate_candidates,
    forget_session,
    ledger,
    verify_hours,
    why,
)


def register(ctx):
    # Different registration/profile scopes never share private search context,
    # even when the host supplies identical conversation IDs in those scopes.
    store = LedgerStore()
    ctx.register_tool(
        name="spoon_candidates",
        toolset="spoonmaster",
        schema=CANDIDATES_SCHEMA,
        handler=partial(candidates, _ledger_store=store),
    )
    ctx.register_tool(
        name="spoon_verify_hours",
        toolset="spoonmaster",
        schema=VERIFY_SCHEMA,
        handler=verify_hours,
    )
    ctx.register_tool(
        name="spoon_evaluate",
        toolset="spoonmaster",
        schema=EVALUATE_SCHEMA,
        handler=partial(evaluate_candidates, _ledger_store=store),
    )
    ctx.register_tool(
        name="spoon_ledger",
        toolset="spoonmaster",
        schema=LEDGER_SCHEMA,
        handler=partial(ledger, _ledger_store=store),
    )
    ctx.register_command(
        "why",
        handler=partial(why, _ledger_store=store),
        description="Show dining exclusions and unresolved checks",
        args_hint="[page]",
    )
    ctx.register_hook("on_session_reset", partial(forget_session, _ledger_store=store))
    ctx.register_hook("on_session_finalize", partial(forget_session, _ledger_store=store))
