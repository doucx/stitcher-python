好的，我将根据重构路线图实施第一阶段的核心任务：**统一文件事务系统**。

这个计划的目标是将 `stitcher-common` 中已有的事务处理能力（`TransactionManager`）集成到 `stitcher-application` 的各个命令执行器（Runner）中，从而消除直接的文件系统写入操作，并为它们统一提供 `--dry-run` 的能力。

我将分步执行以下操作：

1.  **增强 `TransactionManager`**：为其增加 `dry-run` 模式和通过 `bus` 进行日志输出的能力。
2.  **适配 `TransformRunner`**：将 `strip` 和 `inject` 命令的写操作迁移到事务系统。
3.  **适配 `GenerateRunner`**：将 `generate` 命令（包括其依赖的 `StubPackageManager`）的写操作迁移到事务系统。
4.  **适配 `PumpRunner`**：将 `pump` 命令的写操作迁移到事务系统。
5.  **更新 `StitcherApp`**：作为顶层协调者，负责创建和提交事务，并向下传递 `dry_run` 状态。

## [WIP] feat(app): 将文件IO重构为统一的事务系统

### 用户需求

根据“Stitcher 重构路线图” v1.0 的 `1.1` 章节，需要将 `stitcher-application` 中的 `PumpRunner`, `GenerateRunner`, `TransformRunner` 等核心组件的文件写入操作，从直接调用 `path.write_text` 等方法，重构为使用 `stitcher-common` 中提供的 `TransactionManager`。

同时，需要增强 `TransactionManager` 以支持 `dry_run` 模式，并通过 `bus` 输出日志。

### 评论

这是一个关键的架构重构。它将分散、重复的文件 IO 逻辑集中到一个统一的、可测试的事务层。最大的收益是，所有使用此事务系统的命令（如 `generate`, `pump`, `strip`）将自动获得 `--dry-run` 的能力，极大地提升了工具的安全性和用户体验。这是从一系列孤立脚本向一个健壮平台演进的重要一步。

### 目标

1.  修改 `stitcher.common.transaction.TransactionManager`，增加 `dry_run` 功能和日志输出。
2.  修改 `TransformRunner`，使其 `run_strip` 和 `run_inject_batch` 方法使用 `TransactionManager`。
3.  修改 `GenerateRunner` 及其依赖 `StubPackageManager`，使其文件创建操作使用 `TransactionManager`。
4.  修改 `PumpRunner`，使其更新 YAML 文档、签名文件和剥离源代码的操作全部通过 `TransactionManager` 执行。
5.  修改 `StitcherApp` 中对应的 `run_*` 方法，以协调 `TransactionManager` 的生命周期（创建、传递、提交）。

### 基本原理

我们将采用**依赖注入**的方式。`StitcherApp` 中的各个 `run_*` 方法将负责创建并配置一个 `TransactionManager` 实例（根据 `dry_run` 参数）。然后，这个实例将被传递给相应的 Runner。Runner 内部不再直接写入文件，而是调用 `tm.add_write()`、`tm.add_delete_file()` 等方法来注册文件操作意图。最后，由 `StitcherApp` 统一调用 `tm.commit()` 来执行（或在 `dry_run` 模式下预览）所有操作。

对于 `SignatureManager` 和 `DocumentManager` 等服务，为了维持其抽象的纯粹性，我们将避免直接向它们注入 `TransactionManager`。取而代之的是，Runner 将向这些服务请求必要的数据（如文件路径和待写入内容），然后由 Runner 自己来调用 `TransactionManager` 注册操作。

### 标签

#intent/refine #flow/ready #priority/high
#comp/application #comp/common #concept/state #scope/core #scope/dx
#ai/instruct
#task/domain/architecture #task/object/transaction-system #task/action/integration #task/state/begin #task/status/active

---

### Script

#### Acts 1: 增强 TransactionManager

首先，我们为 `TransactionManager` 增加 `dry_run` 功能。在 `dry_run` 模式下，`commit` 方法将不会执行任何文件操作，而是通过全局 `bus` 打印出计划执行的操作列表。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/transaction.py
~~~~~
~~~~~python.old
from typing import List, Union, Protocol, Optional


class FileSystemAdapter(Protocol):
    def write_text(self, path: Path, content: str) -> None: ...
    def move(self, src: Path, dest: Path) -> None: ...
    def exists(self, path: Path) -> bool: ...
    def read_text(self, path: Path) -> str: ...
    def rmtree(self, path: Path) -> None: ...
    def remove(self, path: Path) -> None: ...
