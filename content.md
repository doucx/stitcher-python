## [WIP] fix: 修复 CheckRunner 中的 Pointer 匹配逻辑和行为回退

### 用户需求

1.  修复 `CheckRunner` 中因 `SemanticPointer` 字符串化匹配失败而导致的交互流程中断。
2.  恢复旧版 `CheckAnalyzer` 的行为：即使没有 YAML 文件（但有 Baseline），也应该检测 `signature_drift`。这对于保持测试兼容性至关重要。

### 评论

我们发现了两个关键问题。
首先，`str(pointer)` 匹配不仅脆弱，而且显然已经失效。我们将改为直接比较 `SemanticPointer` 对象。这需要 `CheckRunner` 能够直接访问 `stitcher-spec` 或 `stitcher-analysis` 中定义的原始 Pointer 对象。
其次，`SignatureRule` 过于严格的 `exists_in_yaml` 检查导致了行为回退。虽然从纯洁性角度看它是对的，但为了兼容现有测试（以及某些边缘用例），我们需要放宽这个限制，或者修改测试。考虑到“不改变现有业务行为”的原则，我们应该修改规则。

### 目标

1.  修改 `CheckRunner`，使用对象相等性检查 (`violation.kind == L.check.state.signature_drift`) 代替字符串匹配。
2.  修改 `stitcher-analysis` 的 `SignatureRule`，移除 `if not state.exists_in_yaml: continue` 的限制，只要有 `baseline` 就进行检查。

### 标签

#intent/fix #flow/ready #priority/critical #comp/application #comp/analysis #scope/core #ai/instruct #task/domain/testing #task/object/check-runner #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `SignatureRule` (放宽检查)

为了兼容旧行为，只要存在 Baseline Hash，我们就应该进行签名检查，即使 YAML 文件丢失（这本身是一个 Warning，但不应阻止 Drift 检测）。

~~~~~act
patch_file
packages/stitcher-analysis/src/stitcher/analysis/rules/consistency/signature.py
~~~~~
~~~~~python.old
        for fqn, state in states.items():
            # Skip if not tracked in YAML (not our responsibility)
            if not state.exists_in_yaml:
                continue

            # Skip if not in code (handled by ExistenceRule/Dangling)
~~~~~
~~~~~python.new
        for fqn, state in states.items():
            # Legacy Compatibility: Even if not tracked in YAML, if we have a baseline,
            # we should check for drift. This supports workflows where init generated
            # signatures but no docs were created (e.g. empty docs).
            
            # Skip if not in code (handled by ExistenceRule/Dangling)
~~~~~

#### Acts 2: 修复 `CheckRunner` 的 Pointer 匹配

我们将移除字符串转换，直接使用 Pointer 对象。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python
from typing import List, Tuple
from pathlib import Path

