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
| Fitness Coach | `fitness-coach` | Workout plans, nutrition numbers and motivation | `gemini-flash-latest` | its own pod | [agent.py](agents/fitness_coach/agent.py), [tools.py](agents/fitness_coach/tools.py), [evals](agents/fitness_coach/fitness_coach.evalset.json) |
| Dietician | `dietician` | Meal plans in the user's own cuisine, with calorie, protein and macro targets | `gemini-3.1-flash-lite` | `wellness` group | [agent.py](agents/dietician/agent.py), [tools.py](agents/dietician/tools.py), [evals](agents/dietician/dietician.evalset.json) |
| Yoga Trainer | `yoga-trainer` | Yoga sequences fitted to time and level, with alignment cues, modifications and breathing | `gemini-3.1-flash-lite` | `wellness` group | [agent.py](agents/yoga_trainer/agent.py), [evals](agents/yoga_trainer/yoga_trainer.evalset.json) |
| Lifestyle Coach | `lifestyle-coach` | Small, lasting habit changes around sleep, stress, routine, screens and movement | `gemini-3.1-flash-lite` | `wellness` group | [agent.py](agents/lifestyle_coach/agent.py), [evals](agents/lifestyle_coach/lifestyle_coach.evalset.json) |
| Mental Health Companion | `mental-health` | Supportive listening, coping skills, and crisis lines when someone is at risk | `gemini-3.1-flash-lite` | `wellness` group | [agent.py](agents/mental_health/agent.py), [tools.py](agents/mental_health/tools.py), [evals](agents/mental_health/mental_health.evalset.json) |
| Physio | `physio` | Screens for red flags first, then exercises, pain limits and desk ergonomics | `gemini-3.1-flash-lite` | `wellness` group | [agent.py](agents/physio/agent.py), [evals](agents/physio/physio.evalset.json) |

### What an agent is made of

- **`agent.py`** exports two things. `MANIFEST` declares the slug, version,
  model, limits and billing. `build(ctx)` returns the ADK `LlmAgent`, built
  from the module's `INSTRUCTION` string and its tools.
- **`tools.py`**, where there is one, holds plain Python functions. `build()`
  wraps each in a `FunctionTool`. They are not listed in `MANIFEST.tools`,
  which is for MCP servers only. They are not in `MANIFEST.actions` either,
  because they only compute and change nothing outside the conversation. Each
  docstring is the description the model reads, so keep it accurate.
- **`<module>.evalset.json` and `test_config.json`** are the agent's ADK evals
  and their pass criteria. See [Evals](#evals).
- **`__init__.py`** exists only for `adk eval`. It builds the agent on demand
  and does nothing when the platform imports the package.
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
- Bump `MANIFEST.version` on every change to an agent's directory, evals
  included. A deploy refuses changed files under a version it has already
  deployed.
- Run `elan validate` before every commit.
- Give a new agent evals (see [Evals](#evals)). Copy any agent's `__init__.py`
  unchanged, since it reads the slug from its folder name.

## Evals

Every agent's ADK evals sit beside its code in `agents/<module>/`:

| File | What it holds |
|---|---|
| `<module>.evalset.json` | The cases: each user turn, the tools that turn should call, and rubrics for the reply |
| `test_config.json` | The pass criteria for the set. `adk eval` finds it because it sits beside the eval set |
| `__init__.py` | Builds the agent for `adk eval` as it is deployed: the agent's own `build()` with the platform's plugins |

Because they are in the agent's directory, **editing an eval changes the
agent's directory, so it needs a `MANIFEST.version` bump** like any other
change. The eval files are also copied into the image, where nothing reads
them.

`__init__.py` is lazy. The pod imports the package every time it loads
`agents.<module>.agent`, so the file only defines a module `__getattr__`. That
builds `app` when `adk eval` asks for it and does nothing otherwise.

### Running them

Once per `.venv`, add ADK's eval extras at the ADK version already installed:

```bash
uv pip install --python .venv/bin/python \
  "google-adk[eval]==$(.venv/bin/python -c 'import google.adk; print(google.adk.__version__)')"
```

Then run one agent's set, or all of them:

```bash
elan adk eval agents/physio agents/physio/physio.evalset.json

for m in fitness_coach dietician yoga_trainer lifestyle_coach mental_health physio; do
  elan adk eval agents/$m agents/$m/$m.evalset.json
done
```

Add `--print_detailed_results` to see each case's scores. Results are saved in
`agents/<module>/.adk/eval_history/`, which is git-ignored, so they are never
committed or deployed.

**Evals call the real models** with the key in `.env`: the agent's own model,
plus `gemini-3.1-flash-lite` as the judge, three times per turn. One run of all
six sets used about 90,000 agent tokens plus the judge's calls, which comes to
well under a dollar. Model output varies, so a case can pass one run and fail
the next. Rerun with `--num_runs 3` before acting on a single failure.

**Point `adk eval` at `agents/<module>`, not `.elan/adk/<module>`.** The shims
`elan adk` generates leave `__init__.py` empty. `adk web` accepts that, but
`adk eval` refuses it ("Agent module should have either `root_agent` or
`get_agent_async`"). Each agent's own `__init__.py` builds the agent the same
way those shims do, in a form `adk eval` accepts.

### How a case is scored

- **Tool calls** (`tool_trajectory_avg_score`) apply to the Fitness Coach,
  Dietician and Mental Health Companion. Each expected tool must be called, in
  any order. Arguments are not compared, because ADK compares them for exact
  equality, which would fail `81.65` kg against `81.6` kg.
- **Rubrics** (`rubric_based_final_response_quality_v1`) apply to every agent.
  A judge model answers yes or no to each rubric on each turn. A turn passes at
  a score of 0.8, which with four rubrics or fewer means all of them must pass.

Rubrics belong on each turn, not on the case. A case-level rubric is scored
against every turn, so a turn that rightly asks a question would fail for not
yet giving the answer the next turn gives. Every rubric needs
`"type": "FINAL_RESPONSE_QUALITY"`. Without it the metric silently drops the
rubric, then fails with "Rubrics are required".

The figures quoted in rubrics are what the tools return. When a formula in a
`tools.py` changes, update the rubrics that quote it.

### What each set covers

| Agent | Cases |
|---|---|
| Fitness Coach | BMI in metric and imperial units, a full calorie, protein and macro plan, asking for missing inputs, asking then calculating over two turns, crisis |
| Dietician | A vegetarian meal plan with targets, a macro split, asking for preferences first, insulin-treated diabetes, disordered eating, crisis |
| Yoga Trainer | A beginner sequence, asking before sequencing, pregnancy, glaucoma and inversions, crisis |
| Lifestyle Coach | Fixing sleep habits, understanding before advising, possible sleep apnoea, crisis |
| Mental Health Companion | Crisis in India, crisis with the country unknown, UK support lines, exam anxiety over two turns, a medication question |
| Physio | Cauda equina red flags, a suspected calf clot, desk neck pain, asking before giving exercises, crisis |

Every agent other than the Mental Health Companion has a crisis case. It checks
the same four things each of their instructions asks for. The Mental Health
Companion's own cases test its fuller crisis procedure.

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