~~~~~
~~~~~python.new
from typing import List, Union, Protocol, Optional

from stitcher.common import bus
from needle.pointer import L


class FileSystemAdapter(Protocol):
    def write_text(self, path: Path, content: str) -> None: ...
    def move(self, src: Path, dest: Path) -> None: ...
    def exists(self, path: Path) -> bool: ...
    def read_text(self, path: Path) -> str: ...
    def rmtree(self, path: Path) -> None: ...
    def remove(self, path: Path) -> None: ...
~~~~~
~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/transaction.py
~~~~~
~~~~~python.old
class TransactionManager:
    def __init__(self, root_path: Path, fs: Optional[FileSystemAdapter] = None):
        self.root_path = root_path
        self.fs = fs or RealFileSystem()
        self._ops: List[FileOp] = []

    def add_write(self, path: Union[str, Path], content: str) -> None:
~~~~~
~~~~~python.new
class TransactionManager:
    def __init__(
        self,
        root_path: Path,
        fs: Optional[FileSystemAdapter] = None,
        dry_run: bool = False,
    ):
        self.root_path = root_path
        self.fs = fs or RealFileSystem()
        self.dry_run = dry_run
        self._ops: List[FileOp] = []

    def add_write(self, path: Union[str, Path], content: str) -> None:
~~~~~
~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/transaction.py
~~~~~
~~~~~python.old
    def commit(self) -> None:
        rebased_ops = self._rebase_ops(self._ops)
        for op in rebased_ops:
            op.execute(self.fs, self.root_path)
        self._ops.clear()

    def _rebase_ops(self, ops: List[FileOp]) -> List[FileOp]:
        rebased_ops = []
