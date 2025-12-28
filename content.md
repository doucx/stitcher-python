好的，我们已经完成了一次大规模且至关重要的架构重构。现在所有的修改都已完成，测试也已通过，是时候将这些成果固化为一个原子性的提交了。

我将为你生成一个 `[COMMIT]` 计划。

## [COMMIT] refactor(runtime): 采用组合式加载器架构并迁移至 SST v2.2

### 用户需求
将自“实现 Needle SST v2.2”以来的所有架构重构、代码修复和资源文件迁移工作，创建一个完整、清晰的 Git 提交。

### 评论
这次提交标志着 `stitcher-needle` 运行时架构的一个重要里程碑。通过引入 SST v2.2 规范和组合式加载器模型，我们从根本上解决了一系列关于职责耦合、优先级模糊和开发者体验不佳的问题。现在的系统更加健壮、可预测且易于扩展。

### 目标
1.  将所有相关的代码修改（包括 `pyneedle-*` 系列包、`stitcher-common` 和 `stitcher-cli`）添加到 Git 暂存区。
2.  将所有被迁移脚本更新过的 `needle` 资源文件也添加到暂存区。
3.  创建一个内容详尽的 Git 提交信息，清晰地阐述本次重构的动机、具体变更和带来的好处。

### 基本原理
在完成一个逻辑上完整的、跨多个包的大型重构之后，创建一个单一的、原子性的提交是至关重要的。这确保了版本历史的清晰性，使得未来的代码审查、问题追溯（`git bisect`）和新成员理解项目架构都变得更加容易。

### 标签
#intent/refine #flow/ready #priority/high #comp/runtime #comp/cli #comp/interfaces #concept/state #scope/core #scope/dx #task/domain/storage #task/object/loader-architecture #task/action/refactor #task/state/end

---

### Script

#### Acts 1: 暂存所有变更

我们将添加所有被修改过的包，包括代码和新的资源文件结构。

~~~~~act
git_add
packages/pyneedle/src/needle/__init__.py
packages/pyneedle-nexus/src/needle/nexus/nexus.py
packages/pyneedle-runtime/
packages/pyneedle-spec/src/needle/spec/protocols.py
packages/stitcher-cli/
packages/stitcher-common/
~~~~~

#### Acts 2: 创建提交

现在，我们将这些变更提交到版本历史中。

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(runtime): Adopt composable loader architecture and SST v2.2

This commit marks a fundamental architectural overhaul of the resource loading system, moving from a monolithic, multi-root loader to a decoupled, composable model, and migrating all assets to the new SST v2.2 physical storage specification.

Key Changes:

1.  **SST v2.2 Asset Migration**:
    - All FQN-based `.json` resource files have been migrated to a nested directory structure (`category/namespace.json`).
    - Files now use relative keys, with `_` for self-references, significantly improving developer experience.

2.  **Handler Responsibility Shift**:
    - `JsonHandler` (and all future handlers) is now responsible for the bidirectional transformation: flattening nested structures into FQN keys on load (`flatten`) and recreating them on save (`inflate`).

3.  **`FileSystemLoader` Simplification (SRP)**:
    - `FileSystemLoader` is now a strict single-root loader, removing all multi-root logic (`add_root`). Its sole responsibility is to map a single filesystem root to a flat key-value dictionary.

4.  **Composition via `OverlayNexus`**:
    - `OverlayNexus` is now the sole component responsible for combining multiple resource layers. Priority is explicitly defined by the order of loaders in its constructor, eliminating ambiguity.
    - Application layers (`stitcher-common`, `stitcher-cli`) now act as "composition roots," creating their own loaders and registering them with the central `stitcher_nexus`.

5.  **Robust Duck-Typing**:
    - Replaced a fragile, `isinstance` check for writable loaders with a robust `hasattr` check for `put` and `locate` methods, embracing duck-typing and removing the need for `@runtime_checkable`.

This refactoring resolves previous issues with ambiguous loading priorities, poor developer experience when editing resources, and unclear separation of concerns. The new architecture is more predictable, testable, and extensible.
~~~~~
