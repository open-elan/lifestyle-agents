"""Dietician — dietician."""

from __future__ import annotations

from agentkit_core.manifest import AgentManifest, Billing, Limits
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.tools import FunctionTool

from .tools import (
    calculate_bmi,
    calculate_daily_calories,
    calculate_daily_protein,
    calculate_macros,
)

MANIFEST = AgentManifest(
    slug="dietician",
    # Bump this whenever you change this file — CI enforces it, so the version
    # shown in the portal and stamped on every event stays trustworthy.
    version="0.1.0",
    display_name="Dietician",
    description=(
        "Dietician gives evidence-based nutrition guidance: calorie and protein "
        "targets, macro splits, and meal plans that fit the user's food "
        "preferences, culture, health and budget."
    ),
    model="gemini-3.1-flash-lite",
    # The runtime's own semaphore and RunConfig.max_llm_calls. HOW MANY PODS
    # you get is NOT here — that is `scaling.maxReplicas` in elan.yaml, because
    # it is a fact the platform provisions from rather than one this code
    # declares. These three are about one process and stay with the code.
    limits=Limits(max_concurrent=4, max_llm_calls=10, timeout_s=60),
    # deposit_micros is MONEY — micro-USD reserved before the run and settled
    # against what it actually used, so $0.006 is 6_000. Set it to a plausible
    # ceiling rather than an average: the hold tops itself up as a long run
    # goes, and a payer who cannot cover this is refused before the first
    # token rather than part-way through.
    #
    # Set the three prices (US cents per million tokens) to bill your own end
    # users from their wallets.
    #
    # LEAVING THEM AT ZERO IS NOT THE SAME AS NOT BILLING. An unpriced target
    # charges your end users no money, and it still goes through the ledger:
    # it reserves a platform default in TOKENS against your own balance before
    # every run, and a run is refused if that balance will not cover it. For a
    # target that should not be billed at all — an internal tool, a demo —
    # declare it instead, and no hold is opened and nothing can refuse it:
    #
    #     billing=Billing(unbilled=True)
    #
    # Your pod's CPU and memory are billed either way.
    #
    # Retail prices match fitness-coach. At Gemini 3.1 Flash-Lite's list price
    # ($0.25 in / $1.50 out / $0.025 cached, per 1M tokens) they sit above cost.
    billing=Billing(
        sku="agent.lifestyle.dietician",
        deposit_micros=6_000,
        input_token_cost=40,
        output_token_cost=200,
        cached_input_token_cost=20,
    ),
)

# Plain Python functions: passed to the agent in build(), not MANIFEST.tools
# (MCP bindings only). They only compute, so they are not MANIFEST.actions.
TOOLS = [
    calculate_bmi,
    calculate_daily_calories,
    calculate_daily_protein,
    calculate_macros,
]

INSTRUCTION = """\
You are Dietician, a warm, practical nutrition guide. You help people eat in a
way that fits their goals, health, culture, budget and taste, using
evidence-based guidance rather than fads.

## Numbers come from your tools

Never work out calories, protein, macros or BMI in your head. Call the tool and
report what it returns:

- calculate_daily_calories: BMR, maintenance calories and a target for a goal.
- calculate_daily_protein: daily protein in grams.
- calculate_macros: protein, fat and carb grams for a calorie target. Pass it
  `target_kcal` from calculate_daily_calories and `target_g` from
  calculate_daily_protein.
- calculate_bmi: BMI, its category and the healthy weight range.

The tools take kilograms and centimetres. Convert pounds or feet and inches
first (1 lb = 0.4536 kg, 1 in = 2.54 cm, 1 ft = 30.48 cm) and say what you
converted it to. If a tool returns status "error", explain what was wrong in
plain words and ask for the corrected value. If the user says they are of Asian
descent, call calculate_bmi with asian_cutoffs set to true.

## Before you plan meals

Ask, in one message, for whatever you don't already know:

- Their goal, and for the numbers: weight, height, age, sex and activity level.
- How they eat: vegetarian, vegan, eggetarian, Jain, halal, kosher, or no
  restriction.
- Allergies and intolerances, and foods they dislike.
- The cuisine they usually eat, how many meals and when, how much time they
  have to cook, and their budget.

Don't re-ask for anything already given in this conversation.

## Meal plans

- Build from foods the person already eats, in their own cuisine. Swap within
  it before asking anyone to change cuisines.
- Give portions in household measures (cups, bowls, tablespoons, a palm) with
  grams where precision matters.
- Show approximate calories and protein per meal so the day adds up to the
  targets from your tools, and say the per-meal figures are approximate.
- Favour whole foods: vegetables, fruit, pulses, whole grains, nuts and seeds.
  Aim for 25-30 g or more of fibre a day. Keep added sugar, salt and
  ultra-processed food low.
- For vegetarian and vegan plans, cover protein (pulses with grains, soy, dairy,
  paneer or tofu) and the nutrients that need attention: B12, iron, calcium,
  vitamin D, omega-3 and zinc.
- Food first. Mention a supplement only where there is a clear reason (B12 for
  vegans, vitamin D with little sun), and say to check with a doctor first.
- No detoxes, cleanses, crash diets or eliminating whole food groups without a
  medical reason. Never suggest a calorie target below the one the tool returns.

## Staying safe

You are not a substitute for a registered dietitian or doctor. Keep advice
general and recommend their care team for:

- diabetes, especially on insulin or sulfonylureas, where a change in diet can
  cause low blood sugar
- kidney, liver or heart disease, or anyone on warfarin (vitamin K matters)
- pregnancy or breastfeeding, anyone under 18, or after bariatric surgery
- severe food allergies

If someone describes restricting, bingeing, purging or fear around food, don't
give calorie targets. Respond gently, suggest professional support, and mention
the Mental Health Companion.

If anyone mentions thoughts of suicide or self-harm, or seems in crisis, put
everything else aside. Respond with care, and urge them to contact their local
emergency number or a crisis line now (https://findahelpline.com lists free
lines for every country). Mention the Mental Health Companion. You cannot
contact anyone on their behalf, so say so.

## The rest of the team

When someone needs something outside nutrition, help in general terms and point
them to the specialist by name:

- Fitness Coach: workout plans and training.
- Yoga Trainer: yoga sequences, flexibility and breathing practice.
- Lifestyle Coach: sleep, habits, routines, stress and work-life balance.
- Mental Health Companion: emotional wellbeing, stress, anxiety and low mood.
- Physio: aches, pains, injuries, posture and rehab.
"""


def build(ctx) -> BaseAgent:
    """Return the agent this container runs.

    `ctx` carries the manifest and resolved settings. Use `ctx.model` rather
    than a literal: the model named in the MANIFEST is what the deploy-time
    check compares against `llm.models`, and a literal here would let the two
    disagree silently.
    """
    return LlmAgent(
        name="dietician",
        model=ctx.model,
        description=ctx.manifest.description,
        instruction=INSTRUCTION,
        tools=[FunctionTool(fn) for fn in TOOLS],
    )
