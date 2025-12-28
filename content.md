## [WIP] refactor: 全面重构哈希命名与校验逻辑

### 用户需求
1.  **强制长命名**: 彻底消除 `s_current` 等歧义命名，使用 `current_code_structure_hash` 等自文档化命名。
2.  **规范化消息**: 禁止在代码中硬编码日志字符串，必须使用 Needle 定义的语义化 L 指针。
3.  **修复测试**: 解决哈希计算不一致和断言失败的问题，确保状态机逻辑正确持久化。

### 评论
此次重构是对代码质量的一次重大提升。通过采用极度明确的变量命名，我们消除了核心逻辑中的认知负荷和歧义。引入 `check.state` 命名空间下的 L 指针，确保了 CLI 输出的一致性和可测试性。这是为了长期的可维护性而必须支付的成本。

### 目标
1.  在 `stitcher-common` 中创建 `check/state.json`，定义状态机相关的语义消息。
2.  重构 `SignatureManager`，将 API 和存储键重命名为 `code_structure_hash` 和 `yaml_content_hash`。
3.  重构 `DocumentManager`，重命名哈希计算方法。
4.  完全重写 `StitcherApp.core.py`，应用长命名规则，并使用 `bus.success(L.check.state.relinked, ...)` 等规范调用。
5.  重写集成测试，匹配新的命名和消息断言。

### 基本原理
清晰的命名是逻辑正确性的前提。在处理涉及多个来源（代码 vs YAML）、多个版本（当前 vs 存储）的复杂状态机时，变量名必须承载完整的上下文信息，以防止“张冠李戴”式的逻辑错误。

### 标签
#intent/refine #flow/ready #priority/high #comp/application #comp/common #scope/core #ai/instruct #task/domain/validation #task/object/state-machine #task/action/refactor #task/state/continue

---
### Script

#### Acts 1: 定义状态机语义消息

在 Needle 资产中新增 `check/state.json`，定义所有状态机相关的输出模板。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/state.json
~~~~~
~~~~~json
{
  "relinked": "Re-linked signature for '{key}' in {path}",
  "reconciled": "Reconciled changes for '{key}' in {path}",
  "auto_reconciled": "Automatically updated {count} documentation hash(es) in {path}",
  "extra_doc": "Extra Doc: '{key}' is in docs but not in code.",
  "signature_drift": "Signature Drift: '{key}' code changed, docs may be stale.",
  "co_evolution": "Co-evolution: '{key}' both code and docs changed; intent unclear.",
  "doc_updated": "Doc Updated: '{key}' documentation was improved.",
  "untracked_code": "Untracked Code: '{key}' new public API without documentation."
}
~~~~~

#### Acts 2: 重构 `SignatureManager` 和 `DocumentManager`

应用强制长命名规则。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python
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

    def compute_code_structure_hashes(self, module: ModuleDef) -> Dict[str, str]:
        """Computes structural fingerprints for all addressable functions/methods."""
        hashes = {}
        for func in module.functions:
            hashes[func.name] = func.compute_fingerprint()
        for cls in module.classes:
            for method in cls.methods:
                fqn = f"{cls.name}.{method.name}"
                hashes[fqn] = method.compute_fingerprint()
        return hashes

    def save_composite_hashes(self, module: ModuleDef, hashes: Dict[str, Any]) -> None:
        """
        Saves the composite hash map for a module.
        Expected format: { "FQN": { "code_structure_hash": "...", "yaml_content_hash": "..." } }
        """
        if not hashes:
            sig_path = self._get_sig_path(module)
            if sig_path.exists():
                sig_path.unlink()
            return

        sig_path = self._get_sig_path(module)
        sig_path.parent.mkdir(parents=True, exist_ok=True)

        with sig_path.open("w", encoding="utf-8") as f:
            json.dump(hashes, f, indent=2, sort_keys=True)

    def load_composite_hashes(self, module: ModuleDef) -> Dict[str, Any]:
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

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any

from stitcher.spec import ModuleDef, ClassDef, FunctionDef
from stitcher.io import DocumentAdapter, YamlAdapter


