Of course. Your analysis is spot on. The current implementation of `Needle` is too tightly coupled to the project's working directory, making it brittle and unsuitable for a distributed package.

The solution you've outlined is the correct and standard approach for creating robust, asset-aware tools:
1.  **Enhance the Runtime:** Decouple `Needle` from a single filesystem root by introducing a multi-root search path.
2.  **Package the Assets:** Move the default resources into the `stitcher-common` package itself, so they are always available.
3.  **Automate Registration:** Make the package self-aware, allowing it to automatically register its own assets with the runtime upon initialization.

This will create a layered system where built-in defaults are always present, but can be seamlessly overridden by user-specific files in their project's `.stitcher` directory. I will now generate a plan to execute this refactoring.

## [WIP] feat(needle): Enhance runtime with multi-root support and asset packaging

### 用户需求
1.  **增强 `Needle` 运行时**: 修改 `Needle` 类，使其能够管理一个包含多个根目录的搜索列表，并能合并从这些位置发现的语言资源。
2.  **资源打包**: 将默认的 `needle` 资源文件从项目根目录的 `.stitcher` 文件夹迁移到 `stitcher-common` 包内部，以便它们能随包一起分发。
3.  **自动注册**: 在 `stitcher-common` 中实现逻辑，使其在初始化时能自动发现并向全局 `needle` 实例注册其内部的资源目录。

### 评论
这是一个至关重要的重构，它将 `stitcher` 从一个仅能在开发仓库中运行的工具，转变为一个可被任意项目依赖和使用的、健壮的、可分发的命令行应用。通过将核心资源打包并实现一个分层的配置加载系统，我们极大地提升了项目的可靠性和封装性。

### 目标
1.  重构 `stitcher-needle/src/stitcher/needle/runtime.py` 中的 `Needle` 类，用一个 `roots` 列表替换单一的 `root_path`。
2.  修改 `_ensure_lang_loaded` 方法，使其能够遍历所有已注册的 `roots`，搜索 `needle/` 和 `.stitcher/needle/` 两种路径，并智能地合并找到的资源。
3.  将 `.stitcher/needle/en` 目录物理移动到 `packages/stitcher-common/src/stitcher/common/assets/needle/en`。
4.  在 `stitcher-common` 的 `__init__.py` 或 `bus.py` 中添加代码，利用 `__file__` 定位其自身的 `assets` 目录，并调用 `needle.add_root()` 将其注册。
5.  更新 `stitcher-common` 的 `pyproject.toml`，确保 `assets` 目录被包含在构建的 wheel 包中。

### 基本原理
我们将把 `Needle` 的设计模式从“单一根目录”升级为“分层搜索路径”。系统将维护一个 `roots` 列表。`stitcher-common` 包会首先向这个列表注册其内部的 `assets` 目录，作为默认资源的来源。随后，`Needle` 的默认构造函数会添加当前项目的根目录。在加载资源时，`Needle` 会按顺序扫描所有 `roots`，后加载的配置将覆盖先加载的，从而实现了“用户配置优先于内置默认配置”的优雅覆盖机制。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #comp/common #concept/config #scope/core #ai/instruct #task/domain/runtime #task/object/asset-loading #task/action/refactor #task/state/begin

---
### Script

#### Acts 1: 重构 `Needle` 运行时以支持多根目录

首先，我们修改核心的 `Needle` 类，使其能够处理一个路径列表，而不是单个路径。加载逻辑将被更新以遍历所有根目录并合并结果。

~~~~~act
write_file
packages/stitcher-needle/src/stitcher/needle/runtime.py
~~~~~
~~~~~python
import os
from pathlib import Path
from typing import Dict, Optional, Union, List

from .loader import Loader
from .pointer import SemanticPointer


class Needle:
    """
    The runtime kernel for semantic addressing.
    """

    def __init__(self, roots: Optional[List[Path]] = None):
        self.default_lang = "en"
        self._registry: Dict[str, Dict[str, str]] = {}  # lang -> {fqn: value}
        self._loader = Loader()
        self._loaded_langs: set = set()

        if roots:
            self.roots = roots
        else:
            # Default behavior: find project root and add it.
            self.roots = [self._find_project_root()]

    def add_root(self, path: Path):
        """Adds a new search root to the beginning of the list."""
        if path not in self.roots:
            self.roots.insert(0, path)

    def _find_project_root(self, start_dir: Optional[Path] = None) -> Path:
        """
        Finds the project root by searching upwards for common markers.
        Search priority: pyproject.toml -> .git
        """
        current_dir = (start_dir or Path.cwd()).resolve()
        while current_dir.parent != current_dir:  # Stop at filesystem root
            if (current_dir / "pyproject.toml").is_file():
                return current_dir
            if (current_dir / ".git").is_dir():
                return current_dir
            current_dir = current_dir.parent
        return start_dir or Path.cwd()

    def _ensure_lang_loaded(self, lang: str):
        if lang in self._loaded_langs:
            return

        # Initialize an empty dict for the language
        merged_registry: Dict[str, str] = {}

        # Iterate through all registered roots. Order is important.
        # Earlier roots are defaults, later roots are overrides.
        for root in self.roots:
            # Path Option 1: .stitcher/needle/<lang> (for project-specific overrides)
            hidden_path = root / ".stitcher" / "needle" / lang
            if hidden_path.is_dir():
                merged_registry.update(self._loader.load_directory(hidden_path))

            # Path Option 2: needle/<lang> (for packaged assets)
            asset_path = root / "needle" / lang
            if asset_path.is_dir():
                merged_registry.update(self._loader.load_directory(asset_path))

        self._registry[lang] = merged_registry
        self._loaded_langs.add(lang)

    def get(
        self, pointer: Union[SemanticPointer, str], lang: Optional[str] = None
    ) -> str:
        """
        Resolves a semantic pointer to a string value with graceful fallback.

        Lookup Order:
        1. Target Language
        2. Default Language (en)
        3. Identity (the key itself)
        """
        key = str(pointer)
        target_lang = lang or os.getenv("STITCHER_LANG", self.default_lang)

        # 1. Try target language
        self._ensure_lang_loaded(target_lang)
        val = self._registry.get(target_lang, {}).get(key)
        if val is not None:
            return val

        # 2. Try default language (if different)
        if target_lang != self.default_lang:
            self._ensure_lang_loaded(self.default_lang)
            val = self._registry.get(self.default_lang, {}).get(key)
            if val is not None:
                return val

        # 3. Fallback to Identity
        return key


