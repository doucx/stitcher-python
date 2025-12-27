好的，我将分析这项提案并开始实施。这是一个非常有价值的改进，它将 `Stitcher` 从一个项目内的工具提升为一个符合 Python 官方标准的、可独立分发的类型生态系统协调者，能彻底解决 Monorepo 架构中静态分析工具链的配置难题。

我将遵循您提供的目标和基本原理，分步骤完成本次重构。

## [WIP] feat(core): 实现 PEP 561 自动化存根包生成机制

### 用户需求
根据 [RFC-001](提案：基于 PEP 561 的 Stitcher 自动化存根包生成机制 (RFC-001))，实现一个“存根包 (Stub Package)”生成模式。当用户在配置中指定 `stub_package` 路径时，Stitcher 应自动创建一个符合 PEP 561 规范的独立 Python 包，并将所有生成的 `.pyi` 文件输出到该包的 `src` 目录下，从而为下游工具链提供零配置的类型解析能力。

### 评论
这是一项关键的架构升级。它将 Stitcher 的核心价值——“静态透明性”——从仅限于 IDE 内部扩展到了整个 Python 工具生态（如 MyPy, Pyright CLI, Pyrefly 等），使其成为解决复杂项目静态分析痛点的“终极武器”。通过引入专门的 `StubPackageManager`，我们将包管理的复杂性与核心生成逻辑解耦，确保了实现的可维护性。

### 目标
1.  修改 `StitcherConfig` 数据模型，增加 `stub_package` 配置项，并优化配置加载函数以获取项目名称。
2.  在 `stitcher-application` 中创建一个新的 `StubPackageManager` 服务，专门负责搭建存根包的目录结构和元数据文件（`pyproject.toml`）。
3.  更新 `StitcherApp` 的核心生成流程（`_generate_stubs`），使其能够根据 `stub_package` 配置将 `.pyi` 文件和 `py.typed` 标记输出到正确的位置。
4.  为新的脚手架流程添加清晰的用户反馈消息。

### 基本原理
本次实现的核心是在 `StitcherApp` 中引入对 `stub_package` 配置的判断。如果该配置存在，`run_from_config` 流程会首先调用 `StubPackageManager` 来确保存根包的基础结构存在。随后，核心的 `_generate_stubs` 方法会将输出根目录动态切换到存根包的 `src` 目录。通过复用现有的 `_derive_logical_path` 逻辑，我们可以将来自不同物理位置的源文件正确地映射到存根包内的逻辑路径，同时自动在顶层包目录中创建 PEP 561 所需的 `py.typed` 标记文件。

### 标签
#intent/build #flow/ready #priority/high #comp/application #comp/config #concept/state #scope/api #scope/dx #ai/instruct #task/domain/stubs #task/object/pep561-package #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 更新配置层 (`stitcher-config`)

首先，我们扩展 `StitcherConfig` 数据类以包含 `stub_package` 选项，并增强 `load_config_from_path` 函数，使其能同时返回项目配置和项目名称，为后续的存根包命名提供依据。

~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python.old
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Any, Dict, Optional

if sys.version_info < (3, 11):
~~~~~
~~~~~python.new
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Any, Dict, Optional, Tuple

if sys.version_info < (3, 11):
~~~~~
~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python.old
@dataclass
class StitcherConfig:
    scan_paths: List[str] = field(default_factory=list)
    plugins: Dict[str, str] = field(default_factory=dict)
    stub_path: Optional[str] = None
~~~~~
~~~~~python.new
@dataclass
class StitcherConfig:
    scan_paths: List[str] = field(default_factory=list)
    plugins: Dict[str, str] = field(default_factory=dict)
    stub_path: Optional[str] = None
    stub_package: Optional[str] = None