class DocumentManager:
    def __init__(self, root_path: Path, adapter: Optional[DocumentAdapter] = None):
        self.root_path = root_path
        self.adapter = adapter or YamlAdapter()

    def _extract_from_function(
        self, func: FunctionDef, prefix: str = ""
    ) -> Dict[str, str]:
        docs = {}
        full_name = f"{prefix}{func.name}"
        if func.docstring:
            docs[full_name] = func.docstring
        return docs

    def _extract_from_class(self, cls: ClassDef, prefix: str = "") -> Dict[str, str]:
        docs = {}
        full_name = f"{prefix}{cls.name}"
        if cls.docstring:
            docs[full_name] = cls.docstring
        for method in cls.methods:
            docs.update(self._extract_from_function(method, prefix=f"{full_name}."))
        return docs

    def flatten_module_docs(self, module: ModuleDef) -> Dict[str, str]:
        docs: Dict[str, str] = {}
        if module.docstring:
            docs["__doc__"] = module.docstring
        for func in module.functions:
            docs.update(self._extract_from_function(func))
        for cls in module.classes:
            docs.update(self._extract_from_class(cls))
        for attr in module.attributes:
            if attr.docstring:
                docs[attr.name] = attr.docstring
        for cls in module.classes:
            for attr in cls.attributes:
                if attr.docstring:
                    docs[f"{cls.name}.{attr.name}"] = attr.docstring
        return docs

    def save_docs_for_module(self, module: ModuleDef) -> Path:
        data = self.flatten_module_docs(module)
        if not data:
            return Path("")
        module_path = self.root_path / module.file_path
        output_path = module_path.with_suffix(".stitcher.yaml")
        self.adapter.save(output_path, data)
        return output_path

    def load_docs_for_module(self, module: ModuleDef) -> Dict[str, str]:
        if not module.file_path:
            return {}
        module_path = self.root_path / module.file_path
        doc_path = module_path.with_suffix(".stitcher.yaml")
        return self.adapter.load(doc_path)

    def _apply_to_function(
        self, func: FunctionDef, docs: Dict[str, str], prefix: str = ""
    ):
        full_name = f"{prefix}{func.name}"
        if full_name in docs:
            func.docstring = docs[full_name]

    def _apply_to_class(self, cls: ClassDef, docs: Dict[str, str], prefix: str = ""):
        full_name = f"{prefix}{cls.name}"
        if full_name in docs:
            cls.docstring = docs[full_name]
        for method in cls.methods:
            self._apply_to_function(method, docs, prefix=f"{full_name}.")
        for attr in cls.attributes:
            attr_key = f"{full_name}.{attr.name}"
            if attr_key in docs:
                attr.docstring = docs[attr_key]

    def apply_docs_to_module(self, module: ModuleDef) -> None:
        docs = self.load_docs_for_module(module)
        if not docs:
            return
        if "__doc__" in docs:
            module.docstring = docs["__doc__"]
        for func in module.functions:
            self._apply_to_function(func, docs)
        for cls in module.classes:
            self._apply_to_class(cls, docs)
        for attr in module.attributes:
            if attr.name in docs:
                attr.docstring = docs[attr.name]

    def check_module(self, module: ModuleDef) -> Dict[str, set]:
        public_keys = self._extract_keys(module, public_only=True)
        all_keys = self._extract_keys(module, public_only=False)
        source_docs = self.flatten_module_docs(module)
        yaml_docs = self.load_docs_for_module(module)
        yaml_keys = set(yaml_docs.keys())

        extra = yaml_keys - all_keys
        extra.discard("__doc__")

        missing_doc = set()
        pending_hydration = set()
        redundant_doc = set()
        doc_conflict = set()

        for key in all_keys:
            is_public = key in public_keys
            has_source_doc = key in source_docs
            has_yaml_doc = key in yaml_keys

            if not has_source_doc and not has_yaml_doc:
                if is_public:
                    missing_doc.add(key)
            elif has_source_doc and not has_yaml_doc:
                pending_hydration.add(key)
            elif has_source_doc and has_yaml_doc:
                if source_docs[key] != yaml_docs[key]:
                    doc_conflict.add(key)
                else:
                    redundant_doc.add(key)
        
        return {
            "extra": extra,
            "missing": missing_doc,
            "pending": pending_hydration,
            "redundant": redundant_doc,
            "conflict": doc_conflict,
        }

    def hydrate_module(
        self, module: ModuleDef, force: bool = False, reconcile: bool = False
    ) -> Dict[str, Any]:
        source_docs = self.flatten_module_docs(module)
        if not source_docs:
            return {
                "success": True,
                "updated_keys": [],
                "conflicts": [],
                "reconciled_keys": [],
            }
        yaml_docs = self.load_docs_for_module(module)
        updated_keys = []
        conflicts = []
        reconciled_keys = []
        new_yaml_docs = yaml_docs.copy()

        for key, source_content in source_docs.items():
            if key not in yaml_docs:
                new_yaml_docs[key] = source_content
                updated_keys.append(key)
            elif yaml_docs[key] != source_content:
                if reconcile:
                    reconciled_keys.append(key)
                    continue
                elif force:
                    new_yaml_docs[key] = source_content
                    updated_keys.append(key)
                else:
                    conflicts.append(key)

        if conflicts:
            return {
                "success": False,
                "updated_keys": [],
                "conflicts": conflicts,
                "reconciled_keys": [],
            }

        if updated_keys:
            module_path = self.root_path / module.file_path
            output_path = module_path.with_suffix(".stitcher.yaml")
            self.adapter.save(output_path, new_yaml_docs)

        return {
            "success": True,
            "updated_keys": updated_keys,
            "conflicts": [],
            "reconciled_keys": reconciled_keys,
        }

    def _extract_keys(self, module: ModuleDef, public_only: bool) -> set:
        keys = set()
        if module.docstring:
            keys.add("__doc__")

        def include(name: str) -> bool:
            if public_only:
                return not name.startswith("_")
            return True

        for func in module.functions:
            if include(func.name):
                keys.add(func.name)
        for cls in module.classes:
            if include(cls.name):
                keys.add(cls.name)
                for method in cls.methods:
                    if include(method.name):
                        keys.add(f"{cls.name}.{method.name}")
                for attr in cls.attributes:
                    if include(attr.name):
                        keys.add(f"{cls.name}.{attr.name}")
        for attr in module.attributes:
            if include(attr.name):
                keys.add(attr.name)
        return keys

    def compute_yaml_content_hash(self, content: str) -> str:
        """Computes the hash of a docstring content string."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_yaml_content_hashes(self, module: ModuleDef) -> Dict[str, str]:
        """Computes hashes for each docstring in the corresponding YAML."""
        docs = self.load_docs_for_module(module)
        return {
            fqn: self.compute_yaml_content_hash(doc_content)
            for fqn, doc_content in docs.items()
        }
~~~~~

#### Acts 3: 重构 `StitcherApp`

全面替换变量名，并使用 `L` 指针进行日志记录。

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
    infos: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
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
            # Auto-reconciled (infos) do not affect cleanliness
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
                code_hashes = self.sig_manager.compute_code_structure_hashes(module)
                yaml_hashes = self.doc_manager.compute_yaml_content_hashes(module)
                combined = {}
                all_fqns = set(code_hashes.keys()) | set(yaml_hashes.keys())
                for fqn in all_fqns:
                    combined[fqn] = {
                        "code_structure_hash": code_hashes.get(fqn),
                        "yaml_content_hash": yaml_hashes.get(fqn),
                    }
                self.sig_manager.save_composite_hashes(module, combined)
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

        # 1. Content Checks
        if (self.root_path / module.file_path).with_suffix(".stitcher.yaml").exists():
            doc_issues = self.doc_manager.check_module(module)
            if doc_issues["missing"]:
                result.warnings["missing"].extend(doc_issues["missing"])
            if doc_issues["redundant"]:
                result.warnings["redundant"].extend(doc_issues["redundant"])
            if doc_issues["pending"]:
                result.errors["pending"].extend(doc_issues["pending"])
            if doc_issues["conflict"]:
                result.errors["conflict"].extend(doc_issues["conflict"])
            if doc_issues["extra"]:
                result.errors["extra"].extend(doc_issues["extra"])

        # 2. State Machine Checks
        doc_path = (self.root_path / module.file_path).with_suffix(".stitcher.yaml")
        is_tracked = doc_path.exists()

        current_code_structure_map = self.sig_manager.compute_code_structure_hashes(module)
        current_yaml_content_map = self.doc_manager.compute_yaml_content_hashes(module)
        stored_hashes_map = self.sig_manager.load_composite_hashes(module)
        new_hashes_map = stored_hashes_map.copy()

        all_fqns = set(current_code_structure_map.keys()) | set(stored_hashes_map.keys())

        for fqn in sorted(list(all_fqns)):
            current_code_structure_hash = current_code_structure_map.get(fqn)
            current_yaml_content_hash = current_yaml_content_map.get(fqn)
            stored = stored_hashes_map.get(fqn, {})
            stored_code_structure_hash = stored.get("code_structure_hash")
            stored_yaml_content_hash = stored.get("yaml_content_hash")

            # Case: Extra (In Storage, Not in Code)
            if not current_code_structure_hash and stored_code_structure_hash:
                if fqn in new_hashes_map:
                    new_hashes_map.pop(fqn, None)
                continue

            # Case: New (In Code, Not in Storage)
            if current_code_structure_hash and not stored_code_structure_hash:
                if is_tracked:
                    new_hashes_map[fqn] = {
                        "code_structure_hash": current_code_structure_hash,
                        "yaml_content_hash": current_yaml_content_hash,
                    }
                continue

            # Case: Existing
            code_structure_matches = current_code_structure_hash == stored_code_structure_hash
            yaml_content_matches = current_yaml_content_hash == stored_yaml_content_hash

            if code_structure_matches and yaml_content_matches:
                pass  # Synchronized
            elif code_structure_matches and not yaml_content_matches:
                # Doc Improvement: INFO, Auto-reconcile
                result.infos["doc_improvement"].append(fqn)
                if fqn in new_hashes_map:
                    new_hashes_map[fqn]["yaml_content_hash"] = current_yaml_content_hash
                result.auto_reconciled_count += 1
            elif not code_structure_matches and yaml_content_matches:
                # Signature Drift
                if force_relink:
                    result.reconciled["force_relink"].append(fqn)
                    if fqn in new_hashes_map:
                        new_hashes_map[fqn]["code_structure_hash"] = current_code_structure_hash
                else:
                    result.errors["signature_drift"].append(fqn)
            elif not code_structure_matches and not yaml_content_matches:
                # Co-evolution
                if reconcile:
                    result.reconciled["reconcile"].append(fqn)
                    new_hashes_map[fqn] = {
                        "code_structure_hash": current_code_structure_hash,
                        "yaml_content_hash": current_yaml_content_hash,
                    }
                else:
                    result.errors["co_evolution"].append(fqn)

        # 3. Untracked File check
        if not is_tracked and module.is_documentable():
            undocumented = module.get_undocumented_public_keys()
            if undocumented:
                result.warnings["untracked_detailed"].extend(undocumented)
            else:
                result.warnings["untracked"].append("all")

        # Save hash updates if any
        if new_hashes_map != stored_hashes_map:
            self.sig_manager.save_composite_hashes(module, new_hashes_map)

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
                    if res.auto_reconciled_count > 0:
                        bus.info(
                            L.check.state.auto_reconciled,
                            count=res.auto_reconciled_count,
                            path=res.path
                        )
                    continue

                if res.reconciled_count > 0:
                    for key in res.reconciled.get("force_relink", []):
                        bus.success(
                            L.check.state.relinked, key=key, path=res.path
                        )
                    for key in res.reconciled.get("reconcile", []):
                        bus.success(
                            L.check.state.reconciled, key=key, path=res.path
                        )
                if res.auto_reconciled_count > 0:
                    bus.info(
                        L.check.state.auto_reconciled,
                        count=res.auto_reconciled_count,
                        path=res.path
                    )

                if res.error_count > 0:
                    global_failed_files += 1
                    bus.error(L.check.file.fail, path=res.path, count=res.error_count)
                elif res.warning_count > 0:
                    global_warnings_files += 1
                    bus.warning(
                        L.check.file.warn, path=res.path, count=res.warning_count
                    )

                # Report Specific Issues
                for key in sorted(res.errors["extra"]):
                    bus.error(L.check.state.extra_doc, key=key)
                for key in sorted(res.errors["signature_drift"]):
                    bus.error(L.check.state.signature_drift, key=key)
                for key in sorted(res.errors["co_evolution"]):
                    bus.error(L.check.state.co_evolution, key=key)
                for key in sorted(res.errors["conflict"]):
                    bus.error(L.check.issue.conflict, key=key)
                for key in sorted(res.errors["pending"]):
                    bus.error(L.check.issue.pending, key=key)

                for key in sorted(res.warnings["missing"]):
                    bus.warning(L.check.issue.missing, key=key)
                for key in sorted(res.warnings["redundant"]):
                    bus.warning(L.check.issue.redundant, key=key)
                for key in sorted(res.warnings["untracked_key"]):
                    bus.warning(L.check.state.untracked_code, key=key)
                
                for key in sorted(res.infos["doc_improvement"]):
                    bus.info(L.check.state.doc_updated, key=key)

                if "untracked_detailed" in res.warnings:
                    keys = res.warnings["untracked_detailed"]
                    bus.warning(
                        L.check.file.untracked_with_details,
                        path=res.path,
                        count=len(keys),
                    )
                    for key in sorted(keys):
                        bus.warning(L.check.issue.untracked_missing_key, key=key)
                elif "untracked" in res.warnings:
                    bus.warning(L.check.file.untracked, path=res.path)

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
                code_hashes = self.sig_manager.compute_code_structure_hashes(module)
                yaml_hashes = self.doc_manager.compute_yaml_content_hashes(module)
                all_fqns = set(code_hashes.keys()) | set(yaml_hashes.keys())
                combined = {
                    fqn: {
                        "code_structure_hash": code_hashes.get(fqn),
                        "yaml_content_hash": yaml_hashes.get(fqn),
                    }
                    for fqn in all_fqns
                }
                self.sig_manager.save_composite_hashes(module, combined)
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
    
    # ... rest of methods (run_strip, run_eject) remain same ...
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

#### Acts 4: 重构测试用例

重写 `test_check_state_machine.py` 和 `test_check_signatures.py`，确保它们使用新的 L 指针进行断言，并使用新的键名检查 JSON 数据。

~~~~~act
write_file
tests/integration/test_check_state_machine.py
~~~~~
~~~~~python
from textwrap import dedent
from pathlib import Path
import json
from stitcher.app import StitcherApp
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory
from stitcher.app.services import DocumentManager, SignatureManager


def _get_stored_hashes(project_root: Path, file_path: str) -> dict:
    sig_file = project_root / ".stitcher/signatures" / Path(file_path).with_suffix(".json")
    if not sig_file.exists():
        return {}
    with sig_file.open("r") as f:
        return json.load(f)


def _assert_no_errors_or_warnings(spy_bus: SpyBus):
    errors = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    warnings = [m for m in spy_bus.get_messages() if m["level"] == "warning"]
    assert not errors, f"Unexpected errors: {errors}"
    assert not warnings, f"Unexpected warnings: {warnings}"


def test_state_synchronized(tmp_path, monkeypatch):
    """
    State 1: Synchronized - Code and docs match stored hashes.
    Expected: Silent pass.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Docstring."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)

    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # Remove docstring to achieve 'Synchronized' state without redundant warnings
    (project_root / "src/module.py").write_text("def func(a: int):\n    pass")

    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert success is True
    _assert_no_errors_or_warnings(spy_bus)
    spy_bus.assert_id_called(L.check.run.success, level="success")


