"""Hermes entrypoint. Registration performs no network or storage operations."""

import json

from .spoonmaster.companions import COMPANIONS_SCHEMA, CompanionService
from .spoonmaster.locales import SOURCE_SCHEMA, LocaleService
from .spoonmaster.onboarding import ONBOARD_SCHEMA, Onboarding
from .spoonmaster.outing import dining_context
from .spoonmaster.research_flow import PRESENT, RESEARCH, START, ResearchFlow
from .spoonmaster.taste_service import FEEDBACK_SCHEMA, TasteService, owner_key


def register(ctx):
    # Different registration/profile scopes never share private search context,
    # even when the host supplies identical conversation IDs in those scopes.
    taste = TasteService(lambda: getattr(getattr(ctx, "state", None), "data_dir", None))
    onboarding = Onboarding(
        taste, getattr(ctx, "ask_choice", None), dispatch=getattr(ctx, "dispatch_tool", None)
    )
    locales = LocaleService(
        taste, getattr(ctx, "ask_choice", None), getattr(ctx, "has_plugin", None)
    )
    dining = ResearchFlow(getattr(ctx, "dispatch_tool", None), taste, locales=locales)
    taste.invalidate_context = dining.invalidate_tastes
    companions = CompanionService(taste, dining)
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

    def current_ledger(args, **kwargs):
        return json.dumps({"text": explain("", **kwargs), "basis": "source-led comparison"})

    def profile(args, **kwargs):
        if isinstance(args, dict) and args.get("action") in ("sources_get", "sources_propose"):
            return locales.tool(
                {**args, "action": args["action"].removeprefix("sources_")}, **kwargs
            )
        return taste.profile_tool(args, **kwargs)

    ledger_schema = {
        "name": "spoon_ledger",
        "description": "Read the actual current dining comparison.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    }
    for schema, handler in (
        (ledger_schema, current_ledger),
        (ONBOARD_SCHEMA, onboarding.tool),
        (SOURCE_SCHEMA, profile),
        (FEEDBACK_SCHEMA, taste.feedback_tool),
        (COMPANIONS_SCHEMA, companions.tool),
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
        return dining.why(raw_args, **kwargs) or (
            "No current dining comparison. Tell me where you want to eat and what sounds good."
        )

    ctx.register_command(
        "why",
        handler=explain,
        description="Show dining exclusions and unresolved checks",
        args_hint="[page]",
    )

    def clear_context(session_id=None, **kwargs):
        dining.forget(session_id)
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
    ctx.register_hook("pre_tool_call", dining.before_browser)
    ctx.register_hook("post_tool_call", dining.after_browser)
    ctx.register_hook("transform_llm_output", dining.finish_output)