~~~~~
~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python.old
def load_config_from_path(search_path: Path) -> StitcherConfig:
    plugins = _find_plugins(search_path)

    try:
        config_path = _find_pyproject_toml(search_path)
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        stitcher_data: Dict[str, Any] = data.get("tool", {}).get("stitcher", {})
    except FileNotFoundError:
        # If no root config file, still return discovered plugins with default scan_paths
        return StitcherConfig(plugins=plugins)

    # Create config with data from file, falling back to defaults.
    return StitcherConfig(
        scan_paths=stitcher_data.get("scan_paths", []),
        plugins=plugins,
        stub_path=stitcher_data.get("stub_path"),
    )
~~~~~
~~~~~python.new
def load_config_from_path(search_path: Path) -> Tuple[StitcherConfig, Optional[str]]:
    plugins = _find_plugins(search_path)
    project_name: Optional[str] = None

    try:
        config_path = _find_pyproject_toml(search_path)
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        project_name = data.get("project", {}).get("name")
        stitcher_data: Dict[str, Any] = data.get("tool", {}).get("stitcher", {})

    except FileNotFoundError:
        # If no root config file, still return discovered plugins with default scan_paths
        return StitcherConfig(plugins=plugins), None

    # Create config with data from file, falling back to defaults.
    config = StitcherConfig(
        scan_paths=stitcher_data.get("scan_paths", []),
        plugins=plugins,
        stub_path=stitcher_data.get("stub_path"),
        stub_package=stitcher_data.get("stub_package"),
    )
    return config, project_name
~~~~~

#### Acts 2: 添加 CLI 反馈消息 (`stitcher-common`)

