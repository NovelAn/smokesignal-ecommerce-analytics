"""Pytest config: make the pure rule-based modules importable without triggering
the heavy backend/ai/__init__.py import chain (which pulls the AI client stack).

This lets the rule-based unit tests run on a bare interpreter with only jieba
installed — no fastapi/sqlalchemy/openai etc. required.
"""
import os
import sys
import types
import importlib.util

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_AI_DIR = os.path.join(_ROOT, 'backend', 'ai')

# Allow `import keyword_matcher` / `import data_extractor` directly as top-level
# modules (they only depend on jieba / typing, no project imports).
if _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

# Stub the `backend` and `backend.ai` packages so absolute imports like
# `from backend.ai.data_extractor import ...` resolve WITHOUT executing the real
# backend/ai/__init__.py (which imports minimax_client -> config -> dotenv ...).
for _pkg, _path in (('backend', []), ('backend.ai', [_AI_DIR])):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = _path
        sys.modules[_pkg] = _m


def _load_abs(mod_name: str, filename: str):
    """Load a pure module file under its absolute dotted path into sys.modules."""
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(_AI_DIR, filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load the pure dependency modules under their absolute paths so that
# rule_based_analyzer's `from backend.ai.data_extractor import ...` resolves.
_load_abs('backend.ai.data_extractor', 'data_extractor.py')
_load_abs('backend.ai.keyword_matcher', 'keyword_matcher.py')
