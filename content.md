## [WIP] feat: Refactor locales to SST and finalize Needle runtime

### 用户需求
遵循 SST (物理分片语义分类法) 规范，重构 `locales` 目录结构。同时，将所有资源加载逻辑固化在 `stitcher-needle` 运行时中，并使 `MessageBus` 成为 `needle` 的一个纯粹客户端，从而完成核心架构的解耦。

### 评论
这是对 `stitcher-needle` 架构的最终定型。通过将加载逻辑完全下沉到 `needle` 并简化 `MessageBus`，我们实现了设计初衷：一个负责解析，一个负责分发。采用 FQN (全限定名) 作为 JSON 文件中的键，极大地增强了系统的鲁棒性和未来工具链的可扩展性。

### 目标
1.  **简化 `Loader`**: 移除 FQN 展平逻辑，使其仅负责加载和合并 JSON 文件。
2.  **重构 `MessageBus`**: 移除 `MessageStore`，使其不再处理文件 I/O，而是直接调用 `needle.get()` 来解析消息。
3.  **重构 `Renderer` 协议**: `Renderer` 的职责是“呈现”，它不应该关心消息的 ID 或格式化。它现在将只接收最终的、已解析的字符串。
4.  **迁移 `locales` 文件**: 删除旧文件，并根据 SST 规范创建新的、使用 FQN 键的 JSON 文件。
5.  **更新测试**: 确保集成测试反映新的架构。

### 基本原理
此重构遵循单一职责原则。`Needle` 封装了所有关于“语义”的知识（如何加载、如何降级），`MessageBus` 只负责消息的“路由”，而 `Renderer` 只负责最终的“呈现”。这是一个清晰、分层、可测试的架构。

### 标签
#intent/refine #flow/ready #priority/high #comp/common #comp/runtime #scope/core #ai/instruct #task/domain/runtime #task/object/sst-migration #task/action/implementation #task/state/continue

---
### Script

#### Acts 1: 简化 `Loader` 以支持 FQN 键

我们重写 `Loader`，移除所有路径前缀和展平逻辑。它的新工作是简单地合并所有找到的 JSON 文件中的顶级键。

~~~~~act
write_file
packages/stitcher-needle/src/stitcher/needle/loader.py
~~~~~
~~~~~python
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .interfaces import FileHandler
from .handlers import JsonHandler


class Loader:
    def __init__(self, handlers: Optional[List[FileHandler]] = None):
        # Default to JsonHandler if none provided
        self.handlers = handlers or [JsonHandler()]

    def _load_and_merge_file(self, path: Path, registry: Dict[str, str]):
        for handler in self.handlers:
            if handler.match(path):
                try:
                    content = handler.load(path)
                    # Keys are now expected to be full FQNs at the top level.
                    # We simply validate they are strings and update the registry.
                    for key, value in content.items():
                        registry[key] = str(value)
                except Exception:
                    # Silently ignore malformed files.
                    pass
                return # Stop after first matching handler

    def load_directory(self, root_path: Path) -> Dict[str, str]:
        """
        Scans a directory for supported config files and merges their top-level
        keys into a single flat registry.
        """
        registry: Dict[str, str] = {}

        if not root_path.is_dir():
            return registry

        for dirpath, _, filenames in os.walk(root_path):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                self._load_and_merge_file(file_path, registry)

        return registry
~~~~~

#### Acts 2: 重构 `MessageBus` 和 `Renderer`

`MessageBus` 不再需要 `MessageStore`，而是直接使用全局的 `needle` 实例。`Renderer` 协议也相应简化。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/messaging/protocols.py
~~~~~
~~~~~python
from typing import Any, Protocol

class Renderer(Protocol):
    """
    Protocol for message renderers. A renderer's only job is to
    present a final, formatted string to the user.
    """

    def render(self, message: str, level: str) -> None:
        """
        Renders the message.

        Args:
            message: The fully resolved string to be displayed.
            level: The log level ("info", "warning", "error", "success").
        """
        ...
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/messaging/bus.py
~~~~~
~~~~~python
from typing import Any, Optional, Union

from stitcher.needle import SemanticPointer, needle
from .protocols import Renderer


class MessageBus:
    def __init__(self):
        self._renderer: Optional[Renderer] = None

    def set_renderer(self, renderer: Renderer):
        self._renderer = renderer

    def _render(self, level: str, msg_id: Union[str, SemanticPointer], **kwargs: Any) -> None:
        if not self._renderer:
            return
        
        # Resolve the pointer to a string template using the Needle runtime
        template = needle.get(msg_id)
        
        # Format the final message
        try:
            message = template.format(**kwargs)
        except KeyError:
            # Fallback for formatting errors
            message = f"<formatting_error for '{str(msg_id)}'>"
            
        self._renderer.render(message, level)

    def info(self, msg_id: Union[str, SemanticPointer], **kwargs: Any) -> None:
        self._render("info", msg_id, **kwargs)

    def success(self, msg_id: Union[str, SemanticPointer], **kwargs: Any) -> None:
        self._render("success", msg_id, **kwargs)
        
    def warning(self, msg_id: Union[str, SemanticPointer], **kwargs: Any) -> None:
        self._render("warning", msg_id, **kwargs)

    def error(self, msg_id: Union[str, SemanticPointer], **kwargs: Any) -> None:
        self._render("error", msg_id, **kwargs)

