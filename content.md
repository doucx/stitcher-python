## [WIP] 建立“配置到索引”的确定性反馈环路

检测到“确定性缺失”违例，已根据 ADAP v1.0 协议挂起所有实现活动。

### 1. 显式声明假设 (DECLARE ASSUMPTION)

分析显示，为了修复当前的 E2E 测试失败，我必须做出以下未经证实的核心假设：
*   **假设 `StitcherApp` 初始化的“盲扫”索引与重构时基于配置的“精确”索引在逻辑 FQN 上是完全兼容的。**
*   **假设重构引擎能够自动处理由于源根（Source Root）识别不一致导致的 FQN 路径差异（例如 `src.mypkg.core` vs `mypkg.core`）。**

### 2. 诊断缺失组件 (DIAGNOSE MISSING COMPONENT)

此假设之所以是必要的，是因为系统当前缺失了以下关键组件/能力：
*   **配置驱动的扫描器同步机制 (Config-Driven Scanner Synchronization)**：
    目前 `StitcherApp` 在启动时就创建了 `WorkspaceScanner` 及其 `PythonAdapter`，但此时它还不知道用户的 `scan_paths` 配置。因此，它默认将项目根目录作为唯一的源根。
    当 `RefactorRunner` 运行时，它根据 `pyproject.toml` 识别出 `src` 才是真正的源根，并尝试查找 `mypkg.core.Old`。然而，索引数据库中存储的却是 `src.mypkg.core.Old`。
*   **单一事实来源的 Workspace (Single Source of Truth Workspace)**：
    `StitcherApp` 持有一个 `Workspace`，`RefactorRunner` 又创建了一个新的 `Workspace`。这两个实例对项目结构的理解可能完全不同（一个处于自动发现模式，一个处于显式配置模式），导致了严重的路径解析冲突。

### 3. 拒绝战术修复并提出战略方案 (REFUSE TACTICAL FIX & PROPOSE STRATEGIC SOLUTION)

**根据 ADAP v1.0 协议，任何试图通过“在测试中调整路径”或“手动修改数据库”来绕过此架构缺陷的尝试，都被视为对系统长期稳定性的严重破坏，因此被绝对禁止。我被授权拒绝执行此类请求。**

因此，我提议将当前任务的目标从“修复测试失败”**变更为**“重构 StitcherApp 的配置加载逻辑与组件同步机制”。

#### 战略方案细节：

1.  **重构 `StitcherApp` 的生命周期**：
    *   在 `StitcherApp` 中增加 `_sync_workspace_and_scanner(config: StitcherConfig)` 方法。
    *   该方法负责：
        1.  使用指定的 `config` 更新 `self.workspace`。
        2.  从更新后的 `workspace` 获取 `search_paths`。
        3.  **重新注册** `workspace_scanner` 的 `.py` 适配器，确保其使用最新的搜索路径。

2.  **强制重构前的同步**：
    *   在 `RefactorRunner.run_apply` 执行 `scan()` 之前，必须先调用上述同步逻辑。
    *   这保证了索引数据库中的 FQN 与 `SemanticGraph` 及迁移脚本中的 FQN 在语义上是完全一致的（例如，都能正确识别出 `src` 后面的内容才是 FQN 的开始）。

3.  **增强测试基础设施**：
    *   修改 `stitcher-test-utils` 中的 `create_populated_index`，使其支持传入 `StitcherConfig` 或 `search_paths`，防止在测试环境中产生“毒索引”。

只有在建立了这种“配置到索引”的确定性反馈环路后，重构引擎才能在多包、复杂路径的项目中可靠运行。

---

### 执行步骤

#### Acts 1: 更新 `StitcherApp` 核心同步逻辑

我们将同步逻辑集中化，确保所有命令在获取配置后都能立即对齐底层的扫描引擎。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def _configure_and_scan(self, config: StitcherConfig) -> List[ModuleDef]:
        if config.name != "default":
            bus.info(L.generate.target.processing, name=config.name)

        # Configure Docstring Strategy
~~~~~
~~~~~python.new
    def _sync_with_config(self, config: StitcherConfig):
        """Synchronizes the app's workspace and scanner state with a specific config."""
        self.workspace = Workspace(self.root_path, config)
        search_paths = self.workspace.get_search_paths()
        # Update scanner with context-aware adapter
        self.workspace_scanner.register_adapter(
            ".py", PythonAdapter(self.root_path, search_paths)
        )

    def _configure_and_scan(self, config: StitcherConfig) -> List[ModuleDef]:
        if config.name != "default":
            bus.info(L.generate.target.processing, name=config.name)

        # Ensure the underlying workspace and scanner match this target's configuration
        self._sync_with_config(config)

        # Configure Docstring Strategy
