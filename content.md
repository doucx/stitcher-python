好的，我们现在将阶段 1 和阶段 2 的所有基础工作提交到 Git 仓库。

这是一次关键的提交，标志着 Stitcher 的底层定位模型从“物理路径猜测”转向了“逻辑坐标锚定”。

## [COMMIT] feat: implement global SURI protocols, workspace coordinates, and LockFileManager

### 用户需求
提交当前所有关于 SURI 协议、Workspace 坐标系增强以及 LockFileManager 实现的改动。

### 评论
这个提交确立了系统的新底座。我们现在拥有了标准化的 SURI 生成协议和中心化的 `stitcher.lock` 管理机制。虽然核心业务逻辑尚未切换，但所有必要的“零件”已经生产完成并经过了初步的接口适配。

### 目标
1.  暂存 `stitcher-spec` 中的协议变更。
2.  暂存 `stitcher-workspace` 中的路径算力增强。
3.  暂存 `stitcher-lang-sidecar` 中的 Lock 管理实现。
4.  暂存 `stitcher-lang-python` 中的 SURI 生成器重写及其相关的适配性修复。
5.  创建一个内容详尽的提交记录。

### 基本原理
在进行大规模重构（阶段 3）之前，将基础设施层先行提交，可以确保每个开发阶段都是原子的、可回溯的，符合“正规军”工程标准。

### 标签
#intent/architect #flow/ready #priority/medium #comp/interfaces #comp/build #concept/state #ai/instruct #task/domain/storage #task/object/suri-lockfile #task/action/infrastructure-completion #task/state/continue

---

### Script

#### Acts 1: 提交变更

我们将所有涉及协议定义、路径计算逻辑和新持久化层的修改添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/protocols.py
packages/stitcher-spec/src/stitcher/spec/__init__.py
packages/stitcher-workspace/src/stitcher/workspace/workspace.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/lock_manager.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/__init__.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/transform.py
packages/stitcher-lang-python/src/stitcher/lang/python/uri.py
packages/stitcher-lang-python/src/stitcher/lang/python/__init__.py
packages/stitcher-lang-python/src/stitcher/lang/python/adapter.py
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat: implement global SURI protocols, workspace coordinates, and LockFileManager

This commit establishes the foundation for moving from per-file signature storage to package-level 'stitcher.lock' files.

Key changes:
1. Protocols: Defined 'URIGeneratorProtocol' and 'LockManagerProtocol' in 'stitcher-spec' to standardize logical addressing and persistence.
2. Coordinates: Enhanced 'stitcher-workspace' with 'find_workspace_root' and 'to_workspace_relative' to provide a global coordinate system anchored to the project root.
3. Lock Management: Implemented 'LockFileManager' in 'stitcher-lang-sidecar' for atomic, sorted JSON persistence of fingerprints.
4. URI Generation: Rewrote Python SURI generation to implement the new protocol, ensuring IDs are stable across Monorepo boundaries.
5. Fixes: Updated all internal references to use the new 'PythonURIGenerator' API.

This enables the system to treat entity identities as logical pointers rather than physical file paths, simplifying refactoring and improving I/O performance.
~~~~~

### 下一步建议

基础设施已固化。下一步我们将进入 **阶段 3: 手术式替换 (The Great Switch)**。

我们将通过以下步骤完成最后的一跃：
1.  **物理清理**: 删除 `stitcher-application` 中过时的 `signature_manager.py`。
2.  **依赖注入重构**: 修改 `StitcherApp`，将 `LockFileManager` 和 `PythonURIGenerator` 实例分发给各个 Runner。
3.  **Runner 业务适配**: 修改 `InitRunner` 和 `PumpRunner` 的逻辑，从“逐个写 JSON”改为“操作内存缓存并在结束时 Flush Lock”。
