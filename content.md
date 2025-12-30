我将生成一个计划来实现以下目标：

1.  **更新核心规格**：在 `stitcher-spec` 中引入新的冲突类型 `DANGLING_DOC` 和解决方案 `PURGE_DOC`。
2.  **增强应用逻辑**：修改 `stitcher-application` 中的 `CheckRunner`，使其能够识别悬空文档作为一种可交互解决的冲突，并能执行清除操作。
3.  **更新通用资源**：在 `stitcher-common` 中为新的交互选项和状态消息添加多语言（中/英）支持。
4.  **实现交互界面**：修改 `stitcher-cli`，在交互式 `check` 流程中为悬空文档提供“清除”选项。

我将通过一系列精确的 `patch_file` 操作来完成这些修改。

## [WIP] feat: 在 check 命令中增加交互式清除悬空文档的功能

### 用户需求
当 `stitcher check` 检测到 YAML 文件中存在代码里没有对应项的“悬空文档”（extra docs）时，用户希望能在交互式流程中直接选择删除这些条目，而不是手动编辑 YAML 文件。

### 评论
这是一个对开发者体验（DX）至关重要的改进。它将 `check` 命令从一个纯粹的诊断工具，转变为一个带有修复能力的实用工具，减少了上下文切换，并使整个“代码-文档”同步工作流更加顺畅。

### 目标
1.  在 `stitcher-spec` 中定义 `DANGLING_DOC` 冲突类型和 `PURGE_DOC` 解决方案。
2.  修改 `CheckRunner` 以识别 `DANGLING_DOC` 冲突，并在用户选择 `PURGE_DOC` 时，从对应的 `.stitcher.yaml` 文件中移除该条目。
3.  在 CLI 交互界面中，为 `DANGLING_DOC` 类型的冲突提供一个新的 "[P]urge" 选项。
4.  为新功能添加相应的 UI 文本和状态报告消息。

### 基本原理
我们将扩展现有的冲突解决机制。首先，通过修改 `stitcher-spec` 来从协议层面定义新的冲突和解决方案。接着，在 `CheckRunner` 中，将原先被视为硬性错误（extra）的悬空文档，重新分类为一种可交互的冲突。然后，扩展 `_apply_resolutions` 方法，使其不仅能处理签名文件的更新，还能处理对文档（`.stitcher.yaml`）文件的修改。最后，在 CLI 层，`TyperInteractionHandler` 将识别这个新的冲突类型，并为其动态渲染一个新的菜单选项，将用户的选择传递回应用核心执行。

### 标签
#intent/build #flow/ready #priority/high
#comp/cli #comp/application #comp/spec #scope/ux #scope/dx
#ai/brainstorm
#task/domain/cli #task/object/interactive-check #task/action/feature-enhancement
#task/state/begin

---
### Script

#### Acts 1: 更新核心规格 (stitcher-spec)

首先，我们在 `models.py` 中定义新的冲突类型和解决方案。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python.old
class ConflictType(str, Enum):
    SIGNATURE_DRIFT = "SIGNATURE_DRIFT"
    CO_EVOLUTION = "CO_EVOLUTION"
    DOC_CONTENT_CONFLICT = "DOC_CONTENT_CONFLICT"


class ResolutionAction(str, Enum):
    RELINK = "RELINK"
    RECONCILE = "RECONCILE"
    HYDRATE_OVERWRITE = "HYDRATE_OVERWRITE"  # Equivalent to --force (Code wins)
    HYDRATE_KEEP_EXISTING = (
        "HYDRATE_KEEP_EXISTING"  # Equivalent to --reconcile (YAML wins)
    )
    SKIP = "SKIP"
    ABORT = "ABORT"
~~~~~
~~~~~python.new
class ConflictType(str, Enum):
    SIGNATURE_DRIFT = "SIGNATURE_DRIFT"
    CO_EVOLUTION = "CO_EVOLUTION"
    DOC_CONTENT_CONFLICT = "DOC_CONTENT_CONFLICT"
    DANGLING_DOC = "DANGLING_DOC"