~~~~~

#### Acts 2: 修正 `RefactorRunner` 的初始化与扫描顺序

我们要确保扫描发生在适配器被正确配置（感知到 `src` 等源根）之后。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/refactor.py
~~~~~
~~~~~python.old
    def run_apply(
        self,
        migration_script: Path,
        config: StitcherConfig,
        dry_run: bool = False,
        confirm_callback: Optional[Callable[[int], bool]] = None,
    ) -> bool:
        try:
            # 0. Ensure index is up to date
            bus.info(L.index.run.start)
            self.workspace_scanner.scan()

            # 1. Bootstrap services
            bus.info(L.refactor.run.loading_graph)
            workspace = Workspace(self.root_path, config)
            bus.debug(
                L.debug.log.refactor_workspace_paths, paths=workspace.get_search_paths()
            )
            sidecar_manager = SidecarManager(self.root_path)
            graph = SemanticGraph(workspace, self.index_store)
~~~~~
~~~~~python.new
    def run_apply(
        self,
        migration_script: Path,
        config: StitcherConfig,
        dry_run: bool = False,
        confirm_callback: Optional[Callable[[int], bool]] = None,
    ) -> bool:
        try:
            # 1. Bootstrap services (Auth workspace first)
            workspace = Workspace(self.root_path, config)
            search_paths = workspace.get_search_paths()

            # 2. Sync scanner with the definitive search paths BEFORE scanning
            from stitcher.adapter.python import PythonAdapter

            self.workspace_scanner.register_adapter(
                ".py", PythonAdapter(self.root_path, search_paths)
            )

            # 3. Now perform the scan - indexing will use correct FQNs
            bus.info(L.index.run.start)
            self.workspace_scanner.scan()

            bus.info(L.refactor.run.loading_graph)
            bus.debug(L.debug.log.refactor_workspace_paths, paths=search_paths)
            sidecar_manager = SidecarManager(self.root_path)
            graph = SemanticGraph(workspace, self.index_store)
~~~~~

#### Acts 3: 更新测试辅助工具以支持配置感知的索引

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py
~~~~~
~~~~~python.old
from stitcher.adapter.python.index_adapter import PythonAdapter


def create_populated_index(root_path: Path) -> IndexStore:
    """Creates a temporary IndexStore and performs a full scan."""
    db_path = root_path / ".stitcher" / "index" / "index.db"

    db_manager = DatabaseManager(db_path)
    db_manager.initialize()
    store = IndexStore(db_manager)

    # The scanner needs a workspace-aware adapter.
    # The adapter itself is decoupled; the context is provided here.
    workspace = Workspace(root_path)
    search_paths = workspace.get_search_paths()

    scanner = WorkspaceScanner(root_path, store)
    scanner.register_adapter(".py", PythonAdapter(root_path, search_paths))
    scanner.scan()

    return store
~~~~~
~~~~~python.new
from stitcher.adapter.python.index_adapter import PythonAdapter
from stitcher.config import StitcherConfig


def create_populated_index(
    root_path: Path, config: Optional[StitcherConfig] = None
) -> IndexStore:
    """Creates a temporary IndexStore and performs a full scan."""
    db_path = root_path / ".stitcher" / "index" / "index.db"

    db_manager = DatabaseManager(db_path)
    db_manager.initialize()
    store = IndexStore(db_manager)

    # The scanner needs a workspace-aware adapter.
    # The adapter itself is decoupled; the context is provided here.
    workspace = Workspace(root_path, config=config)
    search_paths = workspace.get_search_paths()

    scanner = WorkspaceScanner(root_path, store)
    scanner.register_adapter(".py", PythonAdapter(root_path, search_paths))
    scanner.scan()

    return store
~~~~~

#### Acts 4: 修复 `test_refactor_internals.py` 传入配置

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_refactor_internals.py
~~~~~
~~~~~python.old
    # Create and populate index
    index_store = create_populated_index(tmp_path)

    workspace = Workspace(root_path=tmp_path, config=config)
~~~~~
~~~~~python.new
    # Create and populate index using the explicit config to ensure correct FQNs
    index_store = create_populated_index(tmp_path, config=config)

    workspace = Workspace(root_path=tmp_path, config=config)
~~~~~

### 下一步建议
我们解决了源根（Source Root）识别不一致导致的路径“中毒”问题。现在 `refactor` 命令应该能够正确地在数据库中找到符号及其引用，因为扫描器和重构引擎现在共享完全一致的项目结构视图。

你可以再次运行测试，这次 E2E 应该能够顺利通过。如果通过，我建议进行一次 `[COMMIT]`，因为我们已经完成了这次重构中最具挑战性的逻辑对齐部分。
