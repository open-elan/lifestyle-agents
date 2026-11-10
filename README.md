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