class ResolutionAction(str, Enum):
    RELINK = "RELINK"
    RECONCILE = "RECONCILE"
    HYDRATE_OVERWRITE = "HYDRATE_OVERWRITE"  # Equivalent to --force (Code wins)
    HYDRATE_KEEP_EXISTING = (
        "HYDRATE_KEEP_EXISTING"  # Equivalent to --reconcile (YAML wins)
    )
    PURGE_DOC = "PURGE_DOC"
    SKIP = "SKIP"
    ABORT = "ABORT"
~~~~~

#### Acts 2: 增强应用逻辑 (stitcher-application)

现在，我们修改 `CheckRunner` 来处理新的冲突类型。

##### 2.1: 在分析阶段识别悬空文档为冲突

我们将修改 `_analyze_file` 方法，将悬空文档（extra）识别为 `DANGLING_DOC` 类型的交互式冲突。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check.py
~~~~~
~~~~~python.old
        # Content checks (unchanged)
        if (self.root_path / module.file_path).with_suffix(".stitcher.yaml").exists():
            doc_issues = self.doc_manager.check_module(module)
            result.warnings["missing"].extend(doc_issues["missing"])
            result.warnings["redundant"].extend(doc_issues["redundant"])
            result.errors["pending"].extend(doc_issues["pending"])
            result.errors["conflict"].extend(doc_issues["conflict"])
            result.errors["extra"].extend(doc_issues["extra"])
~~~~~
~~~~~python.new
        # Content checks
        if (self.root_path / module.file_path).with_suffix(".stitcher.yaml").exists():
            doc_issues = self.doc_manager.check_module(module)
            result.warnings["missing"].extend(doc_issues["missing"])
            result.warnings["redundant"].extend(doc_issues["redundant"])
            result.errors["pending"].extend(doc_issues["pending"])
            result.errors["conflict"].extend(doc_issues["conflict"])
            # extra is now handled as a potential interactive conflict
            for fqn in doc_issues["extra"]:
                unresolved_conflicts.append(
                    InteractionContext(module.file_path, fqn, ConflictType.DANGLING_DOC)
                )
~~~~~

##### 2.2: 实现清除文档的执行逻辑

我们将重构 `_apply_resolutions` 方法，使其能够处理 `PURGE_DOC` 操作，即修改 YAML 文件。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check.py
~~~~~
~~~~~python.old
    def _apply_resolutions(
        self, resolutions: dict[str, list[tuple[str, ResolutionAction]]]
    ):
        for file_path, fqn_actions in resolutions.items():
            module_def = ModuleDef(file_path=file_path)  # Minimal def for path logic
            stored_hashes = self.sig_manager.load_composite_hashes(module_def)
            new_hashes = copy.deepcopy(stored_hashes)

            full_module_def = self.parser.parse(
                (self.root_path / file_path).read_text("utf-8"), file_path
            )
            computed_fingerprints = self.sig_manager.compute_fingerprints(
                full_module_def
            )
            current_yaml_map = self.doc_manager.compute_yaml_content_hashes(
                full_module_def
            )

            for fqn, action in fqn_actions:
                if fqn in new_hashes:
                    fp = new_hashes[fqn]
                    current_fp = computed_fingerprints.get(fqn, Fingerprint())
                    current_code_hash = current_fp.get("current_code_structure_hash")

                    if action == ResolutionAction.RELINK:
                        if current_code_hash:
                            fp["baseline_code_structure_hash"] = str(current_code_hash)
                    elif action == ResolutionAction.RECONCILE:
                        if current_code_hash:
                            fp["baseline_code_structure_hash"] = str(current_code_hash)
                        if fqn in current_yaml_map:
                            fp["baseline_yaml_content_hash"] = str(
                                current_yaml_map[fqn]
                            )

            if new_hashes != stored_hashes:
                self.sig_manager.save_composite_hashes(module_def, new_hashes)