def test_state_doc_improvement_auto_reconciled(tmp_path, monkeypatch):
    """
    State 2: Documentation Improvement.
    Expected: INFO message, auto-reconcile doc hash, pass.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Old Doc."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    (project_root / "src/module.py").write_text("def func(a: int):\n    pass")

    # Modify YAML
    doc_file = project_root / "src/module.stitcher.yaml"
    new_doc_content = "New Doc."
    doc_file.write_text(f'__doc__: "Module Doc"\nfunc: "{new_doc_content}"\n', encoding="utf-8")
    
    initial_hashes = _get_stored_hashes(project_root, "src/module.py")
    
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert success is True
    # Assert Semantic ID for doc update
    spy_bus.assert_id_called(L.check.state.doc_updated, level="info")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["code_structure_hash"] == initial_hashes["func"]["code_structure_hash"]
    
    expected_hash = app.doc_manager.compute_yaml_content_hash(new_doc_content)
    assert final_hashes["func"]["yaml_content_hash"] == expected_hash


def test_state_signature_drift_error(tmp_path, monkeypatch):
    """
    State 3: Signature Drift.
    Expected: ERROR message, check fails.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Doc."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")

    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert success is False
    spy_bus.assert_id_called(L.check.state.signature_drift, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


def test_state_signature_drift_force_relink(tmp_path, monkeypatch):
    """
    State 3 (Resolved): Signature Drift with force_relink.
    Expected: SUCCESS message, update signature hash, pass.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Doc."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")

    initial_hashes = _get_stored_hashes(project_root, "src/module.py")

    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check(force_relink=True)

    assert success is True
    spy_bus.assert_id_called(L.check.state.relinked, level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    
    assert final_hashes["func"]["code_structure_hash"] != initial_hashes["func"]["code_structure_hash"]
    assert final_hashes["func"]["yaml_content_hash"] == initial_hashes["func"]["yaml_content_hash"]


def test_state_co_evolution_error(tmp_path, monkeypatch):
    """
    State 4: Co-evolution.
    Expected: ERROR message, check fails.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Old Doc."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")
    
    doc_file = project_root / "src/module.stitcher.yaml"
    doc_file.write_text('__doc__: "Module Doc"\nfunc: "New YAML Doc."\n', encoding="utf-8")

    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert success is False
    spy_bus.assert_id_called(L.check.state.co_evolution, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


def test_state_co_evolution_reconcile(tmp_path, monkeypatch):
    """
    State 4 (Resolved): Co-evolution with reconcile.
    Expected: SUCCESS message, update both hashes, pass.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Old Doc."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")
    
    doc_file = project_root / "src/module.stitcher.yaml"
    new_doc_content = "New YAML Doc."
    doc_file.write_text(f'__doc__: "Module Doc"\nfunc: "{new_doc_content}"\n', encoding="utf-8")

    initial_hashes = _get_stored_hashes(project_root, "src/module.py")

    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check(reconcile=True)

    assert success is True
    spy_bus.assert_id_called(L.check.state.reconciled, level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["code_structure_hash"] != initial_hashes["func"]["code_structure_hash"]
    assert final_hashes["func"]["yaml_content_hash"] != initial_hashes["func"]["yaml_content_hash"]
    
    expected_doc_hash = app.doc_manager.compute_yaml_content_hash(new_doc_content)
    assert final_hashes["func"]["yaml_content_hash"] == expected_doc_hash
~~~~~

~~~~~act
write_file
tests/integration/test_check_signatures.py
~~~~~
~~~~~python
from textwrap import dedent
from stitcher.app import StitcherApp
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def _assert_no_errors(spy_bus):
    errors = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    assert not errors, f"Unexpected errors: {errors}"


def test_check_detects_signature_change(tmp_path, monkeypatch):
    """
    End-to-End test verifying that modifying a function signature
    triggers a check failure/warning.
    """
    factory = WorkspaceFactory(tmp_path)
    initial_code = dedent("""
    def process(value: int) -> int:
        \"\"\"Process an integer.\"\"\"
        return value * 2
    """).strip()

    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/processor.py", initial_code)
        .build()
    )

    app = StitcherApp(root_path=project_root)

    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    _assert_no_errors(spy_bus)
    spy_bus.assert_id_called(L.init.run.complete, level="success")

    # Modify Code: Change signature AND remove docstring
    modified_code = dedent("""
    def process(value: str) -> int:
        return len(value) * 2
    """).strip()
    (project_root / "src/processor.py").write_text(modified_code, encoding="utf-8")

    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert success is False
    spy_bus.assert_id_called(L.check.state.signature_drift, level="error")


def test_generate_does_not_update_signatures(tmp_path, monkeypatch):
    """
    Verify that running 'generate' is now pure and DOES NOT update the signature baseline.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(a: int): ...")
        .with_docs("src/main.stitcher.yaml", {"func": "doc"})
        .build()
    )
    app = StitcherApp(root_path=project_root)

    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()
    
    (project_root / "src/main.py").write_text("def func(a: str): ...")

    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_from_config()

    spy_bus_check = SpyBus()
    with spy_bus_check.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert not success, "Check passed, but it should have failed."
    spy_bus_check.assert_id_called(L.check.state.signature_drift, level="error")


