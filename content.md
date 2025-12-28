好的，我们来开始实施“签名与文档哈希校验状态机模型”提案。

这个提案的核心是增强 `stitcher check` 的能力，使其能够精确区分代码与文档之间的四种不同步状态，并提供明确的修复指令。这将从根本上提升代码库的健康度和开发体验。

我将分步实施这个计划：
1.  **改造数据层**：更新 `SignatureManager` 和 `DocumentManager`，使其能够处理和存储签名哈希与文档哈希。
2.  **更新接口层**：修改 CLI，引入 `--reconcile` 和 `--force-relink` 这两个意图明确的新标志。
3.  **实现核心逻辑**：重写 `StitcherApp` 中的 `check` 相关方法，实现提案中定义的状态机。
4.  **同步相关命令**：确保 `init` 和 `hydrate` 命令能正确地初始化和更新新的哈希记录。

这是一个相对复杂的重构，我会确保每一步都清晰且专注。

## [WIP] feat: 实现签名与文档哈希校验状态机

### 用户需求
根据“签名与文档哈希校验状态机模型”提案，需要重构 `stitcher check` 命令的核心逻辑。新的实现必须能够：
1.  同时追踪代码（函数签名）和文档（YAML内容）的哈希值。
2.  基于这两个哈希与存储基线的对比，识别出“同步”、“文档改进”、“签名漂移”和“协同演进”四种状态。
3.  为状态 3 和 4 提供 `--force-relink` 和 `--reconcile` 标志进行修复。
4.  自动处理状态 2（文档改进）。

### 评论
这是一个关键的架构升级。将简单的指纹校验升级为确定性状态机，能极大地提升工具的健壮性和用户体验。它将 `stitcher` 从一个简单的检查工具，转变为一个能够理解开发者意图并提供智能引导的诊断工具，是项目走向成熟的重要一步。

### 目标
1.  修改 `SignatureManager`，使其存储结构能同时容纳 `signature_hash` 和 `document_hash`。
2.  为 `DocumentManager` 添加计算文档哈希的能力。
3.  在 `stitcher-cli` 中，用 `--reconcile` 和 `--force-relink` 替换掉旧的 `--update-signatures` 标志。
4.  在 `StitcherApp` 中彻底重写 `_analyze_file` 和 `run_check` 方法，以实现完整的四状态机逻辑。
5.  更新 `run_init` 和 `run_hydrate` 命令，确保它们能与新的哈希状态管理机制正确交互。

### 基本原理
我们将对现有架构进行一次垂直重构：
1.  **数据模型扩展**：`.stitcher/signatures/*.json` 文件将从存储单一哈希字符串 `(FQN -> hash)` 变为存储一个包含两个键的字典 `(FQN -> {"signature_hash": ..., "document_hash": ...})`。
2.  **服务层能力增强**：`SignatureManager` 将负责读写这个新结构。`DocumentManager` 将新增一个 `compute_document_hashes` 方法，负责按 FQN 计算其内容的哈希。
3.  **应用层逻辑重构**：`StitcherApp` 的 `_analyze_file` 方法将成为状态机的核心实现。它会获取“当前签名哈希”、“当前文档哈希”、“已存签名哈希”和“已存文档哈希”这四个值，并通过比较它们来确定当前 FQN 所处的状态，然后根据状态和用户传入的 CLI 标志（`--reconcile`, `--force-relink`）来决定是报告错误、自动修复还是强制更新。

### 标签
#intent/refine #flow/ready #priority/high #comp/cli #comp/application #concept/state #scope/core #ai/instruct #task/domain/validation #task/object/state-machine #task/action/implementation #task/state/begin

---
### Script

#### Acts 1: 扩展 `SignatureManager` 以管理复合哈希

我们将重构 `SignatureManager`，使其能够处理包含签名和文档两种哈希的复合数据结构。这包括重命名方法以明确其职责，并更新其内部逻辑以适应新的数据模型。旧的 `check_signatures` 方法将被移除，因为校验逻辑将上移到应用层。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python.old
import json
from pathlib import Path
from typing import Dict

from stitcher.spec import ModuleDef