为了在生成存根包时提供清晰的反馈，我们预先定义相关的国际化消息。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/generate.json
~~~~~
~~~~~json
{
    "generate.file.success": "✅ Generated stub: {path}",
    "generate.run.complete": "✨ Generation complete. {count} files created.",
    "generate.stub_pkg.scaffold": "Scaffolding stub package '{name}'...",
    "generate.stub_pkg.exists": "ℹ️  Stub package '{name}' already exists, skipping.",
    "generate.stub_pkg.success": "✅ Created stub package '{name}'."
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/generate.json
~~~~~
~~~~~json
{
    "generate.file.success": "✅ 已生成存根: {path}",
    "generate.run.complete": "✨ 生成完成。{count} 个文件已创建。",
    "generate.stub_pkg.scaffold": "正在搭建存根包 '{name}'...",
    "generate.stub_pkg.exists": "ℹ️  存根包 '{name}' 已存在，跳过创建。",
    "generate.stub_pkg.success": "✅ 已创建存根包 '{name}'。"
}
~~~~~

#### Acts 3: 实现存根包管理器 (`stitcher-application`)

我们现在创建 `StubPackageManager`，它封装了创建 Python 包结构和元数据的逻辑。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
~~~~~
~~~~~python
from pathlib import Path
import tomli_w


class StubPackageManager:
    """Manages the scaffolding of a PEP 561 stub package."""

    def scaffold(self, package_path: Path, source_project_name: str) -> bool:
        """
        Creates the directory structure and pyproject.toml for a stub package.

        Returns:
            bool: True if the package was created, False if it already existed.
        """
        config_path = package_path / "pyproject.toml"
        if config_path.exists():
            return False

        # Ensure root directory exists
        package_path.mkdir(parents=True, exist_ok=True)
        (package_path / "src").mkdir(exist_ok=True)

        # Create pyproject.toml
        pyproject_content = {
            "build-system": {
                "requires": ["hatchling"],
                "build-backend": "hatchling.build",
            },
            "project": {
                "name": f"{source_project_name}-stubs",
                "version": "0.1.0",  # Placeholder version
                "description": f"PEP 561 type stubs for {source_project_name}",
            },
        }
        with config_path.open("w", encoding="utf-8") as f:
            tomli_w.dump(pyproject_content, f)

        return True
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/__init__.py
~~~~~
~~~~~python.old
from .doc_manager import DocumentManager
from .signature_manager import SignatureManager

__all__ = ["DocumentManager", "SignatureManager"]
~~~~~
~~~~~python.new
from .doc_manager import DocumentManager
from .signature_manager import SignatureManager
from .stub_package_manager import StubPackageManager

__all__ = ["DocumentManager", "SignatureManager", "StubPackageManager"]
~~~~~

#### Acts 4: 整合核心应用逻辑 (`stitcher-application`)

最后，我们将所有部分整合到 `StitcherApp` 中。这包括：初始化新的管理器，更新所有 `load_config_from_path` 的调用点，实现脚手架逻辑，并修改 `_generate_stubs` 方法以支持新的输出模式。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from stitcher.io import StubGenerator
from stitcher.spec import ModuleDef
from stitcher.common import bus
from needle.pointer import L
from stitcher.config import load_config_from_path
from stitcher.app.services import DocumentManager, SignatureManager


class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.generator = StubGenerator()
        self.doc_manager = DocumentManager(root_path)
        self.sig_manager = SignatureManager(root_path)
~~~~~
~~~~~python.new
from stitcher.io import StubGenerator
from stitcher.spec import ModuleDef
from stitcher.common import bus
from needle.pointer import L
from stitcher.config import load_config_from_path, StitcherConfig
from stitcher.app.services import (
    DocumentManager,
    SignatureManager,
    StubPackageManager,
)


class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.generator = StubGenerator()
        self.doc_manager = DocumentManager(root_path)
        self.sig_manager = SignatureManager(root_path)
        self.stub_pkg_manager = StubPackageManager()
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
    def _scaffold_stub_package(
        self, config: StitcherConfig, project_name: Optional[str]
    ):
        if not config.stub_package or not project_name:
            return

        pkg_path = self.root_path / config.stub_package
        stub_pkg_name = f"{project_name}-stubs"
        bus.info(L.generate.stub_pkg.scaffold, name=stub_pkg_name)
        created = self.stub_pkg_manager.scaffold(pkg_path, project_name)
        if created:
            bus.success(L.generate.stub_pkg.success, name=stub_pkg_name)
        else:
            bus.info(L.generate.stub_pkg.exists, name=stub_pkg_name)

    def _generate_stubs(
        self, modules: List[ModuleDef], config: StitcherConfig
    ) -> List[Path]:
        generated_files: List[Path] = []
        created_py_typed: set[Path] = set()

        for module in modules:
            # Step 1: Hydrate IR with external docs (The "Stitching" process)
            self.doc_manager.apply_docs_to_module(module)

            # Step 2: Generate code
            pyi_content = self.generator.generate(module)

            # Determine Output Path
            if config.stub_package:
                # Stub Package mode
                logical_path = self._derive_logical_path(module.file_path)
                output_path = (
                    self.root_path
                    / config.stub_package
                    / "src"
                    / logical_path.with_suffix(".pyi")
                )

                # Create py.typed marker file in top-level package dir
                if logical_path.parts:
                    top_level_pkg_dir = (
                        self.root_path
                        / config.stub_package
                        / "src"
                        / logical_path.parts[0]
                    )
                    if top_level_pkg_dir not in created_py_typed:
                        top_level_pkg_dir.mkdir(exist_ok=True)
                        (top_level_pkg_dir / "py.typed").touch(exist_ok=True)
                        created_py_typed.add(top_level_pkg_dir)

            elif config.stub_path:
                # Centralized stub_path mode
                logical_path = self._derive_logical_path(module.file_path)
                output_path = (
                    self.root_path / config.stub_path / logical_path.with_suffix(".pyi")
                )
            else:
                # Colocated mode
                output_path = self.root_path / Path(module.file_path).with_suffix(
                    ".pyi"
                )
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
        for scan_path_str in config.scan_paths:
            scan_path = self.root_path / scan_path_str
            if scan_path.is_dir():
                files_to_scan.extend(scan_path.rglob("*.py"))
            elif scan_path.is_file():
                files_to_scan.append(scan_path)

        unique_files = sorted(list(set(files_to_scan)))
        source_modules = self._scan_files(unique_files)

        # 2. Process plugins
        plugin_modules = self._process_plugins(config.plugins)

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
~~~~~python.new
    def run_from_config(self) -> List[Path]:
        config, project_name = load_config_from_path(self.root_path)

        # 0. Scaffold stub package if configured
        if config.stub_package:
            self._scaffold_stub_package(config, project_name)

        # 1. Process source files
        files_to_scan = []
        for scan_path_str in config.scan_paths:
            scan_path = self.root_path / scan_path_str
            if scan_path.is_dir():
                files_to_scan.extend(scan_path.rglob("*.py"))
            elif scan_path.is_file():
                files_to_scan.append(scan_path)

        unique_files = sorted(list(set(files_to_scan)))
        source_modules = self._scan_files(unique_files)

        # 2. Process plugins
        plugin_modules = self._process_plugins(config.plugins)

        # 3. Combine and generate
        all_modules = source_modules + plugin_modules
        if not all_modules:
            bus.warning(L.warning.no_files_or_plugins_found)
            return []

        generated_files = self._generate_stubs(all_modules, config)

        if generated_files:
            bus.success(L.generate.run.complete, count=len(generated_files))

        return generated_files
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_init(self) -> List[Path]:
        config = load_config_from_path(self.root_path)

        # 1. Discover and scan source files
        files_to_scan = []
~~~~~
~~~~~python.new
    def run_init(self) -> List[Path]:
        config, _ = load_config_from_path(self.root_path)

        # 1. Discover and scan source files
        files_to_scan = []
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_check(self) -> bool:
        config = load_config_from_path(self.root_path)

        files_to_scan = []
        for scan_path_str in config.scan_paths:
~~~~~
~~~~~python.new
    def run_check(self) -> bool:
        config, _ = load_config_from_path(self.root_path)

        files_to_scan = []
        for scan_path_str in config.scan_paths:
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_hydrate(
        self, strip: bool = False, force: bool = False, reconcile: bool = False
    ) -> bool:
        bus.info(L.hydrate.run.start)
        config = load_config_from_path(self.root_path)
        modules = self._scan_files(self._get_files_from_config(config))

        if not modules:
~~~~~
~~~~~python.new
    def run_hydrate(
        self, strip: bool = False, force: bool = False, reconcile: bool = False
    ) -> bool:
        bus.info(L.hydrate.run.start)
        config, _ = load_config_from_path(self.root_path)
        modules = self._scan_files(self._get_files_from_config(config))

        if not modules:
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_strip(self) -> List[Path]:
        config = load_config_from_path(self.root_path)
        files_to_scan = self._get_files_from_config(config)
        modified_files: List[Path] = []
~~~~~
~~~~~python.new
    def run_strip(self) -> List[Path]:
        config, _ = load_config_from_path(self.root_path)
        files_to_scan = self._get_files_from_config(config)
        modified_files: List[Path] = []
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_eject(self) -> List[Path]:
        config = load_config_from_path(self.root_path)
        modules = self._scan_files(self._get_files_from_config(config))
        modified_files: List[Path] = []
~~~~~
~~~~~python.new
    def run_eject(self) -> List[Path]:
        config, _ = load_config_from_path(self.root_path)
        modules = self._scan_files(self._get_files_from_config(config))
        modified_files: List[Path] = []
~~~~~

### 下一步建议
我们已经完成了核心逻辑的实现。下一步，我建议：

1.  **添加集成测试**：在 `tests/integration` 目录下创建一个新的测试文件，专门验证 `stub_package` 模式。测试用例应覆盖：
    *   存根包的 `pyproject.toml` 是否被正确创建。
    *   `.pyi` 文件是否生成在 `src` 目录下。
    *   `py.typed` 文件是否在正确的顶层包内被创建。
2.  **更新文档**：修改项目 `README.md` 或相关文档，介绍新的 `stub_package` 配置项及其用法。
3.  **调整 `pyproject.toml`**：在根 `pyproject.toml` 的 `[tool.stitcher]` 部分，可以将 `stub_path` 替换为 `stub_package`，以在本项目中启用新特性进行自举（dogfooding）。例如：`stub_package = "packages/stitcher-stubs"`。

如果您同意，我将开始编写测试用例。