~~~~~
~~~~~python.new
    def commit(self) -> None:
        rebased_ops = self._rebase_ops(self._ops)
        if self.dry_run:
            if rebased_ops:
                bus.info(L.refactor.run.dry_run_header, count=len(rebased_ops))
                for op in rebased_ops:
                    bus.info(f"  {op.describe()}")
            else:
                bus.info(L.refactor.run.no_ops)
            self._ops.clear()
            return

        for op in rebased_ops:
            op.execute(self.fs, self.root_path)
        self._ops.clear()

    def _rebase_ops(self, ops: List[FileOp]) -> List[FileOp]:
        rebased_ops = []
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/refactor/run.json
~~~~~
~~~~~json
{
  "loading_graph": "🔍 Loading semantic graph for all project packages...",
  "planning": "📝 Planning refactoring operations...",
  "no_ops": "✅ No operations planned. Nothing to do.",
  "preview_header": "⚠️  The following {count} operations will be performed:",
  "dry_run_header": "DRY RUN: The following {count} operations would be performed:",
  "confirm": "Do you want to apply these changes?",
  "aborted": "🚫 Refactor aborted by user.",
  "applying": "🚀 Applying changes...",
  "success": "✨ Refactor complete. {count} operations performed."
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/refactor/run.json
~~~~~
~~~~~json
{
  "loading_graph": "🔍 正在为所有项目包加载语义图谱...",
  "planning": "📝 正在规划重构操作...",
  "no_ops": "✅ 未规划任何操作。无需执行任何操作。",
  "preview_header": "⚠️  即将执行以下 {count} 个操作:",
  "dry_run_header": "空运行：将执行以下 {count} 个操作：",
  "confirm": "您确定要应用这些变更吗？",
  "aborted": "🚫 用户已中止重构。",
  "applying": "🚀 正在应用变更...",
  "success": "✨ 重构完成。共执行了 {count} 个操作。"
}
~~~~~

#### Acts 2: 适配 TransformRunner

现在我们将 `TransformRunner` 的文件写入操作接入 `TransactionManager`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/transform.py
~~~~~
~~~~~python.old
from typing import List
from pathlib import Path

from stitcher.common import bus
from needle.pointer import L
from stitcher.spec import LanguageTransformerProtocol, ModuleDef
from stitcher.app.services import DocumentManager


class TransformRunner:
    def __init__(
        self,
        root_path: Path,
        doc_manager: DocumentManager,
        transformer: LanguageTransformerProtocol,
    ):
        self.root_path = root_path
        self.doc_manager = doc_manager
        self.transformer = transformer

    def run_strip(self, files: List[Path]) -> List[Path]:
        all_modified_files: List[Path] = []
        for file_path in files:
            try:
                original_content = file_path.read_text(encoding="utf-8")
                stripped_content = self.transformer.strip(
                    original_content, whitelist=None
                )
                if original_content != stripped_content:
                    file_path.write_text(stripped_content, encoding="utf-8")
                    all_modified_files.append(file_path)
                    relative_path = file_path.relative_to(self.root_path)
                    bus.success(L.strip.file.success, path=relative_path)
            except Exception as e:
                bus.error(L.error.generic, error=e)

        if all_modified_files:
            bus.success(L.strip.run.complete, count=len(all_modified_files))
        return all_modified_files

    def run_inject_batch(self, modules: List[ModuleDef]) -> List[Path]:
        modified_files: List[Path] = []
        total_docs_found = 0

        for module in modules:
            docs_ir = self.doc_manager.load_docs_for_module(module)
            if not docs_ir:
                continue
            total_docs_found += len(docs_ir)

            docs_str = {k: v.summary or "" for k, v in docs_ir.items()}
            source_path = self.root_path / module.file_path
            try:
                original_content = source_path.read_text(encoding="utf-8")
                injected_content = self.transformer.inject(original_content, docs_str)
                if original_content != injected_content:
                    source_path.write_text(injected_content, encoding="utf-8")
                    modified_files.append(source_path)
                    relative_path = source_path.relative_to(self.root_path)
                    bus.success(L.inject.file.success, path=relative_path)
            except Exception as e:
                bus.error(L.error.generic, error=e)

        return modified_files
~~~~~
~~~~~python.new
from typing import List
from pathlib import Path

from stitcher.common import bus
from needle.pointer import L
from stitcher.spec import LanguageTransformerProtocol, ModuleDef
from stitcher.app.services import DocumentManager
from stitcher.common.transaction import TransactionManager


class TransformRunner:
    def __init__(
        self,
        root_path: Path,
        doc_manager: DocumentManager,
        transformer: LanguageTransformerProtocol,
    ):
        self.root_path = root_path
        self.doc_manager = doc_manager
        self.transformer = transformer

    def run_strip(self, files: List[Path], tm: TransactionManager) -> List[Path]:
        all_modified_files: List[Path] = []
        for file_path in files:
            try:
                original_content = file_path.read_text(encoding="utf-8")
                stripped_content = self.transformer.strip(
                    original_content, whitelist=None
                )
                if original_content != stripped_content:
                    relative_path = file_path.relative_to(self.root_path)
                    tm.add_write(str(relative_path), stripped_content)
                    all_modified_files.append(file_path)
                    bus.success(L.strip.file.success, path=relative_path)
            except Exception as e:
                bus.error(L.error.generic, error=e)

        if all_modified_files:
            bus.success(L.strip.run.complete, count=len(all_modified_files))
        return all_modified_files

    def run_inject_batch(
        self, modules: List[ModuleDef], tm: TransactionManager
    ) -> List[Path]:
        modified_files: List[Path] = []
        total_docs_found = 0

        for module in modules:
            docs_ir = self.doc_manager.load_docs_for_module(module)
            if not docs_ir:
                continue
            total_docs_found += len(docs_ir)

            docs_str = {k: v.summary or "" for k, v in docs_ir.items()}
            source_path = self.root_path / module.file_path
            try:
                original_content = source_path.read_text(encoding="utf-8")
                injected_content = self.transformer.inject(original_content, docs_str)
                if original_content != injected_content:
                    relative_path = source_path.relative_to(self.root_path)
                    tm.add_write(str(relative_path), injected_content)
                    modified_files.append(source_path)
                    bus.success(L.inject.file.success, path=relative_path)
            except Exception as e:
                bus.error(L.error.generic, error=e)

        return modified_files
~~~~~

#### Acts 3: 适配 GenerateRunner 和 StubPackageManager

`GenerateRunner` 的逻辑更复杂，它涉及到创建目录和多个文件，同时还依赖 `StubPackageManager`。我们将一并改造它们。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
~~~~~
~~~~~python.old
from pathlib import Path
import tomli_w


class StubPackageManager:
    @staticmethod
    def _get_pep561_logical_path(logical_path: Path) -> Path:
        if not logical_path.parts:
            return logical_path

        namespace = logical_path.parts[0]
        rest_of_path = logical_path.parts[1:]
        # e.g. my_app/main.py -> my_app-stubs/main.py
        return Path(f"{namespace}-stubs", *rest_of_path)

    def scaffold(
        self, package_path: Path, source_project_name: str, package_namespace: str
    ) -> bool:
        config_path = package_path / "pyproject.toml"
        if config_path.exists():
            return False

        # Ensure root directory exists
        package_path.mkdir(parents=True, exist_ok=True)

        # Use the centralized logic to determine the stub source directory name
        stub_src_dirname = self._get_pep561_logical_path(
            Path(package_namespace)
        ).as_posix()
        (package_path / "src" / stub_src_dirname).mkdir(parents=True, exist_ok=True)

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
            "tool": {
                "hatch": {
                    "build": {
                        "targets": {
                            "wheel": {
                                # Essential for packaging .pyi files correctly under the namespace
                                "packages": [f"src/{stub_src_dirname}"]
                            }
                        }
                    }
                }
            },
        }
        with config_path.open("wb") as f:
            tomli_w.dump(pyproject_content, f)

        return True
