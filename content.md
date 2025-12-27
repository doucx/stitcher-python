简要回答
我们将通过增强 Stitcher 工具自身的能力来实现这一目标。

## [WIP] feat: 在 Stitcher 中实现中心化 Stub 生成功能

### 摘要头
## [WIP] feat(app): 实现基于 `stub_path` 的中心化存根生成

### 用户需求
在不改变物理包结构（保留命名空间包和独立子包）的前提下，解决静态分析工具（Pyright/Pytest）因 `pkgutil` 命名空间包机制而产生的解析错误。

### 评论
这是一个“吃自己的狗粮” (Dogfooding) 的经典案例。通过让 Stitcher 理解 Monorepo 的结构并生成一个物理上聚合的 `stubs` 目录，我们为静态分析工具提供了一个无歧义的“事实视图”。这不仅修复了当前问题，还为未来 Stitcher 支持更复杂的架构（如插件系统）奠定了基础。

### 目标
1.  **修改配置加载器**: 在 `StitcherConfig` 中支持新的 `stub_path` 选项。
2.  **实现逻辑路径推断**: 在 `StitcherApp` 中实现从 `packages/*/src/...` 到 `...` 的逻辑路径映射算法。
3.  **重定向生成输出**: 修改 `_generate_stubs` 逻辑，当配置了 `stub_path` 时，将生成的 `.pyi` 文件聚合到该目录。
4.  **应用配置**: 在项目根目录启用此功能并生成 stubs。

### 基本原理
目前的 `stitcher generate` 命令是将 `.pyi` 文件生成在源文件旁边。对于命名空间包，这意味着 `.pyi` 文件也是物理分散的，导致 Pyright 无法将它们识别为同一个包。
通过引入 `stub_path`，我们可以指示 Stitcher 将所有 `.pyi` 文件“缝合”到一个统一的输出目录（例如 `typings/`）中。在这个目录下，`needle/__init__.pyi` 和 `needle/pointer.pyi` 将物理相邻，从而满足静态分析工具对常规包结构的期望。

### 标签
#intent/build #flow/ready #priority/high
#comp/build #concept/config #scope/dx
#ai/instruct
#task/domain/testing #task/object/static-analysis #task/action/implement-stubs-generation
#task/state/begin #task/status/active

---

### Script

#### Acts 1: 更新 `stitcher-config` 以支持 `stub_path`
我们需要先修改配置数据结构，以便能够接收用户的意图。

~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python.old
@dataclass
class StitcherConfig:
    scan_paths: List[str] = field(default_factory=list)
    plugins: Dict[str, str] = field(default_factory=dict)
~~~~~
~~~~~python.new
@dataclass
class StitcherConfig:
    scan_paths: List[str] = field(default_factory=list)
    plugins: Dict[str, str] = field(default_factory=dict)
    stub_path: Optional[str] = None
~~~~~

~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python.old
    # Create config with data from file, falling back to defaults.
    return StitcherConfig(
        scan_paths=stitcher_data.get("scan_paths", []), plugins=plugins
    )
