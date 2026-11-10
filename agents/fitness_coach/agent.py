"""Fitness Coach — fitness-coach."""

from __future__ import annotations

from agentkit_core.manifest import AgentManifest, Billing, Limits
from google.adk.agents import BaseAgent, LlmAgent

MANIFEST = AgentManifest(
    slug="fitness-coach",
    # Bump this whenever you change this file — CI enforces it, so the version
    # shown in the portal and stamped on every event stays trustworthy.
    version="0.1.0",
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

INSTRUCTION = """\
You are fitness coach, help people achieve their fitness goals.
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
    )
