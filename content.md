好的，我们立即开始实施第二阶段。

此阶段的目标是重构 `CheckRunner`，使其能够直接处理文件路径列表，而不是强制依赖于内存中的 `ModuleDef` AST 对象。这将是实现 Zero-IO Check 的核心驱动逻辑变更。

我将修改 `CheckRunner` 以接受 `IndexStore` 作为新的依赖，并添加一个 `analyze_paths` 方法。同时，我也会更新 `StitcherApp` 来注入这个新的依赖。

## [WIP] feat: 重构 CheckRunner 以支持基于路径的 Zero-IO 分析

### 用户需求

根据 Zero-IO Check 路线图的第二阶段，需要重构 `CheckRunner`，为其添加一个新的、基于文件路径列表 (`List[str]`) 的分析入口点 `analyze_paths`。这个新方法应使用在第一阶段创建的 `IndexCheckSubjectAdapter` 来执行分析，从而摆脱对 `ModuleDef` 对象的依赖。

### 评论

这是将 Zero-IO 潜力转化为现实的关键一步。通过为 `CheckRunner` 提供一个直接处理路径的“快速通道”，我们正在解耦检查流程与重量级的 AST 解析步骤。这使得上游调用者（`StitcherApp`）可以将“扫描文件”和“分析文件”两个阶段彻底分开，为第三阶段实现端到端的 Zero-IO 流程铺平了道路。

### 目标

1.  向 `CheckRunner` 的构造函数 `__init__` 中添加 `index_store: IndexStore` 作为新的依赖项。
2.  更新 `StitcherApp` 的构造逻辑，将 `self.index_store` 实例注入到 `CheckRunner` 中。
3.  在 `CheckRunner` 中实现一个新的公共方法 `analyze_paths`，它接收一个文件路径列表。
4.  确保 `analyze_paths` 方法为每个路径实例化 `IndexCheckSubjectAdapter`，并调用 `self.analyzer` 来执行检查。

### 基本原理

为了让 `CheckRunner` 能够使用 `IndexCheckSubjectAdapter`，它必须能够访问 `IndexStore`。因此，第一步是进行依赖注入，将 `IndexStore` 从 `StitcherApp` 传递给 `CheckRunner`。

一旦依赖关系建立，我们就可以创建一个新的 `analyze_paths` 方法。这个方法将成为未来 `check` 命令的主要工作流。它遍历文件路径，为每个路径创建一个轻量级的 `IndexCheckSubjectAdapter`，然后将其传递给现有的、未被修改的 `CheckAnalyzer`。由于 `CheckAnalyzer` 是面向协议 (`CheckSubject`) 编程的，它根本不知道数据是来自 AST 还是数据库，从而实现了完美的逻辑复用和关注点分离。

现有的 `analyze_batch(modules: List[ModuleDef])` 方法将被保留，以处理那些无法或不适合使用持久化索引的场景（例如，对动态生成的插件进行检查）。

### 标签

#intent/refine #flow/ready #priority/high
#comp/engine #concept/state #scope/core
#ai/instruct
#task/domain/testing #task/object/zero-io-check #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 更新 `CheckRunner` 以接受 `IndexStore`

首先，我将修改 `CheckRunner` 的 `__init__` 方法，添加 `index_store` 依赖。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    ModuleDef,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
)
from stitcher.app.services import (
    DocumentManager,
    SignatureManager,
    Differ,
)
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.app.types import FileCheckResult

from .analyzer import CheckAnalyzer
from .resolver import CheckResolver
from .reporter import CheckReporter


from .subject import ASTCheckSubjectAdapter


class CheckRunner:
    def __init__(
        self,
        root_path: Path,
        parser: LanguageParserProtocol,
        doc_manager: DocumentManager,
        sig_manager: SignatureManager,
        differ: Differ,
        interaction_handler: InteractionHandler | None,
        fingerprint_strategy: FingerprintStrategyProtocol,
    ):
        # Keep services needed by both adapter and resolver
        self.root_path = root_path
        self.parser = parser
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager
        self.fingerprint_strategy = fingerprint_strategy

        # Inject dependencies into sub-components
~~~~~
~~~~~python.new
from pathlib import Path
from typing import List, Tuple

from stitcher.spec import (
    ModuleDef,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
)
from stitcher.app.services import (
    DocumentManager,
    SignatureManager,
    Differ,
)
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.app.types import FileCheckResult
from stitcher.index.store import IndexStore

from .analyzer import CheckAnalyzer
from .resolver import CheckResolver
from .reporter import CheckReporter


from .subject import ASTCheckSubjectAdapter, IndexCheckSubjectAdapter


class CheckRunner:
    def __init__(
        self,
        root_path: Path,
        parser: LanguageParserProtocol,
        doc_manager: DocumentManager,
        sig_manager: SignatureManager,
        differ: Differ,
        interaction_handler: InteractionHandler | None,
        fingerprint_strategy: FingerprintStrategyProtocol,
        index_store: IndexStore,
    ):
        # Keep services needed by both adapter and resolver
        self.root_path = root_path
        self.parser = parser
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager
        self.fingerprint_strategy = fingerprint_strategy
        self.index_store = index_store

        # Inject dependencies into sub-components
~~~~~

#### Acts 2: 在 `StitcherApp` 中注入 `IndexStore`

现在，我将更新 `StitcherApp`，将 `index_store` 传递给 `CheckRunner` 的构造函数。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        self.check_runner = CheckRunner(
            root_path,
            parser,
            self.doc_manager,
            self.sig_manager,
            self.differ,
            interaction_handler,
            fingerprint_strategy=self.fingerprint_strategy,
        )
~~~~~
~~~~~python.new
        self.check_runner = CheckRunner(
            root_path,
            parser,
            self.doc_manager,
            self.sig_manager,
            self.differ,
            interaction_handler,
            fingerprint_strategy=self.fingerprint_strategy,
            index_store=self.index_store,
        )
~~~~~

#### Acts 3: 在 `CheckRunner` 中实现 `analyze_paths` 方法

最后，我将在 `CheckRunner` 中添加新的 `analyze_paths` 方法。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
        self.reporter = CheckReporter()

    def analyze_batch(
        self, modules: List[ModuleDef]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
~~~~~
~~~~~python.new
        self.reporter = CheckReporter()

    def analyze_paths(
        self, file_paths: List[str]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
        all_results: List[FileCheckResult] = []
        all_conflicts: List[InteractionContext] = []

        for file_path in file_paths:
            subject = IndexCheckSubjectAdapter(
                file_path, self.index_store, self.doc_manager, self.sig_manager
            )
            result, conflicts = self.analyzer.analyze_subject(subject)
            all_results.append(result)
            all_conflicts.extend(conflicts)

        return all_results, all_conflicts

    def analyze_batch(
        self, modules: List[ModuleDef]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
~~~~~

### 下一步建议

第二阶段已成功完成。`CheckRunner` 现在拥有了处理文件路径列表的能力，并能利用 `IndexCheckSubjectAdapter` 从数据库获取信息。

接下来的工作是路线图的**第三阶段：升级顶层编排逻辑 (`StitcherApp`)**。我将修改 `StitcherApp.run_check` 方法，使其调用我们刚刚创建的 `check_runner.analyze_paths`。这将是实现 Zero-IO 流程的临门一脚，因为它将彻底改变 `check` 命令的工作流，从“解析所有文件”变为“直接从索引分析”。

如果你同意，我将开始制定第三阶段的计划。
