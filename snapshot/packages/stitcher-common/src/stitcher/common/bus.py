from pathlib import Path
from typing import Union, Any
from needle.bus import bus, message_store
from needle.spec import SemanticPointerProtocol

# 1. 定位资产根目录
_assets_root = Path(__file__).parent / "assets"

# 2. 注册资产路径到 MessageStore
if _assets_root.exists():
    message_store.register_asset_root(_assets_root)

# 3. 补齐 stitcher_operator (nexus) 接口
def stitcher_operator(key: Union[str, SemanticPointerProtocol], **kwargs: Any) -> str:
    """包装 pyneedle-bus 的渲染逻辑，保持与旧版 stitcher_operator 兼容。"""
    return bus.render_to_string(key, **kwargs)

# 4. 导出全局单例和操作符
__all__ = ["bus", "stitcher_operator"]