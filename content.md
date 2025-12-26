我们将实现 `stitcher hydrate` 命令及其核心逻辑，支持冲突检测、强制覆盖和可选的源码剥离 (`--strip`)，并更新 `check` 命令以识别代码与 YAML 文档内容不一致的“冲突”状态。

## [WIP] feat: 实现 stitcher hydrate 命令与冲突检测逻辑

### 用户需求
1.  提供一个 `hydrate` 命令，将 Python 源码中的文档字符串提取并合并到对应的 `.stitcher.yaml` 文件中。
2.  **冲突处理**: 如果代码和 YAML 中都存在文档且内容不一致，应报错（视为冲突），除非用户显式强制覆盖。
3.  **Strip 集成**: 支持在成功同步后自动移除源码中的文档字符串。
4.  **Check 增强**: `stitcher check` 需要能够检测并报告这种“内容不一致”的冲突。

### 评论
这是一个非常实用的功能，符合开发者“就近编写文档”的直觉，同时维护了“YAML 为单一事实来源”的架构原则。它实际上引入了类似 Git 的 `push` (hydrate) 语义。

### 目标
1.  在 `stitcher-common` 中定义 `hydrate` 相关消息和新的 `conflict` 检查消息。
2.  在 `DocumentManager` 中实现 `hydrate_module` 逻辑，处理合并、冲突检测和 Force 策略。
3.  更新 `DocumentManager.check_module` 以支持“双重定义不一致”的冲突检测。
4.  在 `StitcherApp` 和 `CLI` 层暴露 `hydrate` 命令。

### 基本原理
我们将 `hydrate` 视为一种“从代码到 YAML”的单向同步操作。为了保证数据安全，默认情况下它不应覆盖 YAML 中已有的内容（除非内容完全一致）。冲突检测逻辑将被复用到 `check` 命令中，确保在 CI/CD 流程中也能捕获文档的不同步状态。

### 标签
#intent/build #flow/ready #priority/high #comp/cli #comp/runtime #concept/sync #scope/ux #ai/instruct #task/domain/cli #task/object/command-hydrate #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 定义消息资产 (Common)

我们需要为 `hydrate` 命令定义一套全新的反馈消息，并在 `check` 模块中增加关于冲突的描述。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/hydrate/main.json
~~~~~
~~~~~json
{
    "hydrate.run.start": "💧 Starting hydration process...",
    "hydrate.file.success": "💧 Hydrated {count} new docstrings from: {path}",
    "hydrate.run.complete": "✨ Hydration complete. {count} files updated.",
    "hydrate.run.no_changes": "🤔 No new docstrings found in source code to hydrate.",
    "hydrate.error.conflict": "❌ Conflict in {path}: Docstring for '{key}' exists in both source code and YAML but differs. Use --force to overwrite YAML.",
    "hydrate.run.conflict": "🚫 Hydration aborted due to conflicts in {count} files."
}
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/main.json
~~~~~
~~~~~json.old
    "check.issue.missing": "   - [MISSING] {key} (present in code, missing in YAML)",
    "check.issue.extra": "   - [EXTRA]   {key} (present in YAML, missing in code)",
    "check.run.success": "✨ All checks passed. Documentation is in sync.",
~~~~~
~~~~~json.new
    "check.issue.missing": "   - [MISSING] {key} (present in code, missing in YAML)",
    "check.issue.extra": "   - [EXTRA]   {key} (present in YAML, missing in code)",
    "check.issue.conflict": "   - [CONFLICT] {key} (content differs between code and YAML)",
    "check.run.success": "✨ All checks passed. Documentation is in sync.",
~~~~~

#### Acts 2: 扩展 DocumentManager (Application)

这是核心逻辑所在。我们需要实现 `hydrate_module` 并更新 `check_module`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
    def check_module(self, module: ModuleDef) -> Dict[str, set]:
        """
        Compares module structure against external docs.
        Returns a dict of issues: {'missing': set(...), 'extra': set(...)}
        """
        # 1. Get keys from Code
        public_keys = self._extract_keys(module, public_only=True)
        all_keys = self._extract_keys(module, public_only=False)

        # 2. Get keys from YAML
        yaml_docs = self.load_docs_for_module(module)
        doc_keys = set(yaml_docs.keys())

        # 3. Diff
        # Missing: Must be public AND not in YAML
        missing = public_keys - doc_keys

        # Extra: In YAML AND not in Code (at all, even private)
        extra = doc_keys - all_keys

        # Allow __doc__ to be present in YAML even if not explicitly demanded by code analysis
        extra.discard("__doc__")

        return {"missing": missing, "extra": extra}
