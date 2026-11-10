"""Human-facing taste summary; storage and export retain their complete schema."""

from .cards import plain


def render_profile(profile):
    if profile is None:
        return (
            "Your food profile\n\nYou haven't saved any tastes yet.\n"
            "Use /spoon personalize for a few quick choices, or /spoon now to find food."
        )
    lines = ["Your food profile", ""]
    if not profile["enabled"]:
        lines += ["Taste memory is paused. Your saved tastes aren't being used.", ""]
    groups = {}
    for pref in profile["prefs"]:
        heading = {
            "dish": "Food",
            "cuisine": "Food",
            "attribute": "Flavors and textures",
            "vibe": "Atmosphere",
            "venue": "Places",
        }[pref["kind"]]
        if pref["item"] in ("familiar favorites", "trying something new"):
            heading = "How you like to explore"
        tone = {1: "Like", -1: "Prefer to avoid", 0: "Neutral about"}[pref["polarity"]]
        qualifier = " (still learning)" if pref["scope"] == "tentative" else ""
        if pref["context"]:
            context = ", ".join(f"{plain(k)}: {plain(v)}" for k, v in pref["context"].items())
            qualifier += f" ({context})"
        groups.setdefault(heading, []).append(f"- {tone}: {plain(pref['item'])}{qualifier}")
    for heading, items in groups.items():
        lines += [heading, *items, ""]
    if not groups:
        lines += ["No tastes saved yet. Use /spoon personalize to get started.", ""]
    if any(p["scope"] == "tentative" for p in profile["prefs"]):
        lines += [
            "These are starting preferences, not firm rules. Choosing one option doesn't "
            "mean you dislike the other.",
            "",
        ]
    lines += [
        'To adjust your tastes, tell me something like "I prefer quiet places now."',
        "Controls: /spoon enable to resume, /spoon pause to pause, /spoon export for full data.",
        "Use /spoon help for correction and deletion commands.",
    ]
    return "\n".join(lines)