class SignatureManager:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.sig_root = root_path / ".stitcher" / "signatures"

    def _get_sig_path(self, module: ModuleDef) -> Path:
        # module.file_path is relative to project root
        rel_path = Path(module.file_path)
        return self.sig_root / rel_path.with_suffix(".json")

    def compute_module_fingerprints(self, module: ModuleDef) -> Dict[str, str]:
        fingerprints = {}

        # 1. Functions
        for func in module.functions:
            fingerprints[func.name] = func.compute_fingerprint()

        # 2. Classes and Methods
        for cls in module.classes:
            # We could fingerprint the class itself (bases etc.), but for now
            # let's focus on methods as they map to docstrings.
            for method in cls.methods:
                fqn = f"{cls.name}.{method.name}"
                fingerprints[fqn] = method.compute_fingerprint()

        return fingerprints

    def save_signatures(self, module: ModuleDef) -> None:
        fingerprints = self.compute_module_fingerprints(module)
        if not fingerprints:
            # If no fingerprints (e.g. empty file), we might want to clean up any old file
            # But for now, just returning is safer.
            return

        sig_path = self._get_sig_path(module)
        # Ensure the directory exists (redundant check but safe)
        if not sig_path.parent.exists():
            sig_path.parent.mkdir(parents=True, exist_ok=True)

        with sig_path.open("w", encoding="utf-8") as f:
            json.dump(fingerprints, f, indent=2, sort_keys=True)

    def load_signatures(self, module: ModuleDef) -> Dict[str, str]:
        sig_path = self._get_sig_path(module)
        if not sig_path.exists():
            return {}

        try:
            with sig_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def check_signatures(self, module: ModuleDef) -> Dict[str, str]:
        current_sigs = self.compute_module_fingerprints(module)
        stored_sigs = self.load_signatures(module)

        issues = {}

        for fqn, current_hash in current_sigs.items():
            stored_hash = stored_sigs.get(fqn)

            # If stored_hash is None, it's a new function (covered by 'missing' check in doc_manager).
            # We only care if it EXISTS in storage but differs.
            if stored_hash and stored_hash != current_hash:
                issues[fqn] = "signature_mismatch"

        return issues
~~~~~
~~~~~python.new
import json
from pathlib import Path
from typing import Dict, Any

from stitcher.spec import ModuleDef


class SignatureManager:
    """Manages the persistence of composite hashes (signature and document)."""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.sig_root = root_path / ".stitcher" / "signatures"

    def _get_sig_path(self, module: ModuleDef) -> Path:
        rel_path = Path(module.file_path)
        return self.sig_root / rel_path.with_suffix(".json")

    def compute_signature_hashes(self, module: ModuleDef) -> Dict[str, str]:
        """Computes signature hashes for all addressable functions/methods."""
        hashes = {}
        for func in module.functions:
            hashes[func.name] = func.compute_fingerprint()
        for cls in module.classes:
            for method in cls.methods:
                fqn = f"{cls.name}.{method.name}"
                hashes[fqn] = method.compute_fingerprint()
        return hashes

    def save_hashes(self, module: ModuleDef, hashes: Dict[str, Any]) -> None:
        """Saves the composite hash map for a module."""
        if not hashes:
            # If no hashes, we might want to clean up any old file.
            # For now, let's remove it to avoid stale state.
            sig_path = self._get_sig_path(module)
            if sig_path.exists():
                sig_path.unlink()
            return

        sig_path = self._get_sig_path(module)
        sig_path.parent.mkdir(parents=True, exist_ok=True)

        with sig_path.open("w", encoding="utf-8") as f:
            json.dump(hashes, f, indent=2, sort_keys=True)

    def load_hashes(self, module: ModuleDef) -> Dict[str, Any]:
        """Loads the composite hash map for a module."""
        sig_path = self._get_sig_path(module)
        if not sig_path.exists():
            return {}
        try:
            with sig_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}
~~~~~

#### Acts 2: 增强 `DocumentManager` 以计算文档哈希

现在，为 `DocumentManager` 添加一个新方法，使其能够计算 YAML 文件中每个 FQN 对应文档内容的哈希值。这是实现状态机所需的四大核心数据之一。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
from pathlib import Path
from typing import Dict, Optional, Any

from stitcher.spec import ModuleDef, ClassDef, FunctionDef
from stitcher.io import DocumentAdapter, YamlAdapter


class DocumentManager:
~~~~~
~~~~~python.new
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any

from stitcher.spec import ModuleDef, ClassDef, FunctionDef
from stitcher.io import DocumentAdapter, YamlAdapter


class DocumentManager:
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
        return keys
~~~~~
~~~~~python.new
        return keys

    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_document_hashes(self, module: ModuleDef) -> Dict[str, str]:
        """Computes hashes for each docstring in the corresponding YAML."""
        docs = self.load_docs_for_module(module)
        return {
            fqn: self._hash_content(doc_content)
            for fqn, doc_content in docs.items()
        }
