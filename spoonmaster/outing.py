"""Current-time defaults and explicit-location guidance."""

from datetime import datetime, timezone

LOCATION_PROMPT = (
    "Let's find you some food. Tell me where you are or plan to be: a city, area, "
    "address or landmark, "
    "or drop a location pin if your chat app supports it."
)


def dining_context(*, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "context": (
            "For dining use spoon_dine to start source-led research, spoon_research for "
            "batches of independent search/read/browser calls, then spoon_present for the answer "
            "and /why. Maps are optional supporting evidence, not candidate admission. "
            "When a user chooses a researched place, check fresh hours using a new source-led "
            "request focused on that place; keep its previous context and source references. "
            "Compare several genuinely relevant businesses using independent local sources "
            "and official menus/hours. Never turn missing map data into no restaurants. "
            "Narrate meaningful progress BETWEEN calls and explain delays. New user context "
            "replaces the active request via spoon_dine; cancel means stop. Host interruption "
            "delivery can vary, so never claim a cancellation until received. "
            "Return recommendations in normal final text, with every alternative and link. "
            "Accept typed or host-transcribed voice input identically. Clarify consequential "
            "transcription ambiguity, especially dietary needs; no microphone setup is needed "
            "for typed use. Never claim transcription is enabled without host evidence. "
            "Ask at most the most useful missing question, never a prerequisite questionnaire. "
            "Offer optional free-form personalization: favorite meals/places, usual companions "
            "and children, diet/allergies, budget, drinks/dessert and travel/wait tolerance. "
            "Reuse stated information. Current party is not necessarily the usual party. "
            "Use spoon_feedback for explicitly opted-in non-sensitive taste learning, with "
            "a plain-language saved-change receipt. Use spoon_companions only with its separate "
            "saving and sensitive-data consent. Dietary needs can remain outing-only. "
            "Use native clarify choices for either/or questions when available. Six optional "
            "taste choices are a starting point, not a complete personal profile. "
            f"Spoonmaster current clock (UTC): {now.astimezone(timezone.utc).isoformat()}. "
            "For dining, use the current time unless the user explicitly states another time. "
            "The plugin supplies current UTC when a request starts. Do not ask the user "
            "what time it is. Convert to the destination timezone, never the host timezone. "
            "Resolve an explicit local meal time against that destination and date; clarify "
            "only an ambiguous requested time. Current time is not a travel ETA. "
            "Use only an outing location stated by the user or a location pin they shared. "
            "Reuse an unambiguous location already supplied for this outing; a new city "
            "replaces the old origin. Do not infer location from IP, host, timezone, tastes "
            "or previous outings. If missing or ambiguous, ask: "
            + LOCATION_PROMPT
            + " An area/landmark is a search anchor, not a claim of exact user position. "
            "A city or neighborhood is sufficient for area research; do not demand a landmark "
            "or invent exact coordinates. Keep area to the plain place name, "
            "without explanations or disclaimers. "
            "Do not request a pin on a terminal; offer the typed alternatives. "
            "Do not ask for location for unrelated questions or personalization."
        )
    }
