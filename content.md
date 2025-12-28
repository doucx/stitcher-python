你说得对，又是一个重构的连锁反应。我之前的修改解决了 `common` 包的问题，但没有同步更新依赖 `common` 包的 `cli` 包。

`AttributeError: 'FileSystemLoader' object has no attribute 'add_root'` 这个错误非常明确。在我们之前的重构中，我们遵循单一职责原则，从 `FileSystemLoader` 中移除了处理多个根目录的能力，因此 `add_root` 方法被废弃了。

`stitcher-cli` 包在其 `__init__.py` 中，仍然在使用旧的模式，试图调用这个不存在的方法来注册它自己的 `needle` 资源（比如命令的帮助文本）。

正确的做法是遵循我们建立的新架构模式：**通过组合而非修改来扩展**。

`stitcher-cli` 不应该去修改 `stitcher_loader`，而应该：
1.  为它自己的 `assets` 目录创建一个全新的、独立的 `FileSystemLoader` 实例。
2.  将这个新的加载器实例添加到 `stitcher_nexus` 的加载器列表的前面。

通过 `stitcher_nexus.loaders.insert(0, cli_loader)`，我们能确保 CLI 的资源具有**最高优先级**，可以覆盖来自 `common` 包甚至用户项目的同名资源，这完全符合分层覆盖的逻辑。

## [WIP] fix(cli): 适配新的组合式加载器架构

### 错误分析
`stitcher check` 命令因 `AttributeError` 启动失败。原因是 `stitcher.cli` 包试图调用已被废弃的 `stitcher_loader.add_root` 方法来注册其内置的 `needle` 资源。这是在 `FileSystemLoader` 切换到单根模式后，未能同步更新下游包导致的。

### 用户需求
修复此 `AttributeError`，并使 `stitcher-cli` 包能够以符合新架构的方式，将其资源正确地注册到全局的 `stitcher_nexus` 中。

### 评论
这个修复是完成我们向组合式加载器架构迁移的最后一步。它强制我们遵循“扩展优于修改”的原则。通过向 `Nexus` 的加载器列表中添加新的加载器，而不是修改已有的加载器，我们创建了一个更清晰、更可预测、更易于调试的系统。

### 目标
1.  修改 `packages/stitcher-cli/src/stitcher/cli/__init__.py` 文件。
2.  移除对 `add_root` 的调用。
3.  改为创建 `stitcher-cli` 专属的 `FileSystemLoader`。
4.  将这个新的加载器实例插入到 `stitcher_nexus.loaders` 列表的头部，以赋予其最高优先级。

### 基本原理
应用程序的不同分层（common, cli）应该各自管理自己的资源加载器。顶层的 `Nexus` 对象则充当这些加载器的“组合器”。当 CLI 模块被导入时，它有责任将其自己的资源层“注册”到这个组合器中。这种模式使得系统的资源来源清晰可见，优先级明确，并且遵循了开闭原则。

### 标签
#intent/fix #flow/ready #priority/high #comp/cli #comp/runtime #concept/config #scope/api #dx #task/domain/storage #task/object/asset-registration #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 更新 `stitcher-cli` 以使用组合模式

我们将重构 `stitcher.cli` 的初始化代码，使其遵循新的架构规范。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from pathlib import Path

from needle.loaders import FileSystemLoader
from stitcher.common import stitcher_nexus
from .main import app

# --- Composition Root for Stitcher CLI Assets ---
# This is where the CLI layer registers its own resources into the shared nexus.

# Auto-register built-in assets for the 'cli' package using the new architecture.
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

__all__ = ["app"]
~~~~~
