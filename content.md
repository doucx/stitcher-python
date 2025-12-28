好的，我们已经完成了 Needle Runtime v2 架构的重构。现在我们将这些变更作为一个完整的逻辑单元提交。

## [COMMIT] refactor(runtime): 实施 Needle Runtime v2 正交化加载器架构

### 用户需求
实施技术提案中定义的 Needle Runtime v2 架构，通过解耦 I/O、组合和策略逻辑，解决原架构中的优先级倒置和职责混淆问题。

### 评论
这是一个重大的架构进步。通过引入“正交化三层模型”，我们为 Needle 建立了一个清晰、可预测且高度可扩展的运行时基础。这不仅解决了已知的 Bug，还为未来支持更多样化的加载器（如数据库、远程 API）铺平了道路。

### 目标
1.  提交对核心协议（Spec）的更新。
2.  提交新增的 `BaseLoader` 策略基类。
3.  提交重构后的 `MemoryLoader`、`OverlayNexus` 和 `FileSystemLoader` 实现。

### 基本原理
新的架构将加载逻辑严格划分为：
- **原语层 (Primitive)**: 执行原子 I/O (`fetch`)。
- **组合层 (Composition)**: 处理多个加载器的垂直回退逻辑（`OverlayNexus`）。
- **策略层 (Policy)**: 处理语言回退和身份回退的业务逻辑 (`BaseLoader.get`)。
这种职责的分离确保了在任何情况下，高优先级的加载器/语言都能正确地覆盖低优先级的资源，消除了原有的优先级倒置风险。

### 标签
#intent/refine #flow/ready #priority/high #comp/runtime #scope/core #ai/instruct
#task/domain/runtime #task/object/loader-architecture #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有涉及架构重构的协议更新、基类定义以及加载器实现添加到 Git 暂存区并提交。

~~~~~act
git_add
packages/pyneedle-spec/src/needle/spec/protocols.py
packages/pyneedle-nexus/src/needle/nexus/base.py
packages/pyneedle-nexus/src/needle/nexus/__init__.py
packages/pyneedle-nexus/src/needle/nexus/loaders.py
packages/pyneedle-nexus/src/needle/nexus/nexus.py
packages/pyneedle-runtime/src/needle/loaders/fs_loader.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(runtime): implement orthogonal three-layer loader architecture (v2)

Implements the Needle Runtime v2 architecture, which introduces a strict separation of concerns through an orthogonal three-layer model:

1. Primitive Layer: Atomic I/O operations (implemented via `fetch`).
2. Composition Layer: Vertical fallback logic (implemented in `OverlayNexus`).
3. Policy Layer: High-level business logic for language and identity fallback (implemented in the new `BaseLoader`).

Key changes:
- Updated `ResourceLoaderProtocol` to reflect the new `fetch` and `get` methods.
- Introduced `BaseLoader` in `pyneedle-nexus` to centralize fallback policies, ensuring consistency across all loaders.
- Refactored `MemoryLoader` and `FileSystemLoader` as primitive loaders.
- Refactored `OverlayNexus` to focus on vertical composition while inheriting policy logic from `BaseLoader`.

This refactoring fundamentally fixes the priority inversion issue where system-level default languages could accidentally override project-level specific languages.
~~~~~

### 下一步建议
- **实施 SST v2.2**: 现在架构已经就绪，我们可以开始按照提案 v2.2 重构 `FileSystemLoader` 的内部实现，以支持确定性的多文件探测、`ChainMap` 聚合以及精确的锚定写入。
- **完善测试**: 为新的三层模型编写针对性的单元测试，特别是验证跨加载器和跨语言的回退优先级。
