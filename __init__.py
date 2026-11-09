"""Hermes entrypoint. Registration performs no network or storage operations."""

from functools import partial

from .spoonmaster.ledger import LedgerStore
from .spoonmaster.plugin import (
    CANDIDATES_SCHEMA,
    EVALUATE_SCHEMA,
    LEDGER_SCHEMA,
    RECOMMEND_SCHEMA,
    SELECT_SCHEMA,
    VERIFY_SCHEMA,
    candidates,
    evaluate_candidates,
    forget_session,
    ledger,
    recommend_candidates,
    select_venue,
    verify_hours,
    why,
)
from .spoonmaster.taste_service import FEEDBACK_SCHEMA, PROFILE_SCHEMA, TasteService


def register(ctx):
    # Different registration/profile scopes never share private search context,
    # even when the host supplies identical conversation IDs in those scopes.
    store = LedgerStore()
    taste = TasteService(lambda: getattr(getattr(ctx, "state", None), "data_dir", None), store)
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
        handler=partial(ledger, _ledger_store=store, _taste_service=taste),
    )
    for schema, handler in (
        (RECOMMEND_SCHEMA, recommend_candidates),
        (SELECT_SCHEMA, select_venue),
    ):
        ctx.register_tool(
            name=schema["name"],
            toolset="spoonmaster",
            schema=schema,
            handler=partial(handler, _ledger_store=store, _taste_service=taste),
        )
    for schema, handler in (
        (PROFILE_SCHEMA, taste.profile_tool),
        (FEEDBACK_SCHEMA, taste.feedback_tool),
    ):
        ctx.register_tool(
            name=schema["name"], toolset="spoonmaster", schema=schema, handler=handler
        )
    ctx.register_command(
        "spoon",
        handler=taste.command,
        description="Optional taste memory and private profile controls",
        args_hint="profile|enable|help",
    )
    ctx.register_command(
        "why",
        handler=partial(why, _ledger_store=store, _taste_service=taste),
        description="Show dining exclusions and unresolved checks",
        args_hint="[page]",
    )

    def clear_context(session_id=None, **kwargs):
        forget_session(session_id, _ledger_store=store)
        taste.forget(session_id)

    ctx.register_hook("on_session_reset", clear_context)
    ctx.register_hook("on_session_finalize", clear_context)
    ctx.register_hook("pre_llm_call", taste.before_turn)
