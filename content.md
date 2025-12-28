简要回答
问题已被精确定位：**初始化顺序错误 (Initialization Order Bug)**。

`stitcher --help` 显示原始 Key 的原因是：`stitcher.cli.main` 模块中的 Typer 装饰器（如 `@app.command(help=nexus.get(...))`) 是在**模块导入时立即执行**的。

而在 `stitcher.cli.__init__.py` 中，`from .main import app` 发生在资产注册代码（`stitcher_nexus.loaders.insert(...)`）**之前**。这意味着当 `main.py` 被解释执行并尝试获取帮助文本时，CLI 的语言包还没有被加载到 Nexus 中，因此 Nexus 只能返回 Key 本身作为兜底。

`check` 命令之所以正常，是因为它使用的 `L.check...` 资源来自 `stitcher-common`，这部分资源在 `stitcher.common` 导入时就已经初始化好了。

解决方案非常简单：调整 `__init__.py` 中的代码顺序，确保“先注册资产，后导入 App”。

## [WIP] fix(cli): 修复 CLI 帮助文本初始化顺序问题

### 用户需求
修复 `stitcher --help` 输出中显示原始 Key（如 `cli.app.description`）而非本地化文本的问题。

### 评论
这是一个经典的 Python 导入时副作用（Import-time Side Effects）问题。Typer/Click 的声明式定义导致 `nexus.get()` 在导入时就被调用，因此必须严格保证环境（Nexus 状态）在导入前已就绪。

### 目标
1.  修改 `packages/stitcher-cli/src/stitcher/cli/__init__.py`。
2.  将 CLI 资源的注册逻辑（创建 `cli_loader` 并注入 Nexus）移动到 `from .main import app` 之前。

### 基本原理
确保在 `main` 模块被加载、装饰器被求值之前，`stitcher_nexus` 中已经包含了 `stitcher-cli` 的资源加载器。

### 标签
#intent/fix #flow/ready #priority/high #comp/cli #concept/init #scope/core #ai/instruct #task/domain/cli #task/object/init-order #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 调整 stitcher.cli.__init__.py 的顺序

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from pathlib import Path

from needle.loaders import FileSystemLoader
from stitcher.common import stitcher_nexus

# --- Composition Root for Stitcher CLI Assets ---
# This is where the CLI layer registers its own resources into the shared nexus.
# CRITICAL: This MUST happen BEFORE importing '.main', because main.py defines
# Typer commands that resolve help strings at import time via nexus.get().

try:
    _cli_assets_root = Path(__file__).parent / "assets"
    if _cli_assets_root.is_dir():
        # 1. Create a dedicated loader for the CLI's assets.
        cli_loader = FileSystemLoader(root=_cli_assets_root)
        # 2. Add it to the nexus loader stack with the highest priority.
        #    This ensures CLI-specific strings override common ones.
        stitcher_nexus.loaders.insert(0, cli_loader)
except NameError:
    # This might happen in some testing or packaging scenarios.
    pass

# Now it is safe to import the app, as the nexus is fully primed.
from .main import app

__all__ = ["app"]
~~~~~

### 下一步建议

执行完此 Patch 后，再次运行 `stitcher --help`，应该就能看到正确的、包含 "Stitcher-Python: 缝合..." 描述的帮助信息了。