~~~~~
~~~~~python.new
    # Create config with data from file, falling back to defaults.
    return StitcherConfig(
        scan_paths=stitcher_data.get("scan_paths", []),
        plugins=plugins,
        stub_path=stitcher_data.get("stub_path"),
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/__init__.py
~~~~~
~~~~~python.old
from .loader import StitcherConfig, load_config_from_path

__all__ = ["StitcherConfig", "load_config_from_path"]
~~~~~
~~~~~python.new
from typing import Optional
from .loader import StitcherConfig, load_config_from_path

__all__ = ["StitcherConfig", "load_config_from_path", "Optional"]
~~~~~

#### Acts 2: 更新 `stitcher-application` 实现聚合逻辑
这是核心逻辑变更。我们需要能够从物理路径推断出逻辑导入路径，并将输出重定向。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def _process_plugins(self, plugins: Dict[str, str]) -> List[ModuleDef]:
        # A dictionary to hold our virtual modules, keyed by their intended file path
        virtual_modules: Dict[Path, ModuleDef] = defaultdict(
            lambda: ModuleDef(file_path="")
        )
~~~~~
~~~~~python.new
    def _derive_logical_path(self, file_path: str) -> Path:
        """
        Heuristic to derive the logical import path from a physical file path.
        Assumes a standard 'src/' layout.
        e.g., 'packages/pkg-a/src/foo/bar.py' -> 'foo/bar.py'
        """
        path_obj = Path(file_path)
        parts = path_obj.parts
        
        # Find the LAST occurrence of 'src' to handle potential nested structures correctly
        try:
            # rindex equivalent for list
            src_index = len(parts) - 1 - parts[::-1].index("src")
            return Path(*parts[src_index + 1:])
        except ValueError:
            # 'src' not found, fallback to original path
            return path_obj

    def _process_plugins(self, plugins: Dict[str, str]) -> List[ModuleDef]:
        # A dictionary to hold our virtual modules, keyed by their intended file path
        virtual_modules: Dict[Path, ModuleDef] = defaultdict(
            lambda: ModuleDef(file_path="")
        )
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def _generate_stubs(self, modules: List[ModuleDef]) -> List[Path]:
        generated_files: List[Path] = []
        for module in modules:
            # Step 1: Hydrate IR with external docs (The "Stitching" process)
            self.doc_manager.apply_docs_to_module(module)

            # Step 2: Generate code
            pyi_content = self.generator.generate(module)
            # Output path is relative to the project root
            output_path = self.root_path / Path(module.file_path).with_suffix(".pyi")

            # Critical step: ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            output_path.write_text(pyi_content, encoding="utf-8")

            # Step 3: Update signatures (Snapshot current state)
~~~~~
~~~~~python.new
    def _generate_stubs(self, modules: List[ModuleDef], stub_path: Optional[str] = None) -> List[Path]:
        generated_files: List[Path] = []
        for module in modules:
            # Step 1: Hydrate IR with external docs (The "Stitching" process)
            self.doc_manager.apply_docs_to_module(module)

            # Step 2: Generate code
            pyi_content = self.generator.generate(module)
            
            # Determine Output Path
            if stub_path:
                # Centralized mode: map physical path to logical path inside stub_path
                logical_path = self._derive_logical_path(module.file_path)
                output_path = self.root_path / stub_path / logical_path.with_suffix(".pyi")
            else:
                # Colocated mode: generate next to source file
                output_path = self.root_path / Path(module.file_path).with_suffix(".pyi")

            # Critical step: ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            output_path.write_text(pyi_content, encoding="utf-8")

            # Step 3: Update signatures (Snapshot current state)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_from_config(self) -> List[Path]:
        config = load_config_from_path(self.root_path)

        # 1. Process source files
        files_to_scan = []
~~~~~
~~~~~python.new
    def run_from_config(self) -> List[Path]:
        config = load_config_from_path(self.root_path)

        # 1. Process source files
        files_to_scan = []
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        # 3. Combine and generate
        all_modules = source_modules + plugin_modules
        if not all_modules:
            bus.warning(L.warning.no_files_or_plugins_found)
            return []

        generated_files = self._generate_stubs(all_modules)

        if generated_files:
            bus.success(L.generate.run.complete, count=len(generated_files))

        return generated_files
~~~~~
~~~~~python.new
        # 3. Combine and generate
        all_modules = source_modules + plugin_modules
        if not all_modules:
            bus.warning(L.warning.no_files_or_plugins_found)
            return []

        generated_files = self._generate_stubs(all_modules, stub_path=config.stub_path)

        if generated_files:
            bus.success(L.generate.run.complete, count=len(generated_files))

        return generated_files
~~~~~

#### Acts 3: 更新 `stitcher-application` 引入 Optional
需要修复 `core.py` 的 import，添加 `Optional` 和 `Path`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
~~~~~
~~~~~python.new
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
~~~~~

#### Acts 4: 配置项目使用新的 Stub 模式
现在我们配置根项目的 `pyproject.toml` 来启用这个功能。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[tool.stitcher]
scan_paths = ["packages"]

[tool.pyright]
include = ["packages", "tests"]
~~~~~
~~~~~toml.new
[tool.stitcher]
scan_paths = ["packages"]
stub_path = "typings"

[tool.pyright]
include = ["packages", "tests"]
stubPath = "typings"
~~~~~

### 下一步建议
我们已经完成了代码和配置的修改。接下来的步骤是：
1.  **执行生成**: 运行 `stitcher generate`。由于我们是在开发环境中使用刚刚修改过的源码，可能需要确保运行的是最新的代码（如果是 editable install 应该没问题）。
2.  **验证**: 检查 `typings/` 目录是否生成了正确的结构（即 `needle/` 下包含 `__init__.pyi`, `pointer/...` 等）。
3.  **检查**: 再次运行 `pyrefly check` 看是否解决了 `missing-import` 错误。
