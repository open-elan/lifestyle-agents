"""Crisis and support lines, looked up rather than remembered.

A model recalling a helpline number from training data is the one place in
this agent where a confident mistake can cost a life: lines get renumbered
(Canada moved to 988 in November 2023), new ones open (Singapore's mindline
1771 in 2025), and a wrong digit fails silently at the worst moment. So the
numbers live here, as data someone checked, and the agent reports them.

ONLY VERIFIED ENTRIES BELONG HERE. A country with no entry gets the
international directory and the local emergency number, which is better than a
number that might be wrong. Recheck every entry when `VERIFIED_ON` gets old.

Pure lookup: it changes nothing outside the conversation, so it is not a
`MANIFEST.actions` entry.
"""

VERIFIED_ON = "2026-11"

_DIRECTORY = {
    "name": "Find A Helpline",
    "contact": "https://findahelpline.com",
    "hours": "Lists free, confidential helplines for every country, searchable by topic.",
}

# ISO 3166 alpha-2 -> the country's emergency number and its verified lines.
_RESOURCES: dict[str, dict] = {
    "IN": {
        "country": "India",
        "emergency": "112",
        "lines": [
            {"name": "Tele-MANAS (national mental health helpline)",
             "contact": "Call 14416 or 1-800-891-4416",
             "hours": "24/7, free, in about 20 languages"},
        ],
    },
    "US": {
        "country": "United States",
        "emergency": "911",
        "lines": [
            {"name": "988 Suicide & Crisis Lifeline",
             "contact": "Call or text 988, or chat at 988lifeline.org",
             "hours": "24/7, free; Spanish available; veterans press 1"},
        ],
    },
    "CA": {
        "country": "Canada",
        "emergency": "911",
        "lines": [
            {"name": "9-8-8 Suicide Crisis Helpline",
             "contact": "Call or text 988",
             "hours": "24/7, free"},
        ],
    },
    "GB": {
        "country": "United Kingdom",
        "emergency": "999",
        "lines": [
            {"name": "Samaritans", "contact": "Call 116 123", "hours": "24/7, free"},
            {"name": "Shout", "contact": "Text SHOUT to 85258", "hours": "24/7, free"},
        ],
    },
    "IE": {
        "country": "Ireland",
        "emergency": "112 or 999",
        "lines": [
            {"name": "Samaritans", "contact": "Call 116 123", "hours": "24/7, free"},
        ],
    },
    "AU": {
        "country": "Australia",
        "emergency": "000",
        "lines": [
            {"name": "Lifeline",
             "contact": "Call 13 11 14, or text 0477 13 11 14",
             "hours": "24/7 by phone"},
        ],
    },
    "NZ": {
        "country": "New Zealand",
        "emergency": "111",
        "lines": [
            {"name": "Need to Talk? 1737",
             "contact": "Call or text 1737",
             "hours": "24/7, free, trained counsellors"},
        ],
    },
    "SG": {
        "country": "Singapore",
        "emergency": "995",
        "lines": [
            {"name": "Samaritans of Singapore (SOS)",
             "contact": "Call 1767, or WhatsApp 9151 1767",
             "hours": "24/7"},
            {"name": "national mindline 1771",
             "contact": "Call 1771, WhatsApp 6669 1771, or webchat at mindline.sg",
             "hours": "24/7"},
        ],
    },
}

_ALIASES: dict[str, str] = {
    "india": "IN", "bharat": "IN",
    "united states": "US", "united states of america": "US", "usa": "US",
    "america": "US", "u.s.": "US", "u.s.a.": "US",
    "canada": "CA",
    "united kingdom": "GB", "uk": "GB", "u.k.": "GB", "great britain": "GB",
    "britain": "GB", "england": "GB", "scotland": "GB", "wales": "GB",
    "northern ireland": "GB",
    "ireland": "IE", "republic of ireland": "IE", "eire": "IE",
    "australia": "AU",
    "new zealand": "NZ", "aotearoa": "NZ",
    "singapore": "SG",
}


def _code_for(country: str) -> str | None:
    key = country.strip().lower()
    if key.upper() in _RESOURCES:
        return key.upper()
    return _ALIASES.get(key)


def get_crisis_resources(country: str) -> dict:
    """Look up crisis and mental health support lines for a country.

    Call this the moment someone may be at risk: any mention of suicide,
    wanting to die, self-harm, harming others, or being unsafe. Also call it
    when someone wants professional support and you know their country.
    Always give the user the numbers this returns, never numbers from memory.

    Args:
        country: The country the user is in, as a name ("India", "UK") or a
            two-letter code ("IN", "GB"). If you don't know it, ask; if they
            won't say, pass "unknown".

    Returns:
        A dict with `found`, the country's `emergency` number, its support
        `lines` (name, how to reach them, hours), and an international
        `directory` that covers every country.
    """
    code = _code_for(country or "")
    if code is None:
        return {
            "status": "success",
            "found": False,
            "country": country,
            "emergency": (
                "The local emergency number. 112 works in every EU country and "
                "connects from mobile phones in many others."
            ),
            "lines": [],
            "directory": _DIRECTORY,
            "note": (
                f"No verified lines are stored for {country!r}. Point the user to "
                "the directory, which lists free lines for every country."
            ),
        }

    entry = _RESOURCES[code]
    return {
        "status": "success",
        "found": True,
        "country": entry["country"],
        "emergency": entry["emergency"],
        "lines": entry["lines"],
        "directory": _DIRECTORY,
        "verified_on": VERIFIED_ON,
        "note": "You cannot contact these services for the user; they need to reach out themselves.",
    }
