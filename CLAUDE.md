# lifestyle

Google ADK agents and workflows that the Elan platform builds, deploys and runs.
This repository holds only agent code and one deploy contract. The platform
supplies the image, the infrastructure and the pipeline, so there is no
Dockerfile, Kubernetes manifest, Terraform or CI workflow here, and none should
be added.

## Documentation

This platform's documentation is at https://openelan.ai/app/docs. Read the page for
what you are changing before guessing at an API.

- https://openelan.ai/app/llms.txt indexes every page, one line each.
- https://openelan.ai/app/llms-full.txt holds every page in one file,
  written for a model.

## Layout

- `elan.yaml` is the deploy contract: the tenant, the project, the source
  repository, every target, and what each is given — resources, scaling, model
  keys, secrets, egress. The platform reads it without running your code.
- `agents/<module>/agent.py` and `workflows/<module>/workflow.py` are one target
  each. Every one exports `MANIFEST` (slug, version, model, tools, limits,
  price) and `build(ctx)`, which returns the ADK agent or `google.adk.Workflow`.
- `.env` holds local settings and the model key, for `elan adk web` only. It is
  git-ignored and a deployed pod never reads it.

## Commands

```bash
elan validate                   # elan.yaml against every MANIFEST, both ways
elan adk web                    # run the agents locally, behind the platform's plugins
elan new agent <slug>           # add a target: writes the module AND declares it
elan new workflow <slug>
elan deploy                     # builds the PUSHED commit, not the working tree
elan status <deployment-id>     # the phase a deploy reached, and why it stopped
elan logs <deployment-id>       # the build output
elan invoke <slug> --text "..." # talk to a deployed agent
elan secret ls                  # which secrets are set, names only
```

## Rules

- **Add a target with `elan new`, never by hand.** A module missing from
  `elan.yaml`, or an entry with no module, is refused at deploy.
- **Bump `MANIFEST.version` whenever you change a target.** A deploy refuses a
  target whose code changed under an unchanged version.
- **Run `elan validate` before every commit** and fix everything it reports.
- **Commit and push before `elan deploy`.** It builds the remote commit.
- **No secret value goes in any file** — not `elan.yaml`, a MANIFEST, code or a
  commit. A person sets the value with `elan secret set`; `elan.yaml` names it
  under a target's `secrets:`; code reads `os.environ["..."]`. Never read,
  print or edit `.env`.
- **Use the platform's variable names.** The model key is `GOOGLE_API_KEY`
  because `llm.keys` in `elan.yaml` resolves to it; an invented name works
  locally and reads nothing once deployed.
- **Keep everything a target imports inside its own directory.** The image is
  built from `agents/` and `workflows/` only; a `lib/` at the root is gone in
  the pod.
- **Never list `agentkit-*` packages in a `pyproject.toml`.** The runtime image
  carries ADK and the platform's packages; add one only for libraries beyond
  those.
- **Declare every tool that acts in `MANIFEST.actions`.** An undeclared tool is
  not governed by autonomy policy, so it runs without anybody being asked.
- **Slugs are identity.** 5 to 16 characters, lowercase letters, digits and
  single hyphens, starting with a letter. Renaming one makes a new agent.

## ADK behavior that surprises people

- The graph class is `google.adk.Workflow`. ADK's docs describe a `GraphAgent`
  that does not ship.
- A workflow node receives the previous node's output, so put model nodes at
  the end: a model between two function nodes hands the second a sentence.
- A workflow whose last node is a `FunctionNode` returns nothing to a caller
  unless that node returns an `Event` with `content`.
- `node_input` is a reserved parameter name, and an optional declared input
  must still be present in session state.
- A paused run emits no `finished` event; a client waiting for one waits out
  its whole timeout.
- To test with no model access, register a fake model in ADK's `LLMRegistry`
  and select it with `MODEL_OVERRIDE`; the building-an-agent guide has the
  recipe. `AGENTKIT_ENV=local`, already in `.env`, is what permits it.