# Global singleton instance
bus = MessageBus()
~~~~~

#### Acts 3: 更新 `CliRenderer` 以符合新协议

`CliRenderer` 的实现变得更简单，它只负责打印。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/rendering.py
~~~~~
~~~~~old
import typer
from stitcher.common.messaging import MessageStore, protocols

class CliRenderer(protocols.Renderer):
    """
    Renders messages to the command line using Typer for colored output.
    """
    def __init__(self, store: MessageStore):
        self._store = store

    def render(self, msg_id: str, level: str, **kwargs):
        message = self._store.get(msg_id, **kwargs)
        
        color = None
        if level == "success":
~~~~~
~~~~~new
import typer
from stitcher.common.messaging import protocols

class CliRenderer(protocols.Renderer):
    """
    Renders messages to the command line using Typer for colored output.
    """
    def render(self, message: str, level: str):
        color = None
        if level == "success":
~~~~~

#### Acts 4: 更新 CLI 的 `bus` 注入

`bus` 不再需要 `store`，`CliRenderer` 也不再需要 `store`。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~old
# --- Dependency Injection at the very start ---
# The CLI is the composition root. It decides *which* renderer to use.
cli_renderer = CliRenderer(store=bus.store)
bus.set_renderer(cli_renderer)
# ---------------------------------------------
~~~~~
~~~~~new
# --- Dependency Injection at the very start ---
# The CLI is the composition root. It decides *which* renderer to use.
cli_renderer = CliRenderer()
bus.set_renderer(cli_renderer)
# ---------------------------------------------
~~~~~

#### Acts 5: 迁移 `locales` 物理文件

现在，我们删除旧文件并创建符合新 SST 规范的文件。

~~~~~act
delete_file
packages/stitcher-common/src/stitcher/common/locales/en/cli.json
~~~~~

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-common/src/stitcher/common/locales/en/generate
mkdir -p packages/stitcher-common/src/stitcher/common/locales/en/error
mkdir -p packages/stitcher-common/src/stitcher/common/locales/en/cli
mkdir -p packages/stitcher-common/src/stitcher/common/locales/en/warning
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/locales/en/generate/main.json
~~~~~
~~~~~json
{
    "generate.file.success": "✅ Generated stub: {path}",
    "generate.run.complete": "✨ Generation complete. {count} files created."
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/locales/en/cli/command.json
~~~~~
~~~~~json
{
    "cli.command.not_implemented": "ℹ️  Command '{command}' is not yet implemented."
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/locales/en/error/main.json
~~~~~
~~~~~json
{
    "error.config.not_found": "⚠️  No [tool.stitcher] config found in pyproject.toml. Nothing to do.",
    "error.generic": "❌ An unexpected error occurred: {error}",
    "error.plugin.inspection": "❌ Error inspecting plugin: {error}"
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/locales/en/warning/main.json
~~~~~
~~~~~json
{
    "warning.no_files_or_plugins_found": "🤔 No source files or plugins were found to process."
}
~~~~~

#### Acts 6: 更新 `Needle` 运行时以指向 `common`

`needle` 的默认根路径应该指向 `stitcher-common` 内部，而不是项目根目录。

~~~~~act
patch_file
packages/stitcher-needle/src/stitcher/needle/runtime.py
~~~~~
~~~~~old
    def _find_project_root(self) -> Path:
        """
        Simple heuristic to find where 'stitcher' directory might be.
        Defaults to current working directory.
        """
        return Path.cwd()

    def _ensure_lang_loaded(self, lang: str):
        if lang in self._loaded_langs:
            return

        # SST path: project_root/stitcher/needle/<lang>/
        needle_dir = self.root_path / "stitcher" / "needle" / lang
        
        # Load and cache
        self._registry[lang] = self._loader.load_directory(needle_dir)
~~~~~
~~~~~new
    def _find_project_root(self) -> Path:
        """
        The canonical source for locales is inside the stitcher-common package.
        """
        # Assumes this file is at .../stitcher/needle/runtime.py
        # We want .../stitcher/common/
        return Path(__file__).parent.parent.parent / "common"

    def _ensure_lang_loaded(self, lang: str):
        if lang in self._loaded_langs:
            return

        # SST path: stitcher-common/src/stitcher/common/locales/<lang>/
        locales_dir = self.root_path / "locales" / lang
        
        # Load and cache
        self._registry[lang] = self._loader.load_directory(locales_dir)
~~~~~