~~~~~
~~~~~python.new
    def _apply_resolutions(
        self, resolutions: dict[str, list[tuple[str, ResolutionAction]]]
    ):
        # --- Handle Signature Updates ---
        sig_updates_by_file = defaultdict(list)
        # --- Handle Doc Purges ---
        purges_by_file = defaultdict(list)

        for file_path, fqn_actions in resolutions.items():
            for fqn, action in fqn_actions:
                if action in [ResolutionAction.RELINK, ResolutionAction.RECONCILE]:
                    sig_updates_by_file[file_path].append((fqn, action))
                elif action == ResolutionAction.PURGE_DOC:
                    purges_by_file[file_path].append(fqn)

        # Apply signature updates
        for file_path, fqn_actions in sig_updates_by_file.items():
            module_def = ModuleDef(file_path=file_path)  # Minimal def for path logic
            stored_hashes = self.sig_manager.load_composite_hashes(module_def)
            new_hashes = copy.deepcopy(stored_hashes)

            full_module_def = self.parser.parse(
                (self.root_path / file_path).read_text("utf-8"), file_path
            )
            computed_fingerprints = self.sig_manager.compute_fingerprints(
                full_module_def
            )
            current_yaml_map = self.doc_manager.compute_yaml_content_hashes(
                full_module_def
            )

            for fqn, action in fqn_actions:
                if fqn in new_hashes:
                    fp = new_hashes[fqn]
                    current_fp = computed_fingerprints.get(fqn, Fingerprint())
                    current_code_hash = current_fp.get("current_code_structure_hash")

                    if action == ResolutionAction.RELINK:
                        if current_code_hash:
                            fp["baseline_code_structure_hash"] = str(current_code_hash)
                    elif action == ResolutionAction.RECONCILE:
                        if current_code_hash:
                            fp["baseline_code_structure_hash"] = str(current_code_hash)
                        if fqn in current_yaml_map:
                            fp["baseline_yaml_content_hash"] = str(
                                current_yaml_map[fqn]
                            )

            if new_hashes != stored_hashes:
                self.sig_manager.save_composite_hashes(module_def, new_hashes)

        # Apply doc purges
        for file_path, fqns_to_purge in purges_by_file.items():
            module_def = ModuleDef(file_path=file_path)
            docs = self.doc_manager.load_docs_for_module(module_def)
            original_len = len(docs)

            for fqn in fqns_to_purge:
                if fqn in docs:
                    del docs[fqn]

            if len(docs) < original_len:
                doc_path = (self.root_path / file_path).with_suffix(".stitcher.yaml")
                if not docs:
                    # If all docs are purged, delete the file
                    if doc_path.exists():
                        doc_path.unlink()
                else:
                    self.doc_manager.adapter.save(doc_path, docs)
~~~~~

##### 2.3: 更新 `run` 方法以处理新流程

最后，我们需要更新 `run` 方法，使其能正确地将用户的 `PURGE_DOC` 选择传递给执行逻辑，处理 `SKIP` 选项，并报告最终结果。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check.py
~~~~~
~~~~~python.old
            for i, context in enumerate(all_conflicts):
                action = chosen_actions[i]
                if action == ResolutionAction.RELINK:
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path]["force_relink"].append(
                        context.fqn
                    )
                elif action == ResolutionAction.RECONCILE:
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path]["reconcile"].append(
                        context.fqn
                    )
                elif action == ResolutionAction.SKIP:
                    for res in all_results:
                        if res.path == context.file_path:
                            error_key = (
                                "signature_drift"
                                if context.conflict_type == ConflictType.SIGNATURE_DRIFT
                                else "co_evolution"
                            )
                            res.errors[error_key].append(context.fqn)
                            break
                elif action == ResolutionAction.ABORT:
                    bus.warning(L.strip.run.aborted)
                    return False

            self._apply_resolutions(dict(resolutions_by_file))

            for res in all_results:
                if res.path in reconciled_results:
                    res.reconciled["force_relink"] = reconciled_results[res.path][
                        "force_relink"
                    ]
                    res.reconciled["reconcile"] = reconciled_results[res.path][
                        "reconcile"
                    ]
