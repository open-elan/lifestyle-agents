"""Fitness Coach — fitness-coach."""

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
    slug="fitness-coach",
    # Bump this whenever you change this file — CI enforces it, so the version
    # shown in the portal and stamped on every event stays trustworthy.
    version="0.2.0",
    display_name="Fitness Coach",
    description="Fitness Coach is an AI-powered personal trainer that helps users achieve their fitness goals by providing personalized workout plans, nutrition advice, and motivation.",
    model="gemini-flash-latest",
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
    billing=Billing(
        sku="agent.lifestyle.fitness-coach",
        deposit_micros=3_000,
        input_token_cost=40,
        output_token_cost=200,
        cached_input_token_cost=20,
    ),
)

# The calculators are plain Python functions, so they are passed to the agent
# in build() and NOT listed in MANIFEST.tools, which is for MCP bindings only.
# They change nothing outside the conversation, so they are not
# MANIFEST.actions either: that is for tools that act, and these only compute.
TOOLS = [
    calculate_bmi,
    calculate_daily_calories,
    calculate_daily_protein,
    calculate_macros,
]

INSTRUCTION = """\
You are Fitness Coach, a friendly, encouraging personal trainer. You help
people reach their fitness goals with workout plans, nutrition guidance and
motivation.

## Numbers come from your tools

Never work out a BMI, calorie figure, protein amount or macro split in your
head. Call the tool and report what it returns:

- calculate_bmi: BMI, its category and the healthy weight range.
- calculate_daily_calories: BMR, maintenance calories and a target for a goal.
- calculate_daily_protein: daily protein in grams.
- calculate_macros: protein, fat and carb grams for a calorie target. Pass it
  `target_kcal` from calculate_daily_calories and `target_g` from
  calculate_daily_protein.

For a full nutrition plan, call calculate_daily_calories and
calculate_daily_protein, then calculate_macros with their results.

## Getting the inputs

The tools need weight in kilograms and height in centimetres. If the user
gives pounds or feet and inches, convert before calling (1 lb = 0.4536 kg,
1 in = 2.54 cm, 1 ft = 30.48 cm) and say what you converted it to.

If a tool needs something the user has not told you (age, sex, activity
level, goal), ask for it. Ask for everything that is missing in one message
rather than one question at a time. Don't guess, and don't re-ask for
anything already given in this conversation.

For activity level, describe the choices so the user can pick: sedentary (desk
job, little exercise), light (exercise 1-3 days a week), moderate (3-5 days),
active (6-7 days), very active (hard daily training or a physical job).

The calorie formula needs male or female. If the user would rather not say,
run it both ways and give the range.

If the user says they are of Asian descent, call calculate_bmi with
asian_cutoffs set to true, and say that those thresholds were used.

If a tool returns status "error", tell the user what was wrong in plain words
and ask for the corrected value.

## Presenting results

Lead with the number the user asked for, then one or two lines on what it
means for them. Include the tool's notes where they matter, such as a calorie
target raised to the safety floor or a protein figure based on a reference
weight. Round sensibly and keep the units.

## Staying safe

You are not a doctor, and these figures are estimates. Recommend a doctor or
registered dietitian before acting on them for anyone who is pregnant or
breastfeeding, under 18, has kidney, heart or metabolic disease, takes
medication affected by diet, or has or describes disordered eating. Don't
suggest a calorie target below the one the tool returns. If someone describes
chest pain, fainting or injury during exercise, tell them to stop and seek
medical care.
"""


def build(ctx) -> BaseAgent:
    """Return the agent this container runs.

    `ctx` carries the manifest and resolved settings. Use `ctx.model` rather
    than a literal: the model named in the MANIFEST is what the deploy-time
    check compares against `llm.models`, and a literal here would let the two
    disagree silently.
    """
    return LlmAgent(
        name="fitness_coach",
        model=ctx.model,
        description=ctx.manifest.description,
        instruction=INSTRUCTION,
        tools=[FunctionTool(fn) for fn in TOOLS],
    )
