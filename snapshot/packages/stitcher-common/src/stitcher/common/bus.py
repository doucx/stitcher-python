import os
from pathlib import Path
from typing import Union, Any

from needle.bus import bus
from needle.operators import I18NFactoryOperator, OverlayOperator
from needle.runtime import nexus as global_nexus
from needle.spec import SemanticPointerProtocol


def _detect_lang() -> str:
    """检测系统或环境变量中定义的语言。"""
    # 1. 显式覆盖
    env_lang = os.getenv("NEEDLE_LANG") or os.getenv("STITCHER_LANG")
    if env_lang:
        return env_lang

    # 2. 系统 LANG 变量 (例如 en_US.UTF-8 -> en)
    sys_lang = os.getenv("LANG")
    if sys_lang:
        base_lang = sys_lang.split(".")[0].split("_")[0]
        if base_lang:
            return base_lang

    return "en"


# 1. 定位资产根目录与语言
_assets_root = Path(__file__).parent / "assets"
_lang = _detect_lang()

# 2. 组装 Stitcher 专属的 Operator
# I18NFactoryOperator 负责根据语言代码从资产目录加载 FileSystemOperator
_factory = I18NFactoryOperator(_assets_root)
_stitcher_i18n = _factory(_lang)

# 3. 构造 Nexus (层叠 Operator)
# 优先级：Stitcher 本地资产 > 全局默认 Nexus
_nexus = OverlayOperator([_stitcher_i18n, global_nexus])

# 4. 注入到全局反馈总线
# 这样 bus.present(), bus.info() 等方法就能使用组装好的解析逻辑
bus.set_operator(_nexus)


# 5. 定义 stitcher_operator (Nexus) 接口
# 此接口用于在 CLI 或代码中直接获取渲染后的字符串
def stitcher_operator(key: Union[str, SemanticPointerProtocol], **kwargs: Any) -> str:
    """
    Stitcher 的核心字符串解析器。
    它包装了 bus.render_to_string，提供从 Pointer 到最终格式化字符串的转换。
    """
    return bus.render_to_string(key, **kwargs)


# 6. 导出全局单例和操作符
__all__ = ["bus", "stitcher_operator"]