~~~~~
~~~~~python.new
            for i, context in enumerate(all_conflicts):
                action = chosen_actions[i]
                if action == ResolutionAction.RELINK:
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path]["force_relink"].append(
                        context.fqn
                    )
                elif action == ResolutionAction.RECONCILE:
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path]["reconcile"].append(
                        context.fqn
                    )
                elif action == ResolutionAction.PURGE_DOC:
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path]["purged"].append(context.fqn)
                elif action == ResolutionAction.SKIP:
                    for res in all_results:
                        if res.path == context.file_path:
                            error_key = {
                                ConflictType.SIGNATURE_DRIFT: "signature_drift",
                                ConflictType.CO_EVOLUTION: "co_evolution",
                                ConflictType.DANGLING_DOC: "extra",
                            }.get(context.conflict_type, "unknown")
                            res.errors[error_key].append(context.fqn)
                            break
                elif action == ResolutionAction.ABORT:
                    bus.warning(L.strip.run.aborted)
                    return False

            self._apply_resolutions(dict(resolutions_by_file))

            for res in all_results:
                if res.path in reconciled_results:
                    res.reconciled["force_relink"] = reconciled_results[res.path][
                        "force_relink"
                    ]
                    res.reconciled["reconcile"] = reconciled_results[res.path][
                        "reconcile"
                    ]
                    res.reconciled["purged"] = reconciled_results[res.path].get(
                        "purged", []
                    )
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check.py
~~~~~
~~~~~python.old
                else:
                    for res in all_results:
                        if res.path == context.file_path:
                            error_key = (
                                "signature_drift"
                                if context.conflict_type == ConflictType.SIGNATURE_DRIFT
                                else "co_evolution"
                            )
                            res.errors[error_key].append(context.fqn)
~~~~~
~~~~~python.new
                else:
                    for res in all_results:
                        if res.path == context.file_path:
                            error_key = {
                                ConflictType.SIGNATURE_DRIFT: "signature_drift",
                                ConflictType.CO_EVOLUTION: "co_evolution",
                                ConflictType.DANGLING_DOC: "extra",
                            }.get(context.conflict_type, "unknown")
                            res.errors[error_key].append(context.fqn)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check.py
~~~~~
~~~~~python.old
            if res.reconciled_count > 0:
                for key in res.reconciled.get("force_relink", []):
                    bus.success(L.check.state.relinked, key=key, path=res.path)
                for key in res.reconciled.get("reconcile", []):
                    bus.success(L.check.state.reconciled, key=key, path=res.path)
~~~~~
~~~~~python.new
            if res.reconciled_count > 0:
                for key in res.reconciled.get("force_relink", []):
                    bus.success(L.check.state.relinked, key=key, path=res.path)
                for key in res.reconciled.get("reconcile", []):
                    bus.success(L.check.state.reconciled, key=key, path=res.path)
                for key in res.reconciled.get("purged", []):
                    bus.success(L.check.state.purged, key=key, path=res.path)
~~~~~

#### Acts 3: 更新多语言资源 (stitcher-common)

我们需要为新的交互选项和状态消息添加英文和中文资源。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/interactive.json
~~~~~
~~~~~json.old
  "reason": {
    "signature_drift": "Reason: Signature has changed, but docs have not (Signature Drift).",
    "co_evolution": "Reason: Both signature and docs have changed (Co-evolution).",
    "doc_content_conflict": "Reason: Source code docstring differs from YAML docstring."
  },
  "option": {
    "relink": { "label": "[F]orce-relink", "desc": "Force-relink new signature with old docs." },
    "reconcile": { "label": "[R]econcile", "desc": "Accept both changes as the new correct state." },
    "overwrite": { "label": "[F]orce overwrite", "desc": "Overwrite YAML with code docs (Code-first)." },
    "keep": { "label": "[R]econcile", "desc": "Keep existing YAML docs (YAML-first)." },
    "skip": { "label": "[S]kip", "desc": "Skip this conflict for now." },
    "abort": { "label": "[A]bort", "desc": "Abort the entire check process." },
    "undo": { "label": "[Z]Undo", "desc": "Go back to the previous conflict." }
  },