def test_check_with_force_relink_reconciles_changes(tmp_path, monkeypatch):
    """
    Verify the complete workflow of reconciling signature changes with `check --force-relink`.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func(a: int):\n    """Doc."""\n    ...')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # Modify: Change signature, remove doc to be clean
    (project_root / "src/main.py").write_text("def func(a: str):\n    ...")

    spy_bus_reconcile = SpyBus()
    with spy_bus_reconcile.patch(monkeypatch, "stitcher.app.core.bus"):
        success_reconcile = app.run_check(force_relink=True)

    assert success_reconcile is True, "Check with --force-relink failed"
    spy_bus_reconcile.assert_id_called(L.check.state.relinked, level="success")
    
    spy_bus_verify = SpyBus()
    with spy_bus_verify.patch(monkeypatch, "stitcher.app.core.bus"):
        success_verify = app.run_check()

    assert success_verify is True, "Verification check failed after reconciliation"
    spy_bus_verify.assert_id_called(L.check.run.success, level="success")
~~~~~

#### Acts 5: 修复 SignatureManager 的单元测试

因为我们重命名了方法和键，`tests/test_signature_manager.py` 也需要更新。

~~~~~act
write_file
packages/stitcher-application/tests/test_signature_manager.py
~~~~~
~~~~~python
import json
from pathlib import Path
from stitcher.spec import ModuleDef, FunctionDef, Argument, ArgumentKind
from stitcher.app.services import SignatureManager


def create_func(name="func", args=None, ret=None):
    return FunctionDef(
        name=name,
        args=args or [],
        return_annotation=ret,
    )


def test_fingerprint_stability():
    # 1. Base case
    arg_a = Argument(
        name="a", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="int"
    )
    func1 = create_func(name="my_func", args=[arg_a], ret="str")
    fp1 = func1.compute_fingerprint()

    # 2. Identical function should have identical fingerprint
    func2 = create_func(name="my_func", args=[arg_a], ret="str")
    fp2 = func2.compute_fingerprint()
    assert fp1 == fp2

    # 3. Change in parameter name -> Different
    arg_b = Argument(
        name="b", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="int"
    )
    func3 = create_func(name="my_func", args=[arg_b], ret="str")
    assert fp1 != func3.compute_fingerprint()

    # 4. Change in annotation -> Different
    arg_a_str = Argument(
        name="a", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="str"
    )
    func4 = create_func(name="my_func", args=[arg_a_str], ret="str")
    assert fp1 != func4.compute_fingerprint()

    # 5. Change in return type -> Different
    func5 = create_func(name="my_func", args=[arg_a], ret="int")
    assert fp1 != func5.compute_fingerprint()


def test_manager_save_and_load_composite_hashes(tmp_path: Path):
    # Arrange
    manager = SignatureManager(root_path=tmp_path)
    module = ModuleDef(file_path="src/main.py", functions=[create_func(name="foo")])

    hashes_to_save = {
        "foo": {"code_structure_hash": "abc", "yaml_content_hash": "def"},
        "bar": {"code_structure_hash": "123", "yaml_content_hash": None},
    }

    # Act: Save
    manager.save_composite_hashes(module, hashes_to_save)

    # Assert: File exists and has correct structure
    sig_path = tmp_path / ".stitcher/signatures/src/main.json"
    assert sig_path.exists()

    with sig_path.open("r") as f:
        data = json.load(f)
        assert data["foo"]["code_structure_hash"] == "abc"
        assert data["foo"]["yaml_content_hash"] == "def"
        assert data["bar"]["code_structure_hash"] == "123"
        assert data["bar"]["yaml_content_hash"] is None

    # Act: Load
    loaded = manager.load_composite_hashes(module)
    assert loaded == hashes_to_save
~~~~~
