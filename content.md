好的，我们来为这些重要的架构变更创建一个提交。

## [COMMIT] feat(arch): 引入重构策略协议与 sidecar 语言包

### 用户需求
为 `RefactoringStrategyProtocol` 的定义、`stitcher-lang-sidecar` 包的创建以及 `PythonRefactoringStrategy` 的实现创建一个 Git 提交。

### 评论
这是一个关键的里程碑提交。它为 `stitcher-refactor` 引擎的完全泛化奠定了坚实的基础。通过将 Sidecar 文件抽象为一种独立的语言，并定义通用的重构协议，我们正在从根本上消除硬编码逻辑，使系统更具扩展性。

### 目标
1.  将所有相关的创建和修改的文件暂存。
2.  创建一个原子性的、描述清晰的 Git 提交，记录本次架构演进。

### 基本原理
将协议定义、Sidecar 语言包的创建和 Python 策略的实现捆绑在一次提交中是合理的，因为它们共同构成了“泛化重构引擎”这一宏大目标的第一步：建立接口并提供初步实现。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/spec #comp/lang-sidecar #comp/lang-python
#task/domain/refactor #task/object/sidecar-adapter #task/action/create #task/state/continue

---

### Script

#### Acts 1: 暂存变更

我们将所有新创建和修改的文件添加到 Git 暂存区。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/refactor.py
packages/stitcher-spec/src/stitcher/spec/__init__.py
packages/stitcher-lang-sidecar/pyproject.toml
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/__init__.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/parser.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
packages/stitcher-lang-python/src/stitcher/lang/python/refactor.py
packages/stitcher-lang-python/src/stitcher/lang/python/__init__.py
~~~~~

#### Acts 2: 提交变更

现在，我们创建一个内容详尽的提交，以记录这些架构级别的改动。

~~~~~act
git_commit
~~~~~
~~~~~text
feat(arch): Introduce refactor strategy protocol and sidecar lang pack

This commit lays the foundational groundwork for generalizing the refactoring engine, moving it away from Python-specific and sidecar-specific logic.

Key changes:

1.  **Define `RefactoringStrategyProtocol` in `stitcher-spec`**: Establishes a formal, language-agnostic interface for applying rename operations. This decouples the refactor engine from the implementation details of any given language.

2.  **Create `stitcher-lang-sidecar` Package**: Elevates `.stitcher.yaml` files to be first-class language citizens. It includes a `SidecarAdapter` that parses YAML keys as `ReferenceRecord`s. This allows the indexer to treat sidecar files as source code containing references, which is critical for unified refactoring.

3.  **Implement `PythonRefactoringStrategy`**: Implements the new protocol in `stitcher-lang-python`, wrapping the existing robust LibCST-based `SymbolRenamerTransformer`.

This prepares the system for the final step of refactoring the `stitcher-refactor` engine itself to consume these new, generic components.
~~~~~

### 下一步建议
我们已经完成了协议定义和语言包的准备工作。下一步就是最核心的手术：**重构 `stitcher-refactor` 引擎**。

具体行动将包括：
1.  移除 `SidecarUpdateMixin` 和相关的 `SidecarUpdateIntent`。
2.  在 `RefactorContext` 中引入一个策略注册表。
3.  重写 `GlobalBatchRenamer`，使其不再硬编码 `SymbolRenamerTransformer`，而是通过策略注册表动态地为不同文件类型（`.py`, `.yaml`）分发重构任务。

如果你同意，我将开始制定执行此项重构的计划。