~~~~~
~~~~~json.new
  "reason": {
    "signature_drift": "Reason: Signature has changed, but docs have not (Signature Drift).",
    "co_evolution": "Reason: Both signature and docs have changed (Co-evolution).",
    "doc_content_conflict": "Reason: Source code docstring differs from YAML docstring.",
    "dangling_doc": "Reason: Documentation exists in YAML but not in code (Dangling Doc)."
  },
  "option": {
    "relink": { "label": "[F]orce-relink", "desc": "Force-relink new signature with old docs." },
    "reconcile": { "label": "[R]econcile", "desc": "Accept both changes as the new correct state." },
    "overwrite": { "label": "[F]orce overwrite", "desc": "Overwrite YAML with code docs (Code-first)." },
    "keep": { "label": "[R]econcile", "desc": "Keep existing YAML docs (YAML-first)." },
    "purge": { "label": "[P]urge", "desc": "Delete this documentation entry from the YAML file." },
    "skip": { "label": "[S]kip", "desc": "Skip this conflict for now." },
    "abort": { "label": "[A]bort", "desc": "Abort the entire check process." },
    "undo": { "label": "[Z]Undo", "desc": "Go back to the previous conflict." }
  },
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/interactive.json
~~~~~
~~~~~json.old
  "reason": {
    "signature_drift": "原因: 签名已变更，但文档未变 (签名漂移)。",
    "co_evolution": "原因: 签名和文档均已变更 (协同演进)。",
    "doc_content_conflict": "原因: 源代码文档字符串与 YAML 文档字符串不一致。"
  },
  "option": {
    "relink": { "label": "[F]强制重链 (Force-relink)", "desc": "强制将新签名关联到旧文档。" },
    "reconcile": { "label": "[R]调和 (Reconcile)", "desc": "接受双方变更作为新的正确状态。" },
    "overwrite": { "label": "[F]强制覆盖 (Force overwrite)", "desc": "使用代码文档覆盖 YAML (代码优先)。" },
    "keep": { "label": "[R]保留 (Reconcile)", "desc": "保留现有 YAML 文档 (YAML优先)。" },
    "skip": { "label": "[S]跳过 (Skip)", "desc": "暂不处理此冲突。" },
    "abort": { "label": "[A]中止 (Abort)", "desc": "中止整个检查过程。" },
    "undo": { "label": "[Z]撤销 (Undo)", "desc": "返回上一个冲突。" }
  },
~~~~~
~~~~~json.new
  "reason": {
    "signature_drift": "原因: 签名已变更，但文档未变 (签名漂移)。",
    "co_evolution": "原因: 签名和文档均已变更 (协同演进)。",
    "doc_content_conflict": "原因: 源代码文档字符串与 YAML 文档字符串不一致。",
    "dangling_doc": "原因: 文档存在于 YAML 但代码中不存在 (悬空文档)。"
  },
  "option": {
    "relink": { "label": "[F]强制重链 (Force-relink)", "desc": "强制将新签名关联到旧文档。" },
    "reconcile": { "label": "[R]调和 (Reconcile)", "desc": "接受双方变更作为新的正确状态。" },
    "overwrite": { "label": "[F]强制覆盖 (Force overwrite)", "desc": "使用代码文档覆盖 YAML (代码优先)。" },
    "keep": { "label": "[R]保留 (Reconcile)", "desc": "保留现有 YAML 文档 (YAML优先)。" },
    "purge": { "label": "[P]清除 (Purge)", "desc": "从 YAML 文件中删除此文档条目。" },
    "skip": { "label": "[S]跳过 (Skip)", "desc": "暂不处理此冲突。" },
    "abort": { "label": "[A]中止 (Abort)", "desc": "中止整个检查过程。" },
    "undo": { "label": "[Z]撤销 (Undo)", "desc": "返回上一个冲突。" }
  },
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/state.json
~~~~~
~~~~~json.old
{
  "co_evolution": "   - [CO-EVOLUTION] {key} (both code and docs changed; intent unclear)",
  "doc_updated": "   - [DOC UPDATED]  {key} (documentation was improved and auto-reconciled)",
  "reconciled": "   ✅ [RECONCILED]  {key} in {path}",
  "relinked": "   ✅ [RE-LINKED]   {key} in {path}",
  "signature_drift": "   - [SIG DRIFT]   {key} (code changed, docs may be stale)"
}
~~~~~
~~~~~json.new
{
  "co_evolution": "   - [CO-EVOLUTION] {key} (both code and docs changed; intent unclear)",
  "doc_updated": "   - [DOC UPDATED]  {key} (documentation was improved and auto-reconciled)",
  "purged": "   ✅ [PURGED]      {key} in {path}",
  "reconciled": "   ✅ [RECONCILED]  {key} in {path}",
  "relinked": "   ✅ [RE-LINKED]   {key} in {path}",
  "signature_drift": "   - [SIG DRIFT]   {key} (code changed, docs may be stale)"
}
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/state.json
~~~~~
~~~~~json.old
{
  "co_evolution": "   - [协同演进]  {key} (代码和文档均已变更，意图不明确)",
  "doc_updated": "   - [文档更新]  {key} (文档已改进并自动调和)",
  "reconciled": "   ✅ [已调和]    {key} (位于 {path})",
  "relinked": "   ✅ [已重链接]  {key} (位于 {path})",
  "signature_drift": "   - [签名漂移]  {key} (代码已变更，文档可能已过时)"
}
~~~~~
~~~~~json.new
{
  "co_evolution": "   - [协同演进]  {key} (代码和文档均已变更，意图不明确)",
  "doc_updated": "   - [文档更新]  {key} (文档已改进并自动调和)",
  "purged": "   ✅ [已清除]    {key} (位于 {path})",
  "reconciled": "   ✅ [已调和]    {key} (位于 {path})",
  "relinked": "   ✅ [已重链接]  {key} (位于 {path})",
  "signature_drift": "   - [签名漂移]  {key} (代码已变更，文档可能已过时)"
}
~~~~~