from needle.pointer import L
from stitcher.spec import (
    ModuleDef,
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
    DifferProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.spec.interaction import InteractionContext
from stitcher.app.types import FileCheckResult

from .protocols import (
    CheckResolverProtocol,
    CheckReporterProtocol,
)
from .subject import IndexCheckSubjectAdapter, ASTCheckSubjectAdapter
from stitcher.analysis.engines.consistency.engine import create_consistency_engine
from stitcher.analysis.schema import (
    FileCheckResult as AnalysisFileCheckResult,
)


class CheckRunner:
    def __init__(
        self,
        doc_manager: DocumentManagerProtocol,
        sig_manager: SignatureManagerProtocol,
        fingerprint_strategy: FingerprintStrategyProtocol,
        index_store: IndexStoreProtocol,
        differ: DifferProtocol,
        resolver: CheckResolverProtocol,
        reporter: CheckReporterProtocol,
        root_path: Path,
    ):
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager
        self.fingerprint_strategy = fingerprint_strategy
        self.index_store = index_store
        self.root_path = root_path

        self.engine = create_consistency_engine(differ=differ)
        self.resolver = resolver
        self.reporter = reporter

    def _translate_results(
        self, analysis_result: AnalysisFileCheckResult
    ) -> Tuple[FileCheckResult, List[InteractionContext]]:
        legacy_result = FileCheckResult(path=analysis_result.path)
        conflicts: List[InteractionContext] = []

        # Object-based mapping
        # Note: We rely on SemanticPointer.__hash__ and __eq__ working correctly.
        KIND_TO_LEGACY_MAP = {
            L.check.issue.conflict: ("errors", "conflict"),
            L.check.state.signature_drift: ("errors", "signature_drift"),
            L.check.state.co_evolution: ("errors", "co_evolution"),
            L.check.issue.extra: ("errors", "extra"),
            L.check.issue.pending: ("errors", "pending"),
            L.check.issue.missing: ("warnings", "missing"),
            L.check.issue.redundant: ("warnings", "redundant"),
            L.check.file.untracked: ("warnings", "untracked"),
            L.check.file.untracked_with_details: ("warnings", "untracked_detailed"),
            L.check.state.doc_updated: ("infos", "doc_improvement"),
        }

        INTERACTIVE_VIOLATIONS = {
            L.check.state.signature_drift,
            L.check.state.co_evolution,
            L.check.issue.extra,
            L.check.issue.conflict,
        }

        for violation in analysis_result.violations:
            # Direct object lookup
            if violation.kind in KIND_TO_LEGACY_MAP:
                category, key = KIND_TO_LEGACY_MAP[violation.kind]
                target_dict = getattr(legacy_result, category)
                
                if violation.kind == L.check.file.untracked_with_details:
                    keys = violation.context.get("keys", [])
                    target_dict[key].extend(keys)
                else:
                    target_dict[key].append(violation.fqn)

            if violation.kind in INTERACTIVE_VIOLATIONS:
                conflicts.append(
                    InteractionContext(
                        file_path=legacy_result.path,
                        fqn=violation.fqn,
                        violation_type=violation.kind,
                        signature_diff=violation.context.get("signature_diff"),
                        doc_diff=violation.context.get("doc_diff"),
                    )
                )

        return legacy_result, conflicts

    def analyze_paths(
        self, file_paths: List[str]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
        all_results: List[FileCheckResult] = []
        all_conflicts: List[InteractionContext] = []

        for file_path in file_paths:
            subject = IndexCheckSubjectAdapter(
                file_path,
                self.index_store,
                self.doc_manager,
                self.sig_manager,
                self.root_path,
            )
            analysis_result = self.engine.analyze(subject)
            legacy_result, conflicts = self._translate_results(analysis_result)
            all_results.append(legacy_result)
            all_conflicts.extend(conflicts)

        return all_results, all_conflicts

    def analyze_batch(
        self, modules: List[ModuleDef]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
        all_results: List[FileCheckResult] = []
        all_conflicts: List[InteractionContext] = []

        for module in modules:
            subject = ASTCheckSubjectAdapter(
                module,
                self.doc_manager,
                self.sig_manager,
                self.fingerprint_strategy,
                self.root_path,
            )
            analysis_result = self.engine.analyze(subject)
            legacy_result, conflicts = self._translate_results(analysis_result)
            all_results.append(legacy_result)
            all_conflicts.extend(conflicts)

        return all_results, all_conflicts

    def auto_reconcile_docs(
        self, results: List[FileCheckResult], modules: List[ModuleDef]
    ):
        self.resolver.auto_reconcile_docs(results, modules)

    def resolve_conflicts(
        self,
        results: List[FileCheckResult],
        conflicts: List[InteractionContext],
        force_relink: bool = False,
        reconcile: bool = False,
    ) -> bool:
        return self.resolver.resolve_conflicts(
            results, conflicts, force_relink, reconcile
        )

    def reformat_all(self, modules: List[ModuleDef]):
        self.resolver.reformat_all(modules)

    def report(self, results: List[FileCheckResult]) -> bool:
        return self.reporter.report(results)
~~~~~

### 下一步建议

这次修复涵盖了两个主要失效点。请重新运行测试。
如果 `test_ghost_keys_trigger_extra_error` 仍然报告重复项，那将是一个非常孤立的、只与 `IndexStore` 或 `Scanner` 在测试环境下的行为有关的问题，我们可以随后单独处理。但绝大多数测试现在应该能通过了。