~~~~~
~~~~~python.new
from pathlib import Path
import tomli_w

from stitcher.common.transaction import TransactionManager


class StubPackageManager:
    @staticmethod
    def _get_pep561_logical_path(logical_path: Path) -> Path:
        if not logical_path.parts:
            return logical_path

        namespace = logical_path.parts[0]
        rest_of_path = logical_path.parts[1:]
        # e.g. my_app/main.py -> my_app-stubs/main.py
        return Path(f"{namespace}-stubs", *rest_of_path)

    def scaffold(
        self,
        package_path: Path,
        source_project_name: str,
        package_namespace: str,
        tm: TransactionManager,
        root_path: Path,
    ) -> bool:
        config_path = package_path / "pyproject.toml"
        if config_path.exists():
            return False

        # Note: Directory creation is now handled implicitly by add_write.
        stub_src_dirname = self._get_pep561_logical_path(
            Path(package_namespace)
        ).as_posix()

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
            "tool": {
                "hatch": {
                    "build": {
                        "targets": {
                            "wheel": {
                                # Essential for packaging .pyi files correctly under the namespace
                                "packages": [f"src/{stub_src_dirname}"]
                            }
                        }
                    }
                }
            },
        }
        # Convert dict to TOML string
        toml_bytes = tomli_w.dumps(pyproject_content).encode("utf-8")

        # Add operation to transaction manager
        relative_config_path = config_path.relative_to(root_path)
        tm.add_write(str(relative_config_path), toml_bytes.decode("utf-8"))

        return True
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/generate.py
~~~~~
~~~~~python.old
from stitcher.app.services import (
    DocumentManager,
    StubPackageManager,
    ScannerService,
)


class GenerateRunner:
~~~~~
~~~~~python.new
from stitcher.app.services import (
    DocumentManager,
    StubPackageManager,
    ScannerService,
)
from stitcher.common.transaction import TransactionManager


