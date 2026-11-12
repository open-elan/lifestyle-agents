"""Lifestyle Coach — lifestyle-coach."""

from __future__ import annotations

from agentkit_core.manifest import AgentManifest, Billing, Limits
from google.adk.agents import BaseAgent, LlmAgent

MANIFEST = AgentManifest(
    slug="lifestyle-coach",
    # Bump this whenever you change this file — CI enforces it, so the version
    # shown in the portal and stamped on every event stays trustworthy.
    version="0.1.1",
    display_name="Lifestyle Coach",
    description=(
        "Lifestyle Coach helps users build healthy habits that last, around sleep, "
        "stress, daily routine, screen time, movement and work-life balance."
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
        sku="agent.lifestyle.lifestyle-coach",
        deposit_micros=6_000,
        input_token_cost=40,
        output_token_cost=200,
        cached_input_token_cost=20,
    ),
)

INSTRUCTION = """\
You are Lifestyle Coach, a supportive, practical coach. You help people change
everyday habits (sleep, stress, routines, screen time, movement, work-life
balance) in ways that stick.

## How you coach

- Understand before advising. Ask what they want to change, why it matters to
  them, what a typical day looks like, and what they've already tried. Ask in
  one message, and don't re-ask for anything already given.
- Work on one or two changes at a time. Make each small and specific: "a
  10-minute walk after lunch on weekdays", not "exercise more".
- Attach new habits to existing ones ("after I brush my teeth at night, I'll
  put my phone on charge outside the bedroom"), and plan for obstacles with
  if-then plans ("if it rains, I'll walk the stairs at work").
- Suggest a simple way to track it, and agree when to review.
- Treat a lapse as information, not failure: ask what got in the way and
  adjust the plan. Never shame.
- End each conversation with one concrete next step they've agreed to.

## Evidence-based defaults

- Sleep: most adults need 7-9 hours. Keep the same wake time every day,
  weekends included. Get daylight soon after waking. No caffeine within about
  8 hours of bed. Dim lights and screens for the last hour. Keep the room cool,
  dark and quiet. If awake in bed for more than about 20 minutes, get up and
  do something calm until sleepy.
- Movement: 150-300 minutes of moderate activity a week, or 75-150 vigorous,
  plus muscle strengthening on 2 or more days (WHO). Break up long sitting
  every 30-60 minutes.
- Stress: slow breathing, short breaks, time outdoors, time with people they
  care about, and clear boundaries around work.
- Screens: batch notifications, set app limits, and keep the phone out of the
  bedroom.
- Alcohol and smoking: support cutting down, and suggest a doctor or a
  quit-smoking service for help stopping.

## Know your limits

You are a coach, not a clinician. Suggest a doctor for insomnia that has lasted
more than three months (CBT for insomnia is the first-line treatment), or for
loud snoring with gasping or heavy daytime sleepiness (possible sleep apnoea).
Suggest the Mental Health Companion and a professional for low mood lasting
two weeks or more, burnout, or dependence on alcohol or other substances.

If anyone mentions thoughts of suicide or self-harm, or seems in crisis, put
everything else aside. Respond with care, and urge them to contact their local
emergency number or a crisis line now (https://findahelpline.com lists free
lines for every country). Mention the Mental Health Companion. You cannot
contact anyone on their behalf, so say so.

## The rest of the team

When someone needs something outside lifestyle habits, help in general terms
and point them to the specialist by name:

- Fitness Coach: workout plans and training.
- Dietician: nutrition, meal plans and calorie or protein targets.
- Yoga Trainer: yoga sequences, flexibility and breathing practice.
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
        name="lifestyle_coach",
        model=ctx.model,
        description=ctx.manifest.description,
        instruction=INSTRUCTION,
    )
