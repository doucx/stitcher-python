感谢你提供如此精确的 `pyright` 和 `pytest` 错误报告。这清晰地表明我之前的计划存在缺陷，特别是在处理类型命名冲突和导入路径方面。

我将立即生成一个修复计划来解决这些问题。

## [WIP] fix: 修正 CheckRunner 集成中的类型冲突和循环导入

### 错误分析

**1. 循环导入 (`ImportError`)**:
`pytest` 报告的 `ImportError` 指出 `create_consistency_engine` 无法从 `stitcher.analysis.engines.consistency` 中导入，原因是“部分初始化的模块”。这是典型的由 `__init__.py` 文件（“barrel exports”）引起的脆弱导入链问题。当 `runner.py` 尝试通过 `...consistency.__init__` 导入时，该 `__init__.py` 文件又去导入 `.engine`，在复杂的依赖关系下可能形成循环。
*   **解决方案**: 我们将绕过脆弱的 `__init__.py` 文件，直接从其源模块 `stitcher.analysis.engines.consistency.engine` 导入 `create_consistency_engine`。这可以明确地断开任何潜在的导入环路。

**2. 类型冲突 (`pyright` errors)**:
`pyright` 的错误是本次重构的核心障碍。问题根源在于我们现在有两个同名为 `FileCheckResult` 的类：
*   **旧版**: `stitcher.app.types.FileCheckResult` (一个 dataclass，包含 `errors`, `warnings` 等字典)。
*   **新版**: `stitcher.analysis.schema.results.FileCheckResult` (一个 dataclass，包含 `violations` 列表)。

在 `CheckRunner` 的 `_translate_results` 方法中，我错误地使用了不明确的类型注解。Python 解析器将 `analysis_result: "FileCheckResult"` 注解解析为了本地（旧版）的 `FileCheckResult`，但实际传入的却是分析引擎返回的新版对象，导致类型不匹配。
*   **解决方案**:
    1.  在 `runner.py` 中，我们将为新版的 `FileCheckResult` 创建一个明确的导入别名，例如 `AnalysisFileCheckResult`。
    2.  我们将使用这个别名来正确注解 `_translate_results` 方法的输入参数，从而解决类型检查错误。

**3. 悬空导入 (`pyright` error)**:
`core.py` 中的 `Import ".runners.check.analyzer" could not be resolved` 错误是我在删除 `analyzer.py` 文件后，忘记移除其对应的 `import` 语句导致的。
*   **解决方案**: 删除该行 `import` 语句。

### 用户需求

修复 `stitcher-application` 在集成 `stitcher-analysis` 后出现的 `ImportError` 和 `pyright` 类型检查错误，使代码能够正确运行并通过静态分析。

### 评论

这次修复是重构过程中的必要校准。它暴露了增量集成中常见的挑战：命名空间冲突和脆弱的导入模式。通过采用别名导入和直接模块导入等健壮的编程实践，我们可以构建一个更清晰、更有弹性的架构，为后续的重构扫清障碍。

### 目标

1.  修改 `stitcher.app.core`，移除对已删除的 `CheckAnalyzer` 的导入。
2.  修改 `stitcher.app.runners.check.runner`：
    *   修复导入路径，直接从 `.engine` 模块导入 `create_consistency_engine`。
    *   通过别名导入解决 `FileCheckResult` 的命名冲突。
    *   修正 `_translate_results` 方法的类型注解，使其通过 `pyright` 检查。

### 基本原理

我们将对两个关键文件进行精确的外科手术式修复。在 `core.py` 中，我们删除无效的导入。在 `runner.py` 中，我们调整导入语句以解决循环导入和类型命名冲突，并更新函数签名以反映正确的类型契约。这使得 `CheckRunner` 能够正确地接收来自 `analysis` 包的数据，并将其转换为 `application` 包中其他组件（如 `Resolver`）所期望的格式，从而恢复端到端链路的类型安全和可运行性。

### 标签

#intent/fix #flow/ready #priority/critical #comp/application #comp/analysis #concept/type-safety #scope/core #ai/instruct #task/domain/testing #task/object/check-command #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `core.py` 中的悬空导入

我们将移除对已删除的 `analyzer.py` 的引用。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from .runners import (
    CheckRunner,
    InitRunner,
    PumpRunner,
    TransformRunner,
    CoverageRunner,
    RefactorRunner,
    IndexRunner,
)
from .runners.check.analyzer import CheckAnalyzer
from .runners.check.resolver import CheckResolver
~~~~~
~~~~~python.new
from .runners import (
    CheckRunner,
    InitRunner,
    PumpRunner,
    TransformRunner,
    CoverageRunner,
    RefactorRunner,
    IndexRunner,
)
from .runners.check.resolver import CheckResolver
~~~~~

#### Acts 2: 修复 `runner.py` 中的导入和类型注解

这是解决核心问题的地方。我们将更新导入、添加别名并修正类型注解。

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
        # Keep services needed by adapter
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager
        self.fingerprint_strategy = fingerprint_strategy
        self.index_store = index_store
        self.root_path = root_path

        # Injected sub-components
        self.engine = create_consistency_engine(differ=differ)
        self.resolver = resolver
        self.reporter = reporter

    def _translate_results(
        self, analysis_result: AnalysisFileCheckResult
    ) -> Tuple[FileCheckResult, List[InteractionContext]]:
        # This is the adapter logic. It translates the new, unified `FileCheckResult`
        # from the analysis engine into the old structures expected by the resolver/reporter.

        legacy_result = FileCheckResult(path=analysis_result.path)
        conflicts: List[InteractionContext] = []

        # Mapping from new Violation 'kind' to old result dict keys
        KIND_TO_LEGACY_MAP = {
            # Errors
            str(L.check.issue.conflict): ("errors", "conflict"),
            str(L.check.state.signature_drift): ("errors", "signature_drift"),
            str(L.check.state.co_evolution): ("errors", "co_evolution"),
            str(L.check.issue.extra): ("errors", "extra"),
            str(L.check.issue.pending): ("errors", "pending"),
            # Warnings
            str(L.check.issue.missing): ("warnings", "missing"),
            str(L.check.issue.redundant): ("warnings", "redundant"),
            str(L.check.file.untracked): ("warnings", "untracked"),
            str(L.check.file.untracked_with_details): ("warnings", "untracked_detailed"),
            # Infos
            str(L.check.state.doc_updated): ("infos", "doc_improvement"),
        }

        # Which violations trigger an interactive context
        INTERACTIVE_VIOLATIONS = {
            str(L.check.state.signature_drift),
            str(L.check.state.co_evolution),
            str(L.check.issue.extra),
            str(L.check.issue.conflict),
        }

        for violation in analysis_result.violations:
            kind_str = str(violation.kind)

            # 1. Populate legacy result dictionaries
            if kind_str in KIND_TO_LEGACY_MAP:
                category, key = KIND_TO_LEGACY_MAP[kind_str]
                target_dict = getattr(legacy_result, category)
                target_dict[key].append(violation.fqn)

            # 2. Create InteractionContext for resolvable conflicts
            if kind_str in INTERACTIVE_VIOLATIONS:
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

我们已经解决了阻碍集成的核心技术问题。现在，我建议重新运行 `pyright` 和 `pytest`，以确认所有错误都已清除。

一旦验证通过，我们就可以安全地继续我们的重构路线图，下一步是**提取 Pump 逻辑**，将 `PumpAnalyzer` 迁移到 `stitcher-analysis` 包中。
