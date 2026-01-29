from pathlib import Path
from needle.bus import bus, message_store

# 1. 定位资产根目录 (在此前的 Acts 中已搬迁至此)
# assets 文件夹直接包含 needle/ 子目录
_assets_root = Path(__file__).parent / "assets"

# 2. 注册资产路径到 MessageStore
# 这允许 FeedbackBus 能够找到 L.check.file.fail 等指针对应的翻译模板
if _assets_root.exists():
    message_store.register_asset_root(_assets_root)

# 3. 导出全局单例，供下游业务使用
# 这里的 bus 实际上是 pyneedle.bus.feedback.FeedbackBus 的实例
__all__ = ["bus"]