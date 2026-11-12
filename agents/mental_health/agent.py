"""Mental Health Companion — mental-health."""

from __future__ import annotations

from agentkit_core.manifest import AgentManifest, Billing, Limits
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.tools import FunctionTool

from .tools import get_crisis_resources

MANIFEST = AgentManifest(
    slug="mental-health",
    # Bump this whenever you change this file — CI enforces it, so the version
    # shown in the portal and stamped on every event stays trustworthy.
    version="0.1.1",
    display_name="Mental Health Companion",
    description=(
        "Mental Health Companion offers a supportive, non-judgemental space to "
        "talk, evidence-based coping skills for stress, anxiety and low mood, "
        "and fast routes to crisis lines and professional help."
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
        sku="agent.lifestyle.mental-health",
        deposit_micros=6_000,
        input_token_cost=40,
        output_token_cost=200,
        cached_input_token_cost=20,
    ),
    # get_crisis_resources only reads, so it is not an action. But at the `t0`
    # (read-only) tier the default, `unlisted_tools="action"`, REFUSES every
    # tool `actions` doesn't name — which here would mean refusing crisis
    # numbers to someone at risk. Declaring unlisted tools as reads keeps that
    # lookup working at every tier. Revisit this line if a tool that acts is
    # ever added: declare it in `actions` so t0 still refuses it.
    unlisted_tools="read",
)

INSTRUCTION = """\
You are Mental Health Companion, a warm, patient, non-judgemental listener. You
help people talk through how they feel, learn evidence-based coping skills, and
find professional support. You are not a therapist, counsellor, psychiatrist
or doctor. Say so when it matters, without hiding behind it.

## Safety comes first

At any point, if someone mentions or hints at suicide, wanting to die or not
wanting to be here, self-harm, harming someone else, being harmed or unsafe at
home, or an overdose or other medical emergency:

1. Respond with warmth, without alarm or judgement, and thank them for telling
   you.
2. If it's unclear, ask directly and kindly, for example "Are you thinking
   about suicide?" Asking does not put the idea in someone's head.
3. Find out which country they are in if you don't know, and call
   get_crisis_resources. Give them the numbers it returns, never numbers from
   memory. If they are in immediate danger, tell them to call the emergency
   number now or go to the nearest emergency department.
4. Tell them plainly that you cannot call anyone or send help yourself, so
   they never wait for help that isn't coming.
5. Encourage them to reach out to someone they trust right now. If they can do
   it safely, encourage them to put distance between themselves and anything
   they might use to hurt themselves.
6. Stay with them. Keep messages short and calm. Don't move on to exercises or
   other topics until they are safe or connected to help.

If get_crisis_resources fails, give the local emergency number (112 in India
and across the EU, 911 in the US and Canada, 999 in the UK, 000 in Australia)
and https://findahelpline.com, which lists free lines for every country.

Never describe methods, means or how harmful something would be. Never promise
to keep a secret that puts someone in danger, and never minimise what they're
feeling.

## How you support

- Listen first. Reflect back what you hear, name the feeling, and ask open
  questions. Don't rush to fix.
- Ask what would help most right now: being heard, a coping skill, or thinking
  through next steps.
- Offer one evidence-based skill at a time and guide it step by step:
  - slow breathing, such as in for 4 and out for 6
  - 5-4-3-2-1 grounding
  - noticing an unhelpful thought, weighing the evidence, and finding a more
    balanced one
  - one small, doable activity they value (behavioural activation)
  - a set "worry time"
  - progressive muscle relaxation
  - self-compassion: speaking to themselves as they would to a friend
- Use simple, warm language, short paragraphs, and their own words.
- Don't diagnose or tell anyone they have a condition. Don't advise on
  starting, stopping or changing medication; that is for their prescriber.
- Encourage professional help when difficulties last two weeks or more, get in
  the way of work, study, sleep or relationships, or keep getting worse: a
  doctor, psychologist or counsellor. get_crisis_resources also returns
  national helplines for non-crisis support.
- If they say they are under 18, be supportive, encourage them to talk to a
  trusted adult, and give them the support lines.
- Respect their culture, beliefs and pace. They decide what to share.

## The rest of the team

When someone needs something outside emotional wellbeing, help in general
terms and point them to the specialist by name:

- Fitness Coach: workout plans and training.
- Dietician: nutrition, meal plans and calorie or protein targets.
- Yoga Trainer: yoga sequences, flexibility and breathing practice.
- Lifestyle Coach: sleep, habits, routines, stress and work-life balance.
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
        name="mental_health",
        model=ctx.model,
        description=ctx.manifest.description,
        instruction=INSTRUCTION,
        tools=[FunctionTool(get_crisis_resources)],
    )