~~~~~
~~~~~python.new
    def check_module(self, module: ModuleDef) -> Dict[str, set]:
        """
        Compares module structure against external docs.
        Returns a dict of issues: {'missing': set(...), 'extra': set(...), 'conflict': set(...)}
        """
        # 1. Get keys from Code
        public_keys = self._extract_keys(module, public_only=True)
        all_keys = self._extract_keys(module, public_only=False)
        
        # We also need the actual content to check for conflicts
        source_docs = self.flatten_module_docs(module)

        # 2. Get keys from YAML
        yaml_docs = self.load_docs_for_module(module)
        doc_keys = set(yaml_docs.keys())

        # 3. Diff
        # Missing: Must be public AND not in YAML
        missing = public_keys - doc_keys

        # Extra: In YAML AND not in Code (at all, even private)
        extra = doc_keys - all_keys

        # Conflict: In BOTH, but content differs
        conflict = set()
        common_keys = source_docs.keys() & yaml_docs.keys()
        for key in common_keys:
            # Simple string comparison. 
            # In future we might want to normalize whitespace, but exact match is safer for now.
            if source_docs[key] != yaml_docs[key]:
                conflict.add(key)

        # Allow __doc__ to be present in YAML even if not explicitly demanded by code analysis
        extra.discard("__doc__")

        return {"missing": missing, "extra": extra, "conflict": conflict}

    def hydrate_module(
        self, module: ModuleDef, force: bool = False
    ) -> Dict[str, Any]:
        """
        Merges docstrings from Code into YAML.
        Returns a dict with 'success': bool, 'updated_keys': list, 'conflicts': list
        """
        source_docs = self.flatten_module_docs(module)
        if not source_docs:
            return {"success": True, "updated_keys": [], "conflicts": []}

        yaml_docs = self.load_docs_for_module(module)
        
        updated_keys = []
        conflicts = []
        
        # We will build a new dict to save, starting with existing YAML docs
        new_yaml_docs = yaml_docs.copy()
        
        for key, source_content in source_docs.items():
            if key not in yaml_docs:
                # New docstring, safe to add
                new_yaml_docs[key] = source_content
                updated_keys.append(key)
            elif yaml_docs[key] != source_content:
                # Conflict
                if force:
                    new_yaml_docs[key] = source_content
                    updated_keys.append(key)
                else:
                    conflicts.append(key)
            # Else: Content is identical, no action needed
            
        if conflicts:
            return {"success": False, "updated_keys": [], "conflicts": conflicts}
            
        if updated_keys:
            # Determine output path (same logic as save_docs_for_module)
            module_path = self.root_path / module.file_path
            output_path = module_path.with_suffix(".stitcher.yaml")
            self.adapter.save(output_path, new_yaml_docs)
            
        return {"success": True, "updated_keys": updated_keys, "conflicts": []}
~~~~~

#### Acts 3: 扩展 StitcherApp (Application)

实现 `run_hydrate` 方法，编排扫描、水合和可选的剥离过程。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        if failed_files > 0:
            bus.error(L.check.run.fail, count=failed_files)
            return False

        if total_warnings > 0:
            bus.success(L.check.run.success_with_warnings, count=total_warnings)
        else:
            bus.success(L.check.run.success)
        return True

    def run_strip(self) -> List[Path]:
