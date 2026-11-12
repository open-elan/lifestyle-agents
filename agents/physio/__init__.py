"""Eval entry point for `adk eval`. The platform itself never uses it.

    elan adk eval agents/<module> agents/<module>/<module>.evalset.json

`adk eval` imports this file and reads `app` from it. agent.py exports MANIFEST
and build(ctx) instead, and the shims `elan adk` generates under .elan/adk/
leave their __init__.py empty, which `adk eval` refuses ("Agent module should
have either `root_agent` or `get_agent_async`"). So `app` is built here, the
way those shims and a pod build it: the platform registry resolves this target
and builds it with the platform's plugins.

LAZY ON PURPOSE. The pod imports this package every time it imports
agents.<module>.agent, so nothing may happen at import time. `app` is built
only when something asks for it, and only `adk eval` does.

Identical in every agent: the slug comes from this folder's name.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_app: Any = None


def __getattr__(name: str) -> Any:
    if name != "app":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    global _app
    if _app is None:
        from agentkit_runtime.builder import build_app
        from agentkit_runtime.config import Settings
        from agentkit_runtime.plugins import build_plugins
        from agentkit_runtime.registry import resolve

        here = Path(__file__).resolve().parent
        # PASSED, NOT INHERITED, as in elan's shim: Settings would otherwise
        # read TARGETS_ROOT from the environment.
        settings = Settings(targets_root=here.parents[1])
        target = resolve(here.name.replace("_", "-"), settings)
        plugins, _ = build_plugins(target, settings, target.version_stamp(settings.build_sha))
        _app = build_app(target, settings, plugins=plugins)
    return _app
