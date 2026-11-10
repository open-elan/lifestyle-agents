# lifestyle

Agents deployed to the Elan platform from this repository.

## Getting set up

Put your model key in `.env` (git-ignored), then:

```bash
elan env                                    # the runtime, into .venv
elan validate                               # both files, checked against each other
elan adk web                                # drive the agents locally
```

## The two files, and why there are two

`elan.yaml` holds **deploy-time facts** — what to build, how big, what it may
reach. Each agent's Python `MANIFEST` holds **runtime behaviour** — its model,
its tools, what it may do without asking. No field appears in both. Where they
look like they overlap they are in a validation relationship: the MANIFEST
states what the agent asks for, `elan.yaml` states what the platform permits,
and a deploy is refused on a mismatch.

`elan new agent <slug>` writes both halves, which is the point of it.

## The agents

Six agents, one per directory under `agents/`. Each directory is named after
its slug, with underscores in place of hyphens.

| Agent | Slug | What it does | Model | Runs in | Files |
|---|---|---|---|---|---|
| Fitness Coach | `fitness-coach` | Workout plans, nutrition numbers and motivation | `gemini-flash-latest` | its own pod | [agent.py](agents/fitness_coach/agent.py), [tools.py](agents/fitness_coach/tools.py) |
| Dietician | `dietician` | Meal plans in the user's own cuisine, with calorie, protein and macro targets | `gemini-3.1-flash-lite` | `wellness` group | [agent.py](agents/dietician/agent.py), [tools.py](agents/dietician/tools.py) |
| Yoga Trainer | `yoga-trainer` | Yoga sequences fitted to time and level, with alignment cues, modifications and breathing | `gemini-3.1-flash-lite` | `wellness` group | [agent.py](agents/yoga_trainer/agent.py) |
| Lifestyle Coach | `lifestyle-coach` | Small, lasting habit changes around sleep, stress, routine, screens and movement | `gemini-3.1-flash-lite` | `wellness` group | [agent.py](agents/lifestyle_coach/agent.py) |
| Mental Health Companion | `mental-health` | Supportive listening, coping skills, and crisis lines when someone is at risk | `gemini-3.1-flash-lite` | `wellness` group | [agent.py](agents/mental_health/agent.py), [tools.py](agents/mental_health/tools.py) |
| Physio | `physio` | Screens for red flags first, then exercises, pain limits and desk ergonomics | `gemini-3.1-flash-lite` | `wellness` group | [agent.py](agents/physio/agent.py) |

### What an agent is made of

- **`agent.py`** exports two things. `MANIFEST` declares the slug, version,
  model, limits and billing. `build(ctx)` returns the ADK `LlmAgent`, built
  from the module's `INSTRUCTION` string and its tools.
- **`tools.py`**, where there is one, holds plain Python functions. `build()`
  wraps each in a `FunctionTool`. They are not listed in `MANIFEST.tools`,
  which is for MCP servers only. They are not in `MANIFEST.actions` either,
  because they only compute and change nothing outside the conversation. Each
  docstring is the description the model reads, so keep it accurate.
- **An entry under `targets:`** in [elan.yaml](elan.yaml) says where the agent
  runs and which models it may use.

Every `INSTRUCTION` follows the same shape: the role, the domain guidance, a
safety section, and a closing "The rest of the team" list naming the other
agents. When an agent is added or renamed, update that list in every other
agent too.

### Tools

| Tool | Used by | What it does |
|---|---|---|
| `calculate_bmi` | Fitness Coach, Dietician | BMI, category and healthy weight range; optional Asian cut-offs |
| `calculate_daily_calories` | Fitness Coach, Dietician | Resting calories (Mifflin-St Jeor), maintenance, and a goal target with a safety floor for fat loss |
| `calculate_daily_protein` | Fitness Coach, Dietician | Grams per day for the goal; uses the weight at BMI 25 when BMI is 30 or more |
| `calculate_macros` | Fitness Coach, Dietician | Splits a calorie target into protein, fat and carbs |
| `get_crisis_resources` | Mental Health Companion | Checked crisis and support lines for eight countries, plus findahelpline.com for the rest |

**The nutrition calculators exist twice, on purpose.** An agent may import only
from its own directory, so [dietician/tools.py](agents/dietician/tools.py) is a
copy of [fitness_coach/tools.py](agents/fitness_coach/tools.py). Fix a formula
in both, and bump both versions.

**The crisis numbers are data that someone checked.** Recheck them when
`VERIFIED_ON` in [mental_health/tools.py](agents/mental_health/tools.py) gets
old, and add a country only with numbers confirmed from its official source.

### How they are deployed

[elan.yaml](elan.yaml) runs the Fitness Coach in its own pod with its own
database. The other five share one pod in the `wellness` group: 500m CPU,
1Gi memory, 0 to 2 replicas, and one database. They scale, restart and roll out
together. A group is **not** a security boundary, because every member can
read the others' database. Move an agent out with
`deployment: {runtime: isolated}` and a `database:` block of its own.

A group cannot choose a model; each target does. A target's `llm` block in
`elan.yaml` must list the model its `MANIFEST.model` names, or `elan validate`
refuses it.

### Billing

Each agent bills under its own SKU, `agent.lifestyle.<slug>`, at the same
retail price per million tokens: $0.40 input, $2.00 output, $0.20 cached input.
Prices are in the `billing=` block of each `MANIFEST`.

### Changing or adding an agent

- Add an agent with `elan new agent <slug>`, never by hand. It writes the
  module and the `elan.yaml` entry together.
- Bump `MANIFEST.version` on every change to an agent's directory. A deploy
  refuses changed code under a version it has already deployed.
- Run `elan validate` before every commit.

## Custom plugins

A target may add ADK plugins of its own, declared in its `MANIFEST`:

```python
MANIFEST = AgentManifest(
    ...,
    plugins=[".plugins.Redactor"],   # plugins.py beside this file
)
```

A leading dot is relative to the target's own package, like a Python import;
without one it is absolute, for a plugin from a library in your
`pyproject.toml`. The path names a `BasePlugin` subclass (constructed with no
arguments) or an already-built instance — an instance is how a plugin gets
configuration.

**Keep it inside the target's directory.** The image is built from `agents/`
and `workflows/` only, so a `lib/` at the repo root is there when your manifest
is read and gone when the pod runs.

Your plugins run **after** the platform's, and that ordering is fixed. ADK
stops at the first callback that returns a value, so anything earlier would
skip the platform's gates rather than sit beside them.

Two ADK behaviours worth knowing before you write one: a nested `AgentTool` or
`WorkflowTool` run fires **no** plugin callbacks at all, and `on_event_callback`
does not fire for a run halted in `before_run_callback`.

## Dependencies

There is no `pyproject.toml` here and you may not need one. The platform's
runtime image already carries ADK and the agentkit packages; add a
`pyproject.toml` only for libraries **beyond** those, and the build will
install it. Never put `agentkit-*` in it.

## Deploying

```bash
git push          # elan deploy builds the REMOTE commit, not your disk
elan deploy
```