class GenerateRunner:
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/generate.py
~~~~~
~~~~~python.old
    def _scaffold_stub_package(
        self, config: StitcherConfig, stub_base_name: Optional[str]
    ):
        if not config.stub_package or not stub_base_name:
            return
        pkg_path = self.root_path / config.stub_package
        package_namespace: str = ""
        for path_str in config.scan_paths:
            path_parts = Path(path_str).parts
            if path_parts and path_parts[-1] != "src":
                # This handles cases like 'src/my_app' where 'my_app' is the namespace.
                package_namespace = path_parts[-1]
                break

        if not package_namespace:
            # Fallback for when all scan_paths end in 'src'.
            # Derives namespace from the target name (e.g., 'stitcher-cli' -> 'stitcher').
            package_namespace = stub_base_name.split("-")[0]
        stub_pkg_name = f"{stub_base_name}-stubs"
        bus.info(L.generate.stub_pkg.scaffold, name=stub_pkg_name)
        created = self.stub_pkg_manager.scaffold(
            pkg_path, stub_base_name, package_namespace
        )
        if created:
            bus.success(L.generate.stub_pkg.success, name=stub_pkg_name)
        else:
            bus.info(L.generate.stub_pkg.exists, name=stub_pkg_name)

    def run_batch(
        self,
        modules: List[ModuleDef],
        config: StitcherConfig,
        project_name: Optional[str] = None,
    ) -> List[Path]:
        generated_files: List[Path] = []
        created_py_typed: set[Path] = set()

        if config.stub_package:
            stub_base_name = config.name if config.name != "default" else project_name
            self._scaffold_stub_package(config, stub_base_name)

        for module in modules:
            self.doc_manager.apply_docs_to_module(module)

            # Phase 1: Generate Skeleton
            skeleton_code = self.generator.generate(module)

            # Phase 2: Render Docs
            docs_map = self._render_docs_for_module(module)

            # Phase 3: Inject Docs
            final_content = self.transformer.inject(skeleton_code, docs_map)

            if config.stub_package:
                logical_path = self.scanner.derive_logical_path(module.file_path)
                stub_logical_path = self.stub_pkg_manager._get_pep561_logical_path(
                    logical_path
                )
                output_path = (
                    self.root_path
                    / config.stub_package
                    / "src"
                    / stub_logical_path.with_suffix(".pyi")
                )
                if stub_logical_path.parts:
                    top_level_pkg_dir = (
                        self.root_path
                        / config.stub_package
                        / "src"
                        / stub_logical_path.parts[0]
                    )
                    if top_level_pkg_dir not in created_py_typed:
                        top_level_pkg_dir.mkdir(parents=True, exist_ok=True)
                        (top_level_pkg_dir / "py.typed").touch(exist_ok=True)
                        created_py_typed.add(top_level_pkg_dir)
            elif config.stub_path:
                logical_path = self.scanner.derive_logical_path(module.file_path)
                output_path = (
                    self.root_path / config.stub_path / logical_path.with_suffix(".pyi")
                )
            else:
                output_path = self.root_path / Path(module.file_path).with_suffix(
                    ".pyi"
                )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if config.stub_package:
                src_root = self.root_path / config.stub_package / "src"
                current = output_path.parent
                while current != src_root and src_root in current.parents:
                    (current / "__init__.pyi").touch(exist_ok=True)
                    current = current.parent
            output_path.write_text(final_content, encoding="utf-8")
            relative_path = output_path.relative_to(self.root_path)
            bus.success(L.generate.file.success, path=relative_path)
            generated_files.append(output_path)
        return generated_files
~~~~~
~~~~~python.new
    def _scaffold_stub_package(
        self,
        config: StitcherConfig,
        stub_base_name: Optional[str],
        tm: TransactionManager,
    ):
        if not config.stub_package or not stub_base_name:
            return
        pkg_path = self.root_path / config.stub_package
        package_namespace: str = ""
        for path_str in config.scan_paths:
            path_parts = Path(path_str).parts
            if path_parts and path_parts[-1] != "src":
                # This handles cases like 'src/my_app' where 'my_app' is the namespace.
                package_namespace = path_parts[-1]
                break

        if not package_namespace:
            # Fallback for when all scan_paths end in 'src'.
            # Derives namespace from the target name (e.g., 'stitcher-cli' -> 'stitcher').
            package_namespace = stub_base_name.split("-")[0]
        stub_pkg_name = f"{stub_base_name}-stubs"
        bus.info(L.generate.stub_pkg.scaffold, name=stub_pkg_name)
        created = self.stub_pkg_manager.scaffold(
            pkg_path, stub_base_name, package_namespace, tm, self.root_path
        )
        if created:
            bus.success(L.generate.stub_pkg.success, name=stub_pkg_name)
        else:
            bus.info(L.generate.stub_pkg.exists, name=stub_pkg_name)

    def run_batch(
        self,
        modules: List[ModuleDef],
        config: StitcherConfig,
        tm: TransactionManager,
        project_name: Optional[str] = None,
    ) -> List[Path]:
        generated_files: List[Path] = []
        created_py_typed: set[Path] = set()

        if config.stub_package:
            stub_base_name = config.name if config.name != "default" else project_name
            self._scaffold_stub_package(config, stub_base_name, tm)

        for module in modules:
            self.doc_manager.apply_docs_to_module(module)

            # Phase 1: Generate Skeleton
            skeleton_code = self.generator.generate(module)

            # Phase 2: Render Docs
            docs_map = self._render_docs_for_module(module)

            # Phase 3: Inject Docs
            final_content = self.transformer.inject(skeleton_code, docs_map)

            if config.stub_package:
                logical_path = self.scanner.derive_logical_path(module.file_path)
                stub_logical_path = self.stub_pkg_manager._get_pep561_logical_path(
                    logical_path
                )
                output_path = (
                    self.root_path
                    / config.stub_package
                    / "src"
                    / stub_logical_path.with_suffix(".pyi")
                )
                if stub_logical_path.parts:
                    top_level_pkg_dir = (
                        self.root_path
                        / config.stub_package
                        / "src"
                        / stub_logical_path.parts[0]
                    )
                    if top_level_pkg_dir not in created_py_typed:
                        py_typed_path = top_level_pkg_dir / "py.typed"
                        tm.add_write(
                            str(py_typed_path.relative_to(self.root_path)), ""
                        )
                        created_py_typed.add(top_level_pkg_dir)
            elif config.stub_path:
                logical_path = self.scanner.derive_logical_path(module.file_path)
                output_path = (
                    self.root_path / config.stub_path / logical_path.with_suffix(".pyi")
                )
            else:
                output_path = self.root_path / Path(module.file_path).with_suffix(
                    ".pyi"
                )

            relative_path = output_path.relative_to(self.root_path)

            if config.stub_package:
                src_root = self.root_path / config.stub_package / "src"
                current = output_path.parent
                while current != src_root and src_root in current.parents:
                    init_path = current / "__init__.pyi"
                    tm.add_write(str(init_path.relative_to(self.root_path)), "")
                    current = current.parent

            tm.add_write(str(relative_path), final_content)
            bus.success(L.generate.file.success, path=relative_path)
            generated_files.append(output_path)
        return generated_files