#### Acts 4: 实现交互界面 (stitcher-cli)

最后，我们在 CLI 中添加新的交互选项和原因显示。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/handlers.py
~~~~~
~~~~~python.old
            if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
                options.append(
                    SemanticMenuOption(
                        key="f",
                        action=ResolutionAction.RELINK,
                        label_id=L.interactive.option.relink.label,
                        desc_id=L.interactive.option.relink.desc,
                    )
                )
            elif context.conflict_type == ConflictType.CO_EVOLUTION:
~~~~~
~~~~~python.new
            if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
                options.append(
                    SemanticMenuOption(
                        key="f",
                        action=ResolutionAction.RELINK,
                        label_id=L.interactive.option.relink.label,
                        desc_id=L.interactive.option.relink.desc,
                    )
                )
            elif context.conflict_type == ConflictType.DANGLING_DOC:
                options.append(
                    SemanticMenuOption(
                        key="p",
                        action=ResolutionAction.PURGE_DOC,
                        label_id=L.interactive.option.purge.label,
                        desc_id=L.interactive.option.purge.desc,
                    )
                )
            elif context.conflict_type == ConflictType.CO_EVOLUTION:
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/interactive.py
~~~~~
~~~~~python.old
        reason_map = {
            ConflictType.SIGNATURE_DRIFT: L.interactive.reason.signature_drift,
            ConflictType.CO_EVOLUTION: L.interactive.reason.co_evolution,
            ConflictType.DOC_CONTENT_CONFLICT: L.interactive.reason.doc_content_conflict,
        }
~~~~~
~~~~~python.new
        reason_map = {
            ConflictType.SIGNATURE_DRIFT: L.interactive.reason.signature_drift,
            ConflictType.CO_EVOLUTION: L.interactive.reason.co_evolution,
            ConflictType.DOC_CONTENT_CONFLICT: L.interactive.reason.doc_content_conflict,
            ConflictType.DANGLING_DOC: L.interactive.reason.dangling_doc,
        }
~~~~~

### 下一步建议
我们已经完成了核心功能的实现。接下来，建议创建或更新集成测试，以确保：
1.  当存在悬空文档时，`check` 命令确实会进入交互模式并显示“Purge”选项。
2.  选择“Purge”后，对应的 YAML 文件被正确修改。
3.  选择“Skip”后，`check` 命令报告一个“extra”错误并以失败状态退出。
