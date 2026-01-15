import os
from pathlib import Path
from typing import Dict
from needle.pointer import L
from needle.operators import I18NFactoryOperator, OverlayOperator
from needle.runtime import _find_project_root

from .bus import FeedbackBus

# 1. Config Sources
# Asset paths are now relative to this file in stitcher-bus
_project_root = _find_project_root()
_bus_assets_root = Path(__file__).parent / "assets"

# 2. Factories
# Note: User overrides still live in project_root/.stitcher/needle
_user_factory = I18NFactoryOperator(_project_root / ".stitcher")
_default_factory = I18NFactoryOperator(_bus_assets_root)

# 3. Dynamic Pipeline with Caching
_operator_cache: Dict[str, OverlayOperator] = {}


def _detect_lang() -> str:
    # 1. Explicit override
    stitcher_lang = os.getenv("STITCHER_LANG")
    if stitcher_lang:
        return stitcher_lang

    # 2. System LANG (e.g. "zh_CN.UTF-8" -> "zh")
    sys_lang = os.getenv("LANG")
    if sys_lang:
        base_lang = sys_lang.split(".")[0].split("_")[0]
        if base_lang:
            return base_lang

    return "en"


def get_current_renderer() -> OverlayOperator:
    lang_code = _detect_lang()

    if lang_code in _operator_cache:
        return _operator_cache[lang_code]

    lang_ptr = getattr(L, lang_code)

    user_op = _user_factory(lang_ptr)
    default_op = _default_factory(lang_ptr)

    # Priority: User > Default
    pipeline = OverlayOperator([user_op, default_op])

    _operator_cache[lang_code] = pipeline
    return pipeline


def stitcher_operator(key):
    renderer = get_current_renderer()
    return renderer(key)


# Initialize the global singleton
bus = FeedbackBus(operator=stitcher_operator)