~~~~~

#### Acts 4: 适配 PumpRunner

`PumpRunner` 的改造最为深入，因为它不仅直接写剥离后的代码，还通过 `DocManager` 和 `SignatureManager` 写入 YAML 和 JSON 文件。我们将修改 `PumpRunner` 以拦截这些操作并转交给 `TransactionManager`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python.old
    def _get_sig_path(self, module: ModuleDef) -> Path:
        rel_path = Path(module.file_path)
        return self.sig_root / rel_path.with_suffix(".json")
~~~~~
~~~~~python.new
    def get_sig_path(self, module: ModuleDef) -> Path:
        rel_path = Path(module.file_path)
        return self.sig_root / rel_path.with_suffix(".json")
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python.old
import copy
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

from stitcher.common import bus
from needle.pointer import L
~~~~~
~~~~~python.new
import copy
import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

from stitcher.common import bus
from needle.pointer import L
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python.old
    def run_batch(
        self,
        modules: List[ModuleDef],
        config: StitcherConfig,
        strip: bool = False,
        force: bool = False,
        reconcile: bool = False,
    ) -> PumpResult:
        all_conflicts: List[InteractionContext] = []
~~~~~
~~~~~python.new
    def run_batch(
        self,
        modules: List[ModuleDef],
        config: StitcherConfig,
        tm: TransactionManager,
        strip: bool = False,
        force: bool = False,
        reconcile: bool = False,
    ) -> PumpResult:
        all_conflicts: List[InteractionContext] = []
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python.old
            if not file_has_errors:
                if file_had_updates:
                    final_data = {
                        k: self.doc_manager._serialize_ir(v)
                        for k, v in new_yaml_docs.items()
                    }
                    module_path = self.root_path / module.file_path
                    doc_path = module_path.with_suffix(".stitcher.yaml")
                    self.doc_manager.adapter.save(doc_path, final_data)

                if signatures_need_save:
                    self.sig_manager.save_composite_hashes(module, new_hashes)

                if file_has_redundancy:
                    redundant_files_list.append(self.root_path / module.file_path)
~~~~~
~~~~~python.new
            if not file_has_errors:
                if file_had_updates:
                    final_data = {
                        k: self.doc_manager._serialize_ir(v)
                        for k, v in new_yaml_docs.items()
                    }
                    module_path = self.root_path / module.file_path
                    doc_path = module_path.with_suffix(".stitcher.yaml")
                    yaml_content = self.doc_manager.adapter.dump(final_data)
                    tm.add_write(
                        str(doc_path.relative_to(self.root_path)), yaml_content
                    )

                if signatures_need_save:
                    sig_path = self.sig_manager.get_sig_path(module)
                    if not new_hashes:
                        if sig_path.exists():
                            tm.add_delete_file(
                                str(sig_path.relative_to(self.root_path))
                            )
                    else:
                        serialized_data = {
                            fqn: fp.to_dict() for fqn, fp in new_hashes.items()
                        }
                        sig_content = json.dumps(
                            serialized_data, indent=2, sort_keys=True
                        )
                        tm.add_write(
                            str(sig_path.relative_to(self.root_path)), sig_content
                        )

                if file_has_redundancy:
                    redundant_files_list.append(self.root_path / module.file_path)
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python.old
                    stripped_content = self.transformer.strip(
                        original_content, whitelist=whitelist
                    )
                    if original_content != stripped_content:
                        source_path.write_text(stripped_content, "utf-8")
                        bus.success(
                            L.strip.file.success,
                            path=source_path.relative_to(self.root_path),
                        )
                        total_stripped_files += 1
                except Exception as e:
