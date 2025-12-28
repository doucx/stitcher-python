这是一个非常严重的回归。正如你所指出的，新的 `_analyze_file` 几乎完全替换了原有的逻辑，导致原本由 `doc_manager.check_module` 处理的“文档内容一致性”检查（Conflict, Missing, Pending 等）全部丢失。这是不可接受的。

此外，大量测试用例因为命令行参数变更（`update_signatures` 被移除）和错误类型变更（`mismatch` 变为 `signature_drift` 等）而失效。

我将分两步修复这个问题：
1.  **修复核心逻辑 (`core.py`)**：恢复 `_analyze_file` 中的 `doc_manager.check_module` 调用，并正确合并两种检查逻辑（状态机 + 内容检查）。同时调整 `doc_improvement` 的处理方式，使其作为 INFO 而非 Warning，以符合“静默通过/成功退出”的预期。
2.  **批量修复测试用例**：使用 `write_file` 彻底更新过时的集成测试文件，使其匹配新的参数和错误类型。

## [WIP] fix: 恢复文档内容检查并适配新状态机测试

### 错误分析
1.  **功能丢失**: `StitcherApp._analyze_file` 中丢失了 `self.doc_manager.check_module(module)` 调用，导致 `check` 命令不再验证代码与 YAML 文档内容的同步性（如 docstring 内容冲突）。
2.  **状态判定错误**: `doc_improvement` 目前被归类为 Warning，导致 `is_clean` 为 False，进而导致 `run_check` 报告 `success_with_warnings` 而非预期的 `success`。
3.  **测试过时**: `test_check_signatures.py` 等文件仍在使用已删除的 CLI 参数 `update_signatures`，且断言旧的错误 ID `mismatch`。

### 解决方案
1.  **重写 `StitcherApp`**:
    *   在 `_analyze_file` 开头调用 `doc_manager.check_module`。
    *   将结果合并到 `FileCheckResult` 中。
    *   引入 `infos` 列表到 `FileCheckResult`，将 `doc_improvement` 移入其中，不影响 `is_clean` 状态。
2.  **重写测试**:
    *   更新 `tests/integration/test_check_signatures.py` 以使用 `force_relink`。
    *   更新 `tests/integration/test_check_state_machine.py` 以匹配新的 INFO 行为。
    *   修正 `test_check_command.py` 中的断言。

### 标签
#intent/fix #flow/ready #priority/high #comp/application #comp/tests #scope/core #ai/instruct #task/domain/validation #task/object/state-machine #task/state/continue

---
### Script

#### Acts 1: 修复 `StitcherApp` 逻辑