~~~~~

#### Acts 3: 更新 CLI 以采用新的校验标志

接下来，我们将修改 `stitcher` 的命令行接口。移除旧的 `--update-signatures` 标志，并根据提案引入更具表达力的 `--reconcile` 和 `--force-relink` 标志。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python.old
@app.command(help=nexus.get(L.cli.command.check.help))
def check(
    update_signatures: bool = typer.Option(
        False,
        "--update-signatures",
        help=nexus.get(L.cli.option.update_signatures.help),
    ),
):
    project_root = Path.cwd()
    app_instance = StitcherApp(root_path=project_root)
    success = app_instance.run_check(update_signatures=update_signatures)
    if not success:
        raise typer.Exit(code=1)
~~~~~
~~~~~python.new
@app.command(help=nexus.get(L.cli.command.check.help))
def check(
    force_relink: bool = typer.Option(
        False,
        "--force-relink",
        help="For 'Signature Drift' errors, forces the new signature to be linked with the existing, unchanged documentation.",
    ),
    reconcile: bool = typer.Option(
        False,
        "--reconcile",
        help="For 'Co-evolution' errors, accepts both signature and documentation changes as the new correct state.",
    ),
):
    if force_relink and reconcile:
        bus.error("Cannot use --force-relink and --reconcile simultaneously.")
        raise typer.Exit(code=1)

    project_root = Path.cwd()
    app_instance = StitcherApp(root_path=project_root)
    success = app_instance.run_check(
        force_relink=force_relink, reconcile=reconcile
    )
    if not success:
        raise typer.Exit(code=1)
~~~~~

#### Acts 4: 重构 `StitcherApp` 以实现状态机和同步机制

这是本次重构的核心。我们将大规模修改 `core.py` 文件：
1.  重写 `_analyze_file` 和 `run_check` 方法，实现完整的状态机校验逻辑。
2.  更新 `run_init`，使其在初始化时能生成包含签名和文档哈希的基线文件。
3.  更新 `run_hydrate`，确保在提取文档后，哈希记录也得到相应更新。

由于改动范围较大且逻辑紧密耦合，我将使用 `write_file` 来确保文件的完整性和一致性。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field

from stitcher.scanner import (
    parse_source_code,
    parse_plugin_entry,
    InspectionError,
    strip_docstrings,
    inject_docstrings,
)
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