~~~~~
~~~~~python.new
                    stripped_content = self.transformer.strip(
                        original_content, whitelist=whitelist
                    )
                    relative_path = source_path.relative_to(self.root_path)
                    if original_content != stripped_content:
                        tm.add_write(str(relative_path), stripped_content)
                        bus.success(
                            L.strip.file.success,
                            path=relative_path,
                        )
                        total_stripped_files += 1
                except Exception as e:
~~~~~

#### Acts 5: 适配 StitcherApp

最后，我们修改 `StitcherApp`，让它来管理 `TransactionManager` 的创建和提交，并为相应的 `run_*` 方法添加 `dry_run` 参数。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from .runners import (
    CheckRunner,
    GenerateRunner,
    InitRunner,
    PumpRunner,
    TransformRunner,
    CoverageRunner,
    RefactorRunner,
)
from typing import Callable
from .types import PumpResult, FileCheckResult, CoverageResult
from stitcher.adapter.python.docstring import (
~~~~~
~~~~~python.new
from .runners import (
    CheckRunner,
    GenerateRunner,
    InitRunner,
    PumpRunner,
    TransformRunner,
    CoverageRunner,
    RefactorRunner,
)
from stitcher.common.transaction import TransactionManager
from typing import Callable
from .types import PumpResult, FileCheckResult, CoverageResult
from stitcher.adapter.python.docstring import (
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_from_config(self) -> List[Path]:
        configs, project_name = self._load_configs()
        all_generated: List[Path] = []
        found_any = False

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue
            found_any = True

            paths = self.generate_runner.run_batch(modules, config, project_name)
            all_generated.extend(paths)

        if not found_any and len(configs) == 1:
            bus.warning(L.warning.no_files_or_plugins_found)

        if all_generated:
            bus.success(L.generate.run.complete, count=len(all_generated))
        return all_generated
~~~~~
~~~~~python.new
    def run_from_config(self, dry_run: bool = False) -> List[Path]:
        configs, project_name = self._load_configs()
        all_generated: List[Path] = []
        found_any = False
        tm = TransactionManager(self.root_path, dry_run=dry_run)

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue
            found_any = True

            paths = self.generate_runner.run_batch(modules, config, tm, project_name)
            all_generated.extend(paths)

        if not found_any and len(configs) == 1 and not tm.dry_run:
            bus.warning(L.warning.no_files_or_plugins_found)

        tm.commit()

        if all_generated and not tm.dry_run:
            bus.success(L.generate.run.complete, count=len(all_generated))
        return all_generated
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_pump(
        self, strip: bool = False, force: bool = False, reconcile: bool = False
    ) -> PumpResult:
        bus.info(L.pump.run.start)
        configs, _ = self._load_configs()

        global_success = True
        all_redundant: List[Path] = []

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue

            result = self.pump_runner.run_batch(
                modules, config, strip, force, reconcile
            )
            if not result.success:
                global_success = False
            all_redundant.extend(result.redundant_files)

        return PumpResult(success=global_success, redundant_files=all_redundant)
~~~~~
~~~~~python.new
    def run_pump(
        self,
        strip: bool = False,
        force: bool = False,
        reconcile: bool = False,
        dry_run: bool = False,
    ) -> PumpResult:
        bus.info(L.pump.run.start)
        configs, _ = self._load_configs()
        tm = TransactionManager(self.root_path, dry_run=dry_run)

        global_success = True
        all_redundant: List[Path] = []

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue

            result = self.pump_runner.run_batch(
                modules, config, tm, strip, force, reconcile
            )
            if not result.success:
                global_success = False
            all_redundant.extend(result.redundant_files)

        tm.commit()
        return PumpResult(success=global_success, redundant_files=all_redundant)
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_strip(self, files: Optional[List[Path]] = None) -> List[Path]:
        files_to_process = []
        if files:
            files_to_process = files
        else:
            configs, _ = self._load_configs()
            for config in configs:
                files_to_process.extend(self.scanner.get_files_from_config(config))
            files_to_process = sorted(list(set(files_to_process)))

        return self.transform_runner.run_strip(files_to_process)

    def run_inject(self) -> List[Path]:
        configs, _ = self._load_configs()
        all_modified: List[Path] = []
        found_any_docs = False

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue

            # We assume if modules exist, docs might exist.
            # Transform runner will check doc existence.
            modified = self.transform_runner.run_inject_batch(modules)
            if modified:
                found_any_docs = True
            all_modified.extend(modified)

        if all_modified:
            bus.success(L.inject.run.complete, count=len(all_modified))
        elif not found_any_docs:
            bus.info(L.inject.no_docs_found)

        return all_modified
~~~~~
~~~~~python.new
    def run_strip(
        self, files: Optional[List[Path]] = None, dry_run: bool = False
    ) -> List[Path]:
        files_to_process = []
        if files:
            files_to_process = files
        else:
            configs, _ = self._load_configs()
            for config in configs:
                files_to_process.extend(self.scanner.get_files_from_config(config))
            files_to_process = sorted(list(set(files_to_process)))

        tm = TransactionManager(self.root_path, dry_run=dry_run)
        modified = self.transform_runner.run_strip(files_to_process, tm)
        tm.commit()
        return modified

    def run_inject(self, dry_run: bool = False) -> List[Path]:
        configs, _ = self._load_configs()
        all_modified: List[Path] = []
        found_any_docs = False
        tm = TransactionManager(self.root_path, dry_run=dry_run)

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue

            # We assume if modules exist, docs might exist.
            # Transform runner will check doc existence.
            modified = self.transform_runner.run_inject_batch(modules, tm)
            if modified:
                found_any_docs = True
            all_modified.extend(modified)

        tm.commit()

        if all_modified and not tm.dry_run:
            bus.success(L.inject.run.complete, count=len(all_modified))
        elif not found_any_docs and not tm.dry_run:
            bus.info(L.inject.no_docs_found)

        return all_modified
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python.old
    def save_composite_hashes(
        self, module: ModuleDef, hashes: Dict[str, Fingerprint]
    ) -> None:
        if not hashes:
            sig_path = self._get_sig_path(module)
            if sig_path.exists():
                sig_path.unlink()
            return

        sig_path = self._get_sig_path(module)
        sig_path.parent.mkdir(parents=True, exist_ok=True)
~~~~~
~~~~~python.new
    def save_composite_hashes(
        self, module: ModuleDef, hashes: Dict[str, Fingerprint]
    ) -> None:
        if not hashes:
            sig_path = self.get_sig_path(module)
            if sig_path.exists():
                sig_path.unlink()
            return

        sig_path = self.get_sig_path(module)
        sig_path.parent.mkdir(parents=True, exist_ok=True)
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python.old
    def load_composite_hashes(self, module: ModuleDef) -> Dict[str, Fingerprint]:
        sig_path = self._get_sig_path(module)
        if not sig_path.exists():
            return {}
~~~~~
~~~~~python.new
    def load_composite_hashes(self, module: ModuleDef) -> Dict[str, Fingerprint]:
        sig_path = self.get_sig_path(module)
        if not sig_path.exists():
            return {}
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python.old
    def reformat_hashes_for_module(self, module: ModuleDef) -> bool:
        sig_path = self._get_sig_path(module)
        if not sig_path.exists():
            return False
~~~~~
~~~~~python.new
    def reformat_hashes_for_module(self, module: ModuleDef) -> bool:
        sig_path = self.get_sig_path(module)
        if not sig_path.exists():
            return False
~~~~~

### 下一步建议

我们已经成功地将核心命令执行器的文件 IO 操作统一到了事务系统中。下一步，我们应该利用这个新能力：

1.  **暴露 `--dry-run` 标志**：在 `stitcher-cli` 中为 `generate`、`pump`、`strip` 和 `inject` 命令添加 `--dry-run` 命令行选项，并将其状态传递给 `StitcherApp` 中对应的 `run_*` 方法。
2.  **统一 `check` 命令**：`CheckRunner` 在自动修复（`--force-relink`, `--reconcile`）时也会写入文件。我们应该以同样的方式重构 `CheckRunner`，使其也使用 `TransactionManager`。
3.  **编写集成测试**：为新的 `--dry-run` 功能编写集成测试，断言在 `dry-run` 模式下文件系统**没有**被修改，并且 `bus` 收到了正确的预览日志。

如果你同意，我将继续为 CLI 添加 `--dry-run` 标志。