~~~~~
~~~~~python.new
        if failed_files > 0:
            bus.error(L.check.run.fail, count=failed_files)
            return False

        if total_warnings > 0:
            bus.success(L.check.run.success_with_warnings, count=total_warnings)
        else:
            bus.success(L.check.run.success)
        return True

    def run_hydrate(self, strip: bool = False, force: bool = False) -> bool:
        """
        Extracts docstrings from source code and merges them into YAML files.
        If 'strip' is True, removes docstrings from source files after successful hydration.
        """
        bus.info(L.hydrate.run.start)
        config = load_config_from_path(self.root_path)
        modules = self._scan_files(self._get_files_from_config(config))
        
        if not modules:
            bus.warning(L.warning.no_files_or_plugins_found)
            return True

        updated_files_count = 0
        conflict_files_count = 0
        
        # Phase 1: Hydrate (Update YAMLs)
        # We process all files. If any file has conflicts, we fail the whole operation
        # (or at least report it). But 'strip' should definitely check per-file success.
        
        files_to_strip = []

        for module in modules:
            result = self.doc_manager.hydrate_module(module, force=force)
            
            if not result["success"]:
                conflict_files_count += 1
                for conflict_key in result["conflicts"]:
                    bus.error(
                        L.hydrate.error.conflict, 
                        path=module.file_path, 
                        key=conflict_key
                    )
                continue
            
            # If successful (or no changes needed), we consider this file "clean"/synced.
            if result["updated_keys"]:
                updated_files_count += 1
                bus.success(
                    L.hydrate.file.success, 
                    path=module.file_path, 
                    count=len(result["updated_keys"])
                )
            
            # If successful, this file is a candidate for stripping
            files_to_strip.append(module)

        if conflict_files_count > 0:
            bus.error(L.hydrate.run.conflict, count=conflict_files_count)
            return False
            
        if updated_files_count == 0:
            bus.info(L.hydrate.run.no_changes)
        else:
            bus.success(L.hydrate.run.complete, count=updated_files_count)

        # Phase 2: Strip (Modify Code)
        if strip and files_to_strip:
            # We reuse the logic from run_strip, but only for the specific files
            # that were successfully processed/hydrated.
            # However, run_strip scans from config. We can just invoke the transform here directly.
            # Or simpler: Call run_strip() but limit it? 
            # run_strip currently re-scans everything. 
            # Let's implement a targeted strip logic here or refactor run_strip.
            # For MVP, let's just do the strip logic inline here for the list of modules.
            
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

        return True

    def run_strip(self) -> List[Path]:
~~~~~

这里还需要微调 `run_check` 以处理新的 conflict 字段。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
            missing = doc_issues["missing"]
            extra = doc_issues["extra"]
            mismatched = sig_issues

            error_count = len(extra) + len(mismatched)
            warning_count = len(missing)
            total_issues = error_count + warning_count
~~~~~
~~~~~python.new
            missing = doc_issues["missing"]
            extra = doc_issues["extra"]
            conflict = doc_issues["conflict"]
            mismatched = sig_issues

            error_count = len(extra) + len(mismatched) + len(conflict)
            warning_count = len(missing)
            total_issues = error_count + warning_count
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
            for key in sorted(list(missing)):
                bus.warning(L.check.issue.missing, key=key)
            for key in sorted(list(extra)):
                bus.error(L.check.issue.extra, key=key)
            for key in sorted(list(mismatched.keys())):
                bus.error(L.check.issue.mismatch, key=key)
~~~~~
~~~~~python.new
            for key in sorted(list(missing)):
                bus.warning(L.check.issue.missing, key=key)
            for key in sorted(list(extra)):
                bus.error(L.check.issue.extra, key=key)
            for key in sorted(list(conflict)):
                bus.error(L.check.issue.conflict, key=key)
            for key in sorted(list(mismatched.keys())):
                bus.error(L.check.issue.mismatch, key=key)
~~~~~

#### Acts 4: 暴露 CLI 命令 (CLI)

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python.old
@app.command()
def eject():
    """Inject docstrings from .stitcher.yaml files back into code."""
    if not typer.confirm(bus.render_to_string(L.eject.run.confirm)):
        bus.warning(L.eject.run.aborted)
        raise typer.Abort()

    project_root = Path.cwd()
    app_instance = StitcherApp(root_path=project_root)
    app_instance.run_eject()
~~~~~
~~~~~python.new
@app.command()
def eject():
    """Inject docstrings from .stitcher.yaml files back into code."""
    if not typer.confirm(bus.render_to_string(L.eject.run.confirm)):
        bus.warning(L.eject.run.aborted)
        raise typer.Abort()

    project_root = Path.cwd()
    app_instance = StitcherApp(root_path=project_root)
    app_instance.run_eject()


@app.command()
def hydrate(
    strip: bool = typer.Option(
        False, "--strip", help="Remove docstrings from source code after hydration."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite YAML content if it differs from source code."
    ),
):
    """
    Extract new docstrings from source code and merge them into .stitcher.yaml.
    """
    project_root = Path.cwd()
    app_instance = StitcherApp(root_path=project_root)
    success = app_instance.run_hydrate(strip=strip, force=force)
    if not success:
        raise typer.Exit(code=1)
~~~~~

### 下一步建议
我们已经实现了 `hydrate` 的所有核心逻辑和 CLI 接入点。接下来，我们应该添加针对 `hydrate` 的集成测试，涵盖以下场景：
1.  **正常 Hydrate**: 代码有新文档，YAML 自动更新。
2.  **冲突检测**: 代码文档与 YAML 已有文档不同，预期失败。
3.  **Force 覆盖**: 使用 `--force` 解决上述冲突。
4.  **Strip 联动**: 验证 `--strip` 选项是否在 hydration 成功后清理了源码。

我将为这些场景编写测试用例。
