"""Hermes entrypoint. Registration performs no network or storage operations."""

import json
from functools import partial

from .spoonmaster.companions import COMPANIONS_SCHEMA, CompanionService
from .spoonmaster.ledger import LedgerStore
from .spoonmaster.locales import LOCALE_SCHEMA, LocaleService
from .spoonmaster.onboarding import ONBOARD_SCHEMA, Onboarding
from .spoonmaster.outing import dining_context, location_clarification
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
from .spoonmaster.research_flow import PRESENT, RESEARCH, START, ResearchFlow
from .spoonmaster.reviews import ReviewSearch
from .spoonmaster.taste_service import FEEDBACK_SCHEMA, PROFILE_SCHEMA, TasteService, owner_key


def register(ctx):
    # Different registration/profile scopes never share private search context,
    # even when the host supplies identical conversation IDs in those scopes.
    store = LedgerStore()
    taste = TasteService(lambda: getattr(getattr(ctx, "state", None), "data_dir", None), store)
    onboarding = Onboarding(
        taste, getattr(ctx, "ask_choice", None), dispatch=getattr(ctx, "dispatch_tool", None)
    )
    companions = CompanionService(taste)
    locales = LocaleService(taste, getattr(ctx, "dispatch_tool", None))
    reviews = ReviewSearch(locales)

    dining = ResearchFlow(
        getattr(ctx, "dispatch_tool", None), taste, post=getattr(ctx, "post_message", None)
    )
    for research_schema, handler in (
        (START, dining.start),
        (RESEARCH, dining.research),
        (PRESENT, dining.present),
    ):
        ctx.register_tool(
            name=research_schema["name"],
            toolset="spoonmaster",
            schema=research_schema,
            handler=handler,
        )
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
        handler=partial(companions.wrap, partial(evaluate_candidates, _ledger_store=store)),
    )

    def current_ledger(args, **kwargs):
        explanation = dining.why(session_id=kwargs.get("session_id"))
        if explanation:
            return json.dumps({"text": explanation, "basis": "source-led comparison"})
        return ledger(args, _ledger_store=store, _taste_service=taste, **kwargs)

    ctx.register_tool(
        name="spoon_ledger",
        toolset="spoonmaster",
        schema=LEDGER_SCHEMA,
        handler=current_ledger,
    )
    for schema, handler in (
        (ONBOARD_SCHEMA, onboarding.tool),
        (RECOMMEND_SCHEMA, recommend_candidates),
        (SELECT_SCHEMA, select_venue),
    ):
        bound = partial(handler, _ledger_store=store, _taste_service=taste)
        if handler is recommend_candidates:
            bound = partial(bound, _review_service=reviews)
        bound = partial(companions.wrap, bound)
        if handler is select_venue:
            bound = partial(onboarding.selection_tool, bound)
        ctx.register_tool(
            name=schema["name"],
            toolset="spoonmaster",
            schema=schema,
            handler=bound,
        )
    for schema, handler in (
        (PROFILE_SCHEMA, taste.profile_tool),
        (FEEDBACK_SCHEMA, taste.feedback_tool),
        (COMPANIONS_SCHEMA, companions.tool),
        (LOCALE_SCHEMA, locales.tool),
    ):
        ctx.register_tool(
            name=schema["name"], toolset="spoonmaster", schema=schema, handler=handler
        )

    def command(raw_args, **kwargs):
        if isinstance(raw_args, str) and raw_args.split()[:1] == ["locale"]:
            return locales.command(raw_args, **kwargs)
        if isinstance(raw_args, str) and raw_args.split()[:1] == ["companions"]:
            return companions.command(raw_args, **kwargs)
        result = onboarding.command(raw_args, **kwargs)
        if isinstance(raw_args, str) and raw_args.split() == ["delete", "confirm"]:
            if result == "Your saved taste profile and companions have been deleted.":
                dining.forget(kwargs.get("session_id"))
                owner = owner_key(kwargs.get("source"), kwargs.get("platform"))
                path = taste.state_directory() / "taste.sqlite3"
                with companions.lock:
                    companions._invalidate(owner, path)
                locales.invalidate(owner, path)
        return result

    ctx.register_command(
        "spoon",
        handler=command,
        description="Optional onboarding, immediate food search and private taste controls",
        args_hint="start|now|profile|help",
    )

    def explain(raw_args, **kwargs):
        return dining.why(raw_args, **kwargs) or why(
            raw_args, _ledger_store=store, _taste_service=taste, **kwargs
        )

    ctx.register_command(
        "why",
        handler=explain,
        description="Show dining exclusions and unresolved checks",
        args_hint="[page]",
    )

    def clear_context(session_id=None, **kwargs):
        dining.forget(session_id)
        forget_session(session_id, _ledger_store=store)
        taste.forget(session_id)
        onboarding.forget(session_id)
        companions.forget(session_id)
        locales.forget(session_id)

    def before_turn(**kwargs):
        dining.observe(**kwargs)
        # Establish CLI/private identity before the onboarding controller reads it.
        recalled = taste.before_turn(**kwargs)
        welcome = onboarding.before_turn(**kwargs)
        if welcome and welcome.get("action") == "block":
            return welcome
        location = location_clarification(kwargs.get("user_message"))
        if location:
            return location
        party = companions.before_turn(**kwargs)
        locale = locales.before_turn(**kwargs)
        contexts = [
            result["context"]
            for result in (welcome, recalled, party, locale, dining_context())
            if result
        ]
        return {"context": "\n".join(contexts)} if contexts else None

    ctx.register_hook("on_session_reset", clear_context)
    ctx.register_hook("on_session_finalize", clear_context)
    ctx.register_hook("pre_llm_call", before_turn)