@dataclass
class FileCheckResult:
    path: str
    errors: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    warnings: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    reconciled: Dict[str, List[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    auto_reconciled_count: int = 0

    @property
    def error_count(self) -> int:
        return sum(len(keys) for keys in self.errors.values())

    @property
    def warning_count(self) -> int:
        return sum(len(keys) for keys in self.warnings.values())

    @property
    def reconciled_count(self) -> int:
        return sum(len(keys) for keys in self.reconciled.values())

    @property
    def is_clean(self) -> bool:
        return (
            self.error_count == 0
            and self.warning_count == 0
            and self.reconciled_count == 0
            and self.auto_reconciled_count == 0
        )


class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.generator = StubGenerator()
        self.doc_manager = DocumentManager(root_path)
        self.sig_manager = SignatureManager(root_path)
        self.stub_pkg_manager = StubPackageManager()

    def _scan_files(self, files_to_scan: List[Path]) -> List[ModuleDef]:
        modules = []
        for source_file in files_to_scan:
            try:
                content = source_file.read_text(encoding="utf-8")
                relative_path = source_file.relative_to(self.root_path).as_posix()
                module_def = parse_source_code(content, file_path=relative_path)
                modules.append(module_def)
            except Exception as e:
                bus.error(L.error.generic, error=e)
        return modules

    def _derive_logical_path(self, file_path: str) -> Path:
        path_obj = Path(file_path)
        parts = path_obj.parts
        try:
            src_index = len(parts) - 1 - parts[::-1].index("src")
            return Path(*parts[src_index + 1 :])
        except ValueError:
            return path_obj

    def _process_plugins(self, plugins: Dict[str, str]) -> List[ModuleDef]:
        virtual_modules: Dict[Path, ModuleDef] = defaultdict(
            lambda: ModuleDef(file_path="")
        )
        for name, entry_point in plugins.items():
            try:
                func_def = parse_plugin_entry(entry_point)
                parts = name.split(".")
                module_path_parts = parts[:-1]
                func_file_name = parts[-1]
                func_path = Path(*module_path_parts, f"{func_file_name}.py")
                for i in range(1, len(module_path_parts) + 1):
                    init_path = Path(*parts[:i], "__init__.py")
                    if not virtual_modules[init_path].file_path:
                        virtual_modules[init_path].file_path = init_path.as_posix()
                if not virtual_modules[func_path].file_path:
                    virtual_modules[func_path].file_path = func_path.as_posix()
                virtual_modules[func_path].functions.append(func_def)
            except InspectionError as e:
                bus.error(L.error.plugin.inspection, error=e)
        return list(virtual_modules.values())

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
                package_namespace = path_parts[-1]
                break
            elif len(path_parts) >= 2 and path_parts[-2] == "src":
                if "pyneedle" in stub_base_name:
                    package_namespace = "needle"
                elif "stitcher" in stub_base_name:
                    package_namespace = "stitcher"
                break
        if not package_namespace:
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

    def _generate_stubs(
        self, modules: List[ModuleDef], config: StitcherConfig
    ) -> List[Path]:
        generated_files: List[Path] = []
        created_py_typed: set[Path] = set()
        for module in modules:
            self.doc_manager.apply_docs_to_module(module)
            pyi_content = self.generator.generate(module)
            if config.stub_package:
                logical_path = self._derive_logical_path(module.file_path)
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
                logical_path = self._derive_logical_path(module.file_path)
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
            output_path.write_text(pyi_content, encoding="utf-8")
            relative_path = output_path.relative_to(self.root_path)
            bus.success(L.generate.file.success, path=relative_path)
            generated_files.append(output_path)
        return generated_files

    def _get_files_from_config(self, config: StitcherConfig) -> List[Path]:
        files_to_scan = []
        for scan_path_str in config.scan_paths:
            scan_path = self.root_path / scan_path_str
            if scan_path.is_dir():
                files_to_scan.extend(scan_path.rglob("*.py"))
            elif scan_path.is_file():
                files_to_scan.append(scan_path)
        return sorted(list(set(files_to_scan)))

    def run_from_config(self) -> List[Path]:
        configs, project_name = load_config_from_path(self.root_path)
        all_generated_files: List[Path] = []
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            if config.stub_package:
                stub_base_name = (
                    config.name if config.name != "default" else project_name
                )
                self._scaffold_stub_package(config, stub_base_name)
            unique_files = self._get_files_from_config(config)
            source_modules = self._scan_files(unique_files)
            plugin_modules = self._process_plugins(config.plugins)
            all_modules = source_modules + plugin_modules
            if not all_modules:
                if len(configs) == 1:
                    bus.warning(L.warning.no_files_or_plugins_found)
                continue
            generated_files = self._generate_stubs(all_modules, config)
            all_generated_files.extend(generated_files)
        if all_generated_files:
            bus.success(L.generate.run.complete, count=len(all_generated_files))
        return all_generated_files

    def run_init(self) -> List[Path]:
        configs, _ = load_config_from_path(self.root_path)
        all_created_files: List[Path] = []
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            if not modules:
                continue
            for module in modules:
                output_path = self.doc_manager.save_docs_for_module(module)
                s_hashes = self.sig_manager.compute_signature_hashes(module)
                d_hashes = self.doc_manager.compute_document_hashes(module)
                combined = {}
                all_fqns = set(s_hashes.keys()) | set(d_hashes.keys())
                for fqn in all_fqns:
                    combined[fqn] = {
                        "signature_hash": s_hashes.get(fqn),
                        "document_hash": d_hashes.get(fqn),
                    }
                self.sig_manager.save_hashes(module, combined)
                if output_path and output_path.name:
                    relative_path = output_path.relative_to(self.root_path)
                    bus.success(L.init.file.created, path=relative_path)
                    all_created_files.append(output_path)
        if all_created_files:
            bus.success(L.init.run.complete, count=len(all_created_files))
        else:
            bus.info(L.init.no_docs_found)
        return all_created_files

    def _analyze_file(
        self, module: ModuleDef, force_relink: bool, reconcile: bool
    ) -> FileCheckResult:
        result = FileCheckResult(path=module.file_path)
        doc_path = (self.root_path / module.file_path).with_suffix(".stitcher.yaml")
        is_tracked = doc_path.exists()

        s_current_map = self.sig_manager.compute_signature_hashes(module)
        d_current_map = self.doc_manager.compute_document_hashes(module)
        stored_hashes_map = self.sig_manager.load_hashes(module)
        new_hashes_map = stored_hashes_map.copy()

        all_fqns = set(s_current_map.keys()) | set(stored_hashes_map.keys())

        for fqn in sorted(list(all_fqns)):
            s_current = s_current_map.get(fqn)
            d_current = d_current_map.get(fqn)
            stored = stored_hashes_map.get(fqn, {})
            s_stored = stored.get("signature_hash")
            d_stored = stored.get("document_hash")

            if not s_current and s_stored:
                result.errors["extra"].append(fqn)
                new_hashes_map.pop(fqn, None)
                continue

            if s_current and not s_stored:
                if is_tracked:
                    result.warnings["untracked_key"].append(fqn)
                new_hashes_map[fqn] = {
                    "signature_hash": s_current,
                    "document_hash": d_current,
                }
                continue

            s_match = s_current == s_stored
            d_match = d_current == d_stored

            if s_match and d_match:
                pass
            elif s_match and not d_match:
                result.warnings["doc_improvement"].append(fqn)
                if fqn in new_hashes_map:
                    new_hashes_map[fqn]["document_hash"] = d_current
                result.auto_reconciled_count += 1
            elif not s_match and d_match:
                if force_relink:
                    result.reconciled["force_relink"].append(fqn)
                    if fqn in new_hashes_map:
                        new_hashes_map[fqn]["signature_hash"] = s_current
                else:
                    result.errors["signature_drift"].append(fqn)
            elif not s_match and not d_match:
                if reconcile:
                    result.reconciled["reconcile"].append(fqn)
                    new_hashes_map[fqn] = {
                        "signature_hash": s_current,
                        "document_hash": d_current,
                    }
                else:
                    result.errors["co_evolution"].append(fqn)

        if not is_tracked and module.is_documentable():
            undocumented = module.get_undocumented_public_keys()
            if undocumented:
                result.warnings["untracked_detailed"].extend(undocumented)
            else:
                result.warnings["untracked"].append("all")

        if new_hashes_map != stored_hashes_map:
            self.sig_manager.save_hashes(module, new_hashes_map)

        return result

    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        configs, _ = load_config_from_path(self.root_path)
        global_failed_files = 0
        global_warnings_files = 0
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            if not modules:
                continue
            for module in modules:
                res = self._analyze_file(module, force_relink, reconcile)
                if res.is_clean:
                    continue

                if res.reconciled_count > 0:
                    for key in res.reconciled.get("force_relink", []):
                        bus.success(
                            f"[OK] Re-linked signature for '{key}' in {res.path}"
                        )
                    for key in res.reconciled.get("reconcile", []):
                        bus.success(
                            f"[OK] Reconciled changes for '{key}' in {res.path}"
                        )
                if res.auto_reconciled_count > 0:
                    bus.info(
                        f"[INFO] Automatically updated {res.auto_reconciled_count} documentation hash(es) in {res.path}"
                    )

                if res.error_count > 0:
                    global_failed_files += 1
                    bus.error(L.check.file.fail, path=res.path, count=res.error_count)
                elif res.warning_count > 0:
                    global_warnings_files += 1
                    bus.warning(
                        L.check.file.warn, path=res.path, count=res.warning_count
                    )

                for key in sorted(res.errors["extra"]):
                    bus.error(f"[Extra Doc] '{key}': In docs but not in code.")
                for key in sorted(res.errors["signature_drift"]):
                    bus.error(
                        f"[Signature Drift] '{key}': Code changed, docs may be stale."
                    )
                for key in sorted(res.errors["co_evolution"]):
                    bus.error(
                        f"[Co-evolution] '{key}': Both code and docs changed; intent unclear."
                    )
                for key in sorted(res.warnings["untracked_key"]):
                    bus.warning(
                        f"[Untracked Code] '{key}': New public API without documentation."
                    )
                for key in sorted(res.warnings["doc_improvement"]):
                    bus.info(f"[Doc Updated] '{key}': Documentation was improved.")
                if "untracked_detailed" in res.warnings:
                    keys = res.warnings["untracked_detailed"]
                    bus.warning(
                        f"[Untracked File] '{res.path}' has {len(keys)} undocumented public APIs."
                    )
                elif "untracked" in res.warnings:
                    bus.warning(
                        f"[Untracked File] '{res.path}' is not tracked by stitcher."
                    )

        if global_failed_files > 0:
            bus.error(L.check.run.fail, count=global_failed_files)
            return False
        if global_warnings_files > 0:
            bus.success(L.check.run.success_with_warnings, count=global_warnings_files)
        else:
            bus.success(L.check.run.success)
        return True

    def run_hydrate(
        self, strip: bool = False, force: bool = False, reconcile: bool = False
    ) -> bool:
        bus.info(L.hydrate.run.start)
        configs, _ = load_config_from_path(self.root_path)
        total_updated = 0
        total_conflicts = 0
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            if not modules:
                continue
            files_to_strip = []
            for module in modules:
                result = self.doc_manager.hydrate_module(
                    module, force=force, reconcile=reconcile
                )
                if not result["success"]:
                    total_conflicts += 1
                    for conflict_key in result["conflicts"]:
                        bus.error(
                            L.hydrate.error.conflict,
                            path=module.file_path,
                            key=conflict_key,
                        )
                    continue
                if result["reconciled_keys"]:
                    bus.info(
                        L.hydrate.info.reconciled,
                        path=module.file_path,
                        count=len(result["reconciled_keys"]),
                    )
                if result["updated_keys"]:
                    total_updated += 1
                    bus.success(
                        L.hydrate.file.success,
                        path=module.file_path,
                        count=len(result["updated_keys"]),
                    )
                s_hashes = self.sig_manager.compute_signature_hashes(module)
                d_hashes = self.doc_manager.compute_document_hashes(module)
                all_fqns = set(s_hashes.keys()) | set(d_hashes.keys())
                combined = {
                    fqn: {
                        "signature_hash": s_hashes.get(fqn),
                        "document_hash": d_hashes.get(fqn),
                    }
                    for fqn in all_fqns
                }
                self.sig_manager.save_hashes(module, combined)
                files_to_strip.append(module)
            if strip and files_to_strip:
                stripped_count = 0
                for module in files_to_strip:
                    source_path = self.root_path / module.file_path
                    try:
                        original_content = source_path.read_text(encoding="utf-8")
                        stripped_content = strip_docstrings(original_content)
                        if original_content != stripped_content:
                            source_path.write_text(stripped_content, encoding="utf-8")
                            stripped_count += 1
                            relative_path = source_path.relative_to(self.root_path)
                            bus.success(L.strip.file.success, path=relative_path)
                    except Exception as e:
                        bus.error(L.error.generic, error=e)
                if stripped_count > 0:
                    bus.success(L.strip.run.complete, count=stripped_count)
        if total_conflicts > 0:
            bus.error(L.hydrate.run.conflict, count=total_conflicts)
            return False
        if total_updated == 0:
            bus.info(L.hydrate.run.no_changes)
        else:
            bus.success(L.hydrate.run.complete, count=total_updated)
        return True

    def run_strip(self) -> List[Path]:
        configs, _ = load_config_from_path(self.root_path)
        all_modified_files: List[Path] = []
        for config in configs:
            files_to_scan = self._get_files_from_config(config)
            for file_path in files_to_scan:
                try:
                    original_content = file_path.read_text(encoding="utf-8")
                    stripped_content = strip_docstrings(original_content)
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

    def run_eject(self) -> List[Path]:
        configs, _ = load_config_from_path(self.root_path)
        all_modified_files: List[Path] = []
        total_docs_found = 0
        for config in configs:
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            for module in modules:
                docs = self.doc_manager.load_docs_for_module(module)
                if not docs:
                    continue
                total_docs_found += len(docs)
                source_path = self.root_path / module.file_path
                try:
                    original_content = source_path.read_text(encoding="utf-8")
                    injected_content = inject_docstrings(original_content, docs)
                    if original_content != injected_content:
                        source_path.write_text(injected_content, encoding="utf-8")
                        all_modified_files.append(source_path)
                        relative_path = source_path.relative_to(self.root_path)
                        bus.success(L.eject.file.success, path=relative_path)
                except Exception as e:
                    bus.error(L.error.generic, error=e)
        if all_modified_files:
            bus.success(L.eject.run.complete, count=len(all_modified_files))
        elif total_docs_found == 0:
            bus.info(L.eject.no_docs_found)
        return all_modified_files
~~~~~

### 下一步建议
我们已经完成了核心逻辑的重构。下一步是为这个新的状态机编写全面的单元测试和集成测试，以确保其在各种边界条件下的行为都符合预期。我将创建一个新的测试文件 `tests/test_check_state_machine.py` 来专门验证这部分逻辑。