恢复 `check_module` 调用，并优化 `doc_improvement` 的处理。

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

        # 1. Content Checks (Missing, Extra, Conflict, Pending)
        # This populates errors/warnings for content-level issues.
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
            # 'extra' from check_module refers to keys in YAML not in Code.
            # We will handle 'extra' in the state machine loop below to be consistent
            # with hash checking, or merge them. check_module's extra is accurate for keys.
            if doc_issues["extra"]:
                result.errors["extra"].extend(doc_issues["extra"])

        # 2. State Machine Checks (Signature Drift, Co-evolution, Doc Improvement)
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

            # Case: Extra (In Storage, Not in Code)
            if not s_current and s_stored:
                # doc_manager.check_module already reports 'extra' for keys in YAML.
                # Here we ensure it's removed from hash storage.
                # We don't need to report it again if doc_manager did, but cleaning up is good.
                if fqn in new_hashes_map:
                    new_hashes_map.pop(fqn, None)
                continue

            # Case: New (In Code, Not in Storage)
            if s_current and not s_stored:
                if is_tracked:
                    # If it's a new function in a tracked file, check_module reports 'missing' or 'pending'.
                    # We just need to initialize its hash.
                    new_hashes_map[fqn] = {
                        "signature_hash": s_current,
                        "document_hash": d_current,
                    }
                continue

            # Case: Existing (In Code and Storage)
            s_match = s_current == s_stored
            d_match = d_current == d_stored

            if s_match and d_match:
                pass  # Synchronized
            elif s_match and not d_match:
                # Doc Improvement: INFO, Auto-reconcile
                result.infos["doc_improvement"].append(fqn)
                if fqn in new_hashes_map:
                    new_hashes_map[fqn]["document_hash"] = d_current
                result.auto_reconciled_count += 1
            elif not s_match and d_match:
                # Signature Drift
                if force_relink:
                    result.reconciled["force_relink"].append(fqn)
                    if fqn in new_hashes_map:
                        new_hashes_map[fqn]["signature_hash"] = s_current
                else:
                    result.errors["signature_drift"].append(fqn)
            elif not s_match and not d_match:
                # Co-evolution
                if reconcile:
                    result.reconciled["reconcile"].append(fqn)
                    new_hashes_map[fqn] = {
                        "signature_hash": s_current,
                        "document_hash": d_current,
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
                    # Even if clean, report Auto-reconciled (INFO)
                    if res.auto_reconciled_count > 0:
                        bus.info(
                            f"[INFO] Automatically updated {res.auto_reconciled_count} documentation hash(es) in {res.path}"
                        )
                    continue

                # Report Reconciled Actions (Success)
                if res.reconciled_count > 0:
                    for key in res.reconciled.get("force_relink", []):
                        bus.success(
                            f"[OK] Re-linked signature for '{key}' in {res.path}"
                        )
                    for key in res.reconciled.get("reconcile", []):
                        bus.success(
                            f"[OK] Reconciled changes for '{key}' in {res.path}"
                        )
                # Report Auto-reconciled (INFO) - also here if file had other issues
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

                # Report Specific Issues
                for key in sorted(res.errors["extra"]):
                    bus.error(L.check.issue.extra, key=key)
                for key in sorted(res.errors["signature_drift"]):
                    bus.error(
                        f"[Signature Drift] '{key}': Code changed, docs may be stale."
                    )
                for key in sorted(res.errors["co_evolution"]):
                    bus.error(
                        f"[Co-evolution] '{key}': Both code and docs changed; intent unclear."
                    )
                for key in sorted(res.errors["conflict"]):
                    bus.error(L.check.issue.conflict, key=key)
                for key in sorted(res.errors["pending"]):
                    bus.error(L.check.issue.pending, key=key)

                for key in sorted(res.warnings["missing"]):
                    bus.warning(L.check.issue.missing, key=key)
                for key in sorted(res.warnings["redundant"]):
                    bus.warning(L.check.issue.redundant, key=key)
                for key in sorted(res.warnings["untracked_key"]):
                    bus.warning(
                        f"[Untracked Code] '{key}': New public API without documentation."
                    )
                
                # Infos are just printed, usually
                for key in sorted(res.infos["doc_improvement"]):
                    bus.info(f"[Doc Updated] '{key}': Documentation was improved.")

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

#### Acts 2: 修复 `test_check_signatures.py`

更新为使用 `force_relink` 并断言新的错误消息。

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
    # 1. Setup Initial Workspace
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

    # 2. Run Init (Baseline)
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    _assert_no_errors(spy_bus)
    spy_bus.assert_id_called(L.init.run.complete, level="success")

    # 3. Modify Code
    modified_code = dedent("""
    def process(value: str) -> int:
        \"\"\"Process a string (Changed).\"\"\"
        return len(value) * 2
    """).strip()
    (project_root / "src/processor.py").write_text(modified_code, encoding="utf-8")

    # 4. Run Check
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 5. Assertions
    assert success is False, "Check passed but should have failed due to signature mismatch"
    # New error message format for Signature Drift
    msg = f"[Signature Drift] 'process': Code changed, docs may be stale."
    spy_bus.assert_id_called(msg, level="error")


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

    # 1. Run Init to set baseline
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # 2. Modify Code
    (project_root / "src/main.py").write_text("def func(a: str): ...")

    # 3. Run Generate
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_from_config()

    # 4. Run Check - it should now FAIL because generate did not update anything.
    spy_bus_check = SpyBus()
    with spy_bus_check.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert not success, "Check passed, but it should have failed."
    msg = f"[Signature Drift] 'func': Code changed, docs may be stale."
    spy_bus_check.assert_id_called(msg, level="error")


def test_check_with_force_relink_reconciles_changes(tmp_path, monkeypatch):
    """
    Verify the complete workflow of reconciling signature changes with `check --force-relink`.
    """
    # 1. Arrange: Setup and Init to establish a baseline.
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func(a: int):\n    """Doc."""\n    ...')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # 2. Modify the code to create a signature mismatch (Signature Drift).
    # Docstring in code matches YAML docstring, so no content conflict.
    (project_root / "src/main.py").write_text('def func(a: str):\n    """Doc."""\n    ...')

    # 3. Act I: Run check with the --force-relink flag
    spy_bus_reconcile = SpyBus()
    with spy_bus_reconcile.patch(monkeypatch, "stitcher.app.core.bus"):
        success_reconcile = app.run_check(force_relink=True)

    # 4. Assert I: The reconciliation check should succeed and report the update
    assert success_reconcile is True, "Check with --force-relink failed"
    spy_bus_reconcile.assert_id_called(f"[OK] Re-linked signature for 'func' in src/main.py", level="success")
    
    # 5. Act II: Run a normal check again to verify the baseline was updated
    spy_bus_verify = SpyBus()
    with spy_bus_verify.patch(monkeypatch, "stitcher.app.core.bus"):
        success_verify = app.run_check()

    # 6. Assert II: The verification check should now pass cleanly
    assert success_verify is True, "Verification check failed after reconciliation"
    spy_bus_verify.assert_id_called(L.check.run.success, level="success")
~~~~~

#### Acts 3: 修复 `test_check_state_machine.py`

更新 `test_state_doc_improvement_auto_reconciled` 以匹配新的 INFO 行为。

~~~~~act
patch_file
tests/integration/test_check_state_machine.py
~~~~~
~~~~~python
    # 4. Assert: Should pass, report doc improvement, and update doc hash
    assert success is True
    spy_bus.assert_id_called(f"[Doc Updated] 'func': Documentation was improved.", level="info")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
~~~~~
~~~~~python
    # 4. Assert: Should pass, report doc improvement, and update doc hash
    assert success is True
    spy_bus.assert_id_called(f"[Doc Updated] 'func': Documentation was improved.", level="info")
    # Because there are auto-reconciled items (infos), check reports clean success
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
~~~~~