# Global Runtime Instance
needle = Needle()
~~~~~

#### Acts 2: 更新 `Needle` 的单元测试

测试用例需要更新，以验证新的多根目录加载和覆盖逻辑是否正确工作。

~~~~~act
write_file
packages/stitcher-needle/tests/test_runtime.py
~~~~~
~~~~~python
import json
from pathlib import Path
from stitcher.needle import Needle, L


def test_needle_multi_root_loading_and_override(tmp_path: Path):
    # 1. Setup a workspace with two separate roots
    
    # Root 1: Simulates a packaged asset directory
    pkg_asset_root = tmp_path / "pkg" / "assets"
    (pkg_asset_root / "needle" / "en" / "cli").mkdir(parents=True)
    (pkg_asset_root / "needle" / "en" / "cli" / "main.json").write_text(
        json.dumps({
            "cli.default": "I am a default",
            "cli.override_me": "Default Value"
        })
    )

    # Root 2: Simulates a user's project directory with overrides
    project_root = tmp_path / "my_project"
    project_root.mkdir()
    (project_root / "pyproject.toml").touch() # Makes it a project root
    
    user_override_dir = project_root / ".stitcher" / "needle" / "en"
    user_override_dir.mkdir(parents=True)
    (user_override_dir / "overrides.json").write_text(
        json.dumps({
            "cli.override_me": "User Override!",
            "cli.user_only": "I am from the user"
        })
    )

    # 2. Initialize Runtime and add roots
    # Initialize with project_root, then add package root.
    # The project root will be checked last, thus overriding package assets.
    rt = Needle(roots=[project_root])
    rt.add_root(pkg_asset_root) # add_root prepends

    # Final search order should be: [pkg_asset_root, project_root]

    # 3. Test assertions
    # Found in default assets
    assert rt.get(L.cli.default) == "I am a default"

    # Found in user overrides
    assert rt.get(L.cli.user_only) == "I am from the user"

    # Value from user should take precedence over default
    assert rt.get(L.cli.override_me) == "User Override!"

    # Ultimate Identity Fallback
    assert rt.get(L.unknown.key) == "unknown.key"
~~~~~

#### Acts 3: 迁移内置资源并清理旧目录

现在我们将物理文件移动到 `stitcher-common` 包中，并删除根目录下的旧 `.stitcher` 文件夹。

~~~~~act
run_command
~~~~~
~~~~~bash
# Create the new asset directory structure
mkdir -p packages/stitcher-common/src/stitcher/common/assets

# Move the old needle directory into the new assets location
mv .stitcher/needle packages/stitcher-common/src/stitcher/common/assets/

# Remove the now-empty old .stitcher directory
rm -rf .stitcher
~~~~~

#### Acts 4: 在 `stitcher-common` 中实现资源自动注册

我们修改 `stitcher-common` 的代码，让它在被导入时自动将自己的 `assets` 目录注册到全局的 `needle` 实例中。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Make core singletons easily accessible
from .messaging.bus import bus
from stitcher.needle import needle
from pathlib import Path

# --- Auto-register built-in assets ---
# Find the path to our packaged assets directory and register it with Needle.
# This makes default translations and messages available out-of-the-box.
try:
    # __file__ gives the path to this __init__.py file
    _assets_path = Path(__file__).parent / "assets"
    if _assets_path.is_dir():
        needle.add_root(_assets_path)
except NameError:
    # __file__ might not be defined in some environments (e.g. frozen).
    # We can add more robust discovery methods here later if needed.
    pass
# -------------------------------------


__all__ = ["bus"]
~~~~~

#### Acts 5: 确保资源被打包

最后，也是关键的一步，我们必须告诉构建工具 `hatch` 将 `assets` 目录包含在最终的 wheel 包中。

~~~~~act
patch_file
packages/stitcher-common/pyproject.toml
~~~~~
~~~~~toml.old
[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
~~~~~
~~~~~toml.new
[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
include = ["/src/stitcher/common/assets"]
~~~~~

### 下一步建议
我们已经完成了核心的运行时重构和资源迁移。下一步是验证整个工具链在新的资源加载机制下是否仍然正常工作。
我建议运行完整的集成测试套件，特别是 `test_check_command.py` 和 `test_init_command.py`，确保 `StitcherApp` 能够正确地向用户显示内置的提示和错误消息。如果所有测试通过，这个重构就可以被认为是成功的。
