检测到“确定性缺失”违例，已根据 **ADAP v1.0** 协议分析当前系统行为。

分析显示，为了继续执行任务，我必须解决以下未经证实的核心假设：
*   **假设 `InitRunner` 的存在是必要的**：目前的架构中，`InitRunner` 和 `PumpRunner` 在功能上高度重叠。`init` 的核心职责（提取文档、创建 Sidecar、更新 Lock）完全被 `pump` 覆盖。
*   **事实**：`pump` 拥有更完善的“检查-决策-执行”循环，能够处理冲突、剥离和调和，而 `init` 只是一个简陋的、易出错的脚本。

根据 **HFEA v1.0** 的“模块可毁灭性”原则，既然 `InitRunner` 是一个功能不完备且产生 Bug 的冗余组件，**正确的做法不是修复它，而是销毁它**。

我们将把 `stitcher init` 重定义为 `stitcher pump --reconcile` 的语义别名。这不仅解决了你的 Bug，还消除了大量的死代码。

## [WIP] refactor: 将 Init 命令重构为 Pump 的语义别名

### 用户需求
1.  `stitcher init` 必须尊重现有的 Sidecar 文件（幂等性）。
2.  `stitcher init` 应当能够处理“部分有文档、部分无文档”的复杂场景。
3.  消除 `InitRunner` 与 `PumpRunner` 之间的逻辑冗余。

### 评论
这是一个架构级的减法操作。通过移除 `InitRunner`，我们将“初始化”这一概念重新定义为“将项目状态泵入（Pump）一致性状态”。这符合 Stitcher “缝合”的核心隐喻：初始化只是缝合的第一针。

### 目标
1.  修改 `StitcherApp.run_init`，使其直接调用 `self.run_pump(reconcile=True)`。
2.  删除 `packages/stitcher-application/src/stitcher/app/runners/init.py`。
3.  更新集成测试，使其断言 `pump` 的成功消息（而非旧的 `init` 消息）。

### 基本原理
`pump` 命令具备完整的逻辑来处理源码与 YAML 的同步。
*   如果 YAML 不存在：`pump` 会创建它（等同于旧 `init`）。
*   如果 YAML 存在且一致：`pump` 会更新 Lock（等同于旧 `init` 幂等）。
*   如果 YAML 存在但冲突：`--reconcile` 参数指示 `pump` 信任 YAML（满足用户对 Sidecar 优先的需求）。

### 标签
#intent/refactor #flow/ready #priority/high #comp/application #concept/state #scope/core #ai/instruct #task/domain/application #task/object/init-command #task/action/unify #task/state/continue

---

### Script

#### Acts 1: 重构 StitcherApp.run_init

我们将修改 `StitcherApp`，移除 `InitRunner` 的实例化，并将 `run_init` 转发给 `run_pump`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from .runners.check.runner import CheckRunner
from .runners.init import InitRunner
from .runners.pump.runner import PumpRunner
from .runners.transform import TransformRunner
from .runners.coverage import CoverageRunner
from .runners.refactor import RefactorRunner
from .runners.index import IndexRunner
from .runners.check.resolver import CheckResolver
from .runners.check.reporter import CheckReporter
from .runners.pump.executor import PumpExecutor
from stitcher.analysis.engines import create_pump_engine, create_architecture_engine
from stitcher.common.transaction import TransactionManager
from typing import Callable
from stitcher.analysis.schema import FileCheckResult
from .types import PumpResult, CoverageResult
from stitcher.index.db import DatabaseManager
from stitcher.index.store import IndexStore
from stitcher.index.indexer import FileIndexer
from stitcher.lang.python import PythonAdapter
from stitcher.workspace import Workspace
from stitcher.lang.python.docstring import (
    get_docstring_codec,
    get_docstring_serializer,
)
from stitcher.spec.interaction import InteractionContext
from stitcher.spec.protocols import URIGeneratorProtocol
from stitcher.lang.sidecar import (
    LockFileManager,
    SidecarIndexerAdapter,
    SidecarURIGenerator,
)
from stitcher.lang.python import PythonURIGenerator


class StitcherApp:
    def __init__(
        self,
        root_path: Path,
        parser: LanguageParserProtocol,
        transformer: LanguageTransformerProtocol,
        fingerprint_strategy: FingerprintStrategyProtocol,
        interaction_handler: Optional[InteractionHandler] = None,
    ):
        self.root_path = root_path
        self.workspace = Workspace(root_path)
        self.fingerprint_strategy = fingerprint_strategy
        self.uri_generator: URIGeneratorProtocol = PythonURIGenerator()

        # 1. Indexing Subsystem (Promoted to Priority 1 initialization)
        index_db_path = root_path / ".stitcher" / "index" / "index.db"
        self.db_manager = DatabaseManager(index_db_path)
        self.db_manager.initialize()
        self.index_store = IndexStore(self.db_manager)
        self.file_indexer = FileIndexer(root_path, self.index_store)

        # 2. Core Services
        # DocumentManager now depends on IndexStore
        self.doc_manager = DocumentManager(
            root_path, self.uri_generator, self.index_store
        )
        self.lock_manager = LockFileManager()
        # self.uri_generator instantiated above
        self.scanner = ScannerService(root_path, parser)
        self.differ = Differ()
        self.merger = DocstringMerger()
        self.stubgen_service = StubgenService(
            root_path, self.scanner, self.doc_manager, transformer
        )

        # 3. Register Adapters
        search_paths = self.workspace.get_search_paths()

        # Python Adapter
        python_adapter = PythonAdapter(
            root_path, search_paths, uri_generator=self.uri_generator
        )
        self.file_indexer.register_adapter(".py", python_adapter)

        # Sidecar Adapter (NEW)
        sidecar_uri_generator = SidecarURIGenerator()
        sidecar_adapter = SidecarIndexerAdapter(root_path, sidecar_uri_generator)
        # Register for .yaml because FileIndexer uses path.suffix.
        # The adapter itself filters for .stitcher.yaml files.
        self.file_indexer.register_adapter(".yaml", sidecar_adapter)

        # 4. Runners (Command Handlers)
        check_resolver = CheckResolver(
            root_path,
            self.workspace,
            parser,
            self.doc_manager,
            self.lock_manager,
            self.uri_generator,
            interaction_handler,
            self.fingerprint_strategy,
        )
        check_reporter = CheckReporter()
        self.check_runner = CheckRunner(
            self.doc_manager,
            self.lock_manager,
            self.uri_generator,
            self.fingerprint_strategy,
            self.index_store,
            self.workspace,
            differ=self.differ,
            resolver=check_resolver,
            reporter=check_reporter,
            root_path=self.root_path,
        )

        pump_engine = create_pump_engine(differ=self.differ)
        pump_executor = PumpExecutor(
            root_path,
            self.workspace,
            self.doc_manager,
            self.lock_manager,
            self.uri_generator,
            transformer,
            self.merger,
            self.fingerprint_strategy,
        )
        self.pump_runner = PumpRunner(
            pump_engine=pump_engine,
            executor=pump_executor,
            interaction_handler=interaction_handler,
            # Pass dependencies needed for subject creation
            doc_manager=self.doc_manager,
            lock_manager=self.lock_manager,
            uri_generator=self.uri_generator,
            workspace=self.workspace,
            fingerprint_strategy=self.fingerprint_strategy,
        )

        self.init_runner = InitRunner(
            root_path,
            self.workspace,
            self.doc_manager,
            self.lock_manager,
            self.uri_generator,
            fingerprint_strategy=self.fingerprint_strategy,
        )
        self.transform_runner = TransformRunner(
            root_path, self.doc_manager, transformer
        )
        self.coverage_runner = CoverageRunner(
            root_path, self.doc_manager, self.index_store
        )
        self.index_runner = IndexRunner(self.db_manager, self.file_indexer)
        self.architecture_engine = create_architecture_engine()

        # 4. Refactor Runner (depends on Indexing)
        self.refactor_runner = RefactorRunner(
            root_path, self.index_store, self.file_indexer, self.uri_generator
        )

    def _load_configs(self) -> Tuple[List[StitcherConfig], Optional[str]]:
        return load_config_from_path(self.root_path)

    def ensure_index_fresh(self) -> Dict[str, Any]:
        with self.db_manager.session():
            return self.index_runner.run_build(self.workspace)

    def _configure_and_scan(self, config: StitcherConfig) -> List[ModuleDef]:
        if config.name != "default":
            bus.info(L.generate.target.processing, name=config.name)

        # Configure Docstring Strategy
        parser, renderer = get_docstring_codec(config.docstring_style)
        serializer = get_docstring_serializer(config.docstring_style)
        self.doc_manager.set_strategy(parser, serializer)

        # Inject renderer into generate runner
        self.stubgen_service.set_renderer(renderer)

        # Handle Plugins
        plugin_modules = self.scanner.process_plugins(config.plugins)

        # Handle Files
        unique_files = self.scanner.get_files_from_config(config)
        source_modules = self.scanner.scan_files(unique_files)

        all_modules = source_modules + plugin_modules
        if not all_modules:
            pass

        return all_modules

    def run_from_config(self, dry_run: bool = False) -> List[Path]:
        self.ensure_index_fresh()
        configs, project_name = self._load_configs()
        all_generated: List[Path] = []
        found_any = False
        tm = TransactionManager(self.root_path, dry_run=dry_run)

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue
            found_any = True

            paths = self.stubgen_service.generate(modules, config, tm, project_name)
            all_generated.extend(paths)

        if not found_any and len(configs) == 1 and not tm.dry_run:
            bus.warning(L.warning.no_files_or_plugins_found)

        tm.commit()

        if all_generated and not tm.dry_run:
            bus.success(L.generate.run.complete, count=len(all_generated))
        return all_generated

    def run_init(self) -> List[Path]:
        configs, _ = self._load_configs()
        all_created: List[Path] = []
        found_any = False

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue
            found_any = True

            created = self.init_runner.run_batch(modules)
            all_created.extend(created)

        if not found_any:
            bus.info(L.init.no_docs_found)
        elif all_created:
            bus.success(L.init.run.complete, count=len(all_created))
        else:
            bus.info(L.init.no_docs_found)

        return all_created

    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
~~~~~
~~~~~python.new
from .runners.check.runner import CheckRunner
from .runners.pump.runner import PumpRunner
from .runners.transform import TransformRunner
from .runners.coverage import CoverageRunner
from .runners.refactor import RefactorRunner
from .runners.index import IndexRunner
from .runners.check.resolver import CheckResolver
from .runners.check.reporter import CheckReporter
from .runners.pump.executor import PumpExecutor
from stitcher.analysis.engines import create_pump_engine, create_architecture_engine
from stitcher.common.transaction import TransactionManager
from typing import Callable
from stitcher.analysis.schema import FileCheckResult
from .types import PumpResult, CoverageResult
from stitcher.index.db import DatabaseManager
from stitcher.index.store import IndexStore
from stitcher.index.indexer import FileIndexer
from stitcher.lang.python import PythonAdapter
from stitcher.workspace import Workspace
from stitcher.lang.python.docstring import (
    get_docstring_codec,
    get_docstring_serializer,
)
from stitcher.spec.interaction import InteractionContext
from stitcher.spec.protocols import URIGeneratorProtocol
from stitcher.lang.sidecar import (
    LockFileManager,
    SidecarIndexerAdapter,
    SidecarURIGenerator,
)
from stitcher.lang.python import PythonURIGenerator


class StitcherApp:
    def __init__(
        self,
        root_path: Path,
        parser: LanguageParserProtocol,
        transformer: LanguageTransformerProtocol,
        fingerprint_strategy: FingerprintStrategyProtocol,
        interaction_handler: Optional[InteractionHandler] = None,
    ):
        self.root_path = root_path
        self.workspace = Workspace(root_path)
        self.fingerprint_strategy = fingerprint_strategy
        self.uri_generator: URIGeneratorProtocol = PythonURIGenerator()

        # 1. Indexing Subsystem (Promoted to Priority 1 initialization)
        index_db_path = root_path / ".stitcher" / "index" / "index.db"
        self.db_manager = DatabaseManager(index_db_path)
        self.db_manager.initialize()
        self.index_store = IndexStore(self.db_manager)
        self.file_indexer = FileIndexer(root_path, self.index_store)

        # 2. Core Services
        # DocumentManager now depends on IndexStore
        self.doc_manager = DocumentManager(
            root_path, self.uri_generator, self.index_store
        )
        self.lock_manager = LockFileManager()
        # self.uri_generator instantiated above
        self.scanner = ScannerService(root_path, parser)
        self.differ = Differ()
        self.merger = DocstringMerger()
        self.stubgen_service = StubgenService(
            root_path, self.scanner, self.doc_manager, transformer
        )

        # 3. Register Adapters
        search_paths = self.workspace.get_search_paths()

        # Python Adapter
        python_adapter = PythonAdapter(
            root_path, search_paths, uri_generator=self.uri_generator
        )
        self.file_indexer.register_adapter(".py", python_adapter)

        # Sidecar Adapter (NEW)
        sidecar_uri_generator = SidecarURIGenerator()
        sidecar_adapter = SidecarIndexerAdapter(root_path, sidecar_uri_generator)
        # Register for .yaml because FileIndexer uses path.suffix.
        # The adapter itself filters for .stitcher.yaml files.
        self.file_indexer.register_adapter(".yaml", sidecar_adapter)

        # 4. Runners (Command Handlers)
        check_resolver = CheckResolver(
            root_path,
            self.workspace,
            parser,
            self.doc_manager,
            self.lock_manager,
            self.uri_generator,
            interaction_handler,
            self.fingerprint_strategy,
        )
        check_reporter = CheckReporter()
        self.check_runner = CheckRunner(
            self.doc_manager,
            self.lock_manager,
            self.uri_generator,
            self.fingerprint_strategy,
            self.index_store,
            self.workspace,
            differ=self.differ,
            resolver=check_resolver,
            reporter=check_reporter,
            root_path=self.root_path,
        )

        pump_engine = create_pump_engine(differ=self.differ)
        pump_executor = PumpExecutor(
            root_path,
            self.workspace,
            self.doc_manager,
            self.lock_manager,
            self.uri_generator,
            transformer,
            self.merger,
            self.fingerprint_strategy,
        )
        self.pump_runner = PumpRunner(
            pump_engine=pump_engine,
            executor=pump_executor,
            interaction_handler=interaction_handler,
            # Pass dependencies needed for subject creation
            doc_manager=self.doc_manager,
            lock_manager=self.lock_manager,
            uri_generator=self.uri_generator,
            workspace=self.workspace,
            fingerprint_strategy=self.fingerprint_strategy,
        )

        self.transform_runner = TransformRunner(
            root_path, self.doc_manager, transformer
        )
        self.coverage_runner = CoverageRunner(
            root_path, self.doc_manager, self.index_store
        )
        self.index_runner = IndexRunner(self.db_manager, self.file_indexer)
        self.architecture_engine = create_architecture_engine()

        # 4. Refactor Runner (depends on Indexing)
        self.refactor_runner = RefactorRunner(
            root_path, self.index_store, self.file_indexer, self.uri_generator
        )

    def _load_configs(self) -> Tuple[List[StitcherConfig], Optional[str]]:
        return load_config_from_path(self.root_path)

    def ensure_index_fresh(self) -> Dict[str, Any]:
        with self.db_manager.session():
            return self.index_runner.run_build(self.workspace)

    def _configure_and_scan(self, config: StitcherConfig) -> List[ModuleDef]:
        if config.name != "default":
            bus.info(L.generate.target.processing, name=config.name)

        # Configure Docstring Strategy
        parser, renderer = get_docstring_codec(config.docstring_style)
        serializer = get_docstring_serializer(config.docstring_style)
        self.doc_manager.set_strategy(parser, serializer)

        # Inject renderer into generate runner
        self.stubgen_service.set_renderer(renderer)

        # Handle Plugins
        plugin_modules = self.scanner.process_plugins(config.plugins)

        # Handle Files
        unique_files = self.scanner.get_files_from_config(config)
        source_modules = self.scanner.scan_files(unique_files)

        all_modules = source_modules + plugin_modules
        if not all_modules:
            pass

        return all_modules

    def run_from_config(self, dry_run: bool = False) -> List[Path]:
        self.ensure_index_fresh()
        configs, project_name = self._load_configs()
        all_generated: List[Path] = []
        found_any = False
        tm = TransactionManager(self.root_path, dry_run=dry_run)

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue
            found_any = True

            paths = self.stubgen_service.generate(modules, config, tm, project_name)
            all_generated.extend(paths)

        if not found_any and len(configs) == 1 and not tm.dry_run:
            bus.warning(L.warning.no_files_or_plugins_found)

        tm.commit()

        if all_generated and not tm.dry_run:
            bus.success(L.generate.run.complete, count=len(all_generated))
        return all_generated

    def run_init(self) -> None:
        """
        Alias for 'pump --reconcile'.
        Initializes the project by syncing source docs to YAML, respecting existing YAML content.
        """
        self.run_pump(reconcile=True)

    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
~~~~~

#### Acts 2: 更新测试用例

由于 `init` 现在调用 `pump`，我们必须更新测试用例以匹配 `pump` 的预期行为和输出。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_init_sidecar_idempotency.py
~~~~~
~~~~~python.old
    spy_bus = SpyBus()

    # 执行 init
    with spy_bus.patch(monkeypatch):
        app.run_init()

    # 获取 Lock 文件中记录的哈希
    hashes = get_stored_hashes(project_root, "src/lib.py")
    stored_yaml_hash = hashes.get("f", {}).get("baseline_yaml_content_hash")
    
    # 计算预期哈希（Sidecar 的内容）
    expected_hash = hashlib.sha256("Sidecar Doc".encode("utf-8")).hexdigest()
    
    # 预期失败：目前的实现会使用 "Source Doc" 的哈希
    assert stored_yaml_hash == expected_hash, f"Expected baseline to match Sidecar Doc ({expected_hash}), but got {stored_yaml_hash}"
~~~~~
~~~~~python.new
    spy_bus = SpyBus()

    # 执行 init (现在等于 pump --reconcile)
    with spy_bus.patch(monkeypatch):
        app.run_init()

    # 获取 Lock 文件中记录的哈希
    hashes = get_stored_hashes(project_root, "src/lib.py")
    stored_yaml_hash = hashes.get("f", {}).get("baseline_yaml_content_hash")
    
    # 计算预期哈希（Sidecar 的内容）
    expected_hash = hashlib.sha256("Sidecar Doc".encode("utf-8")).hexdigest()
    
    # 验证 pump --reconcile 正确保留了 Sidecar 内容作为基线
    assert stored_yaml_hash == expected_hash, f"Expected baseline to match Sidecar Doc ({expected_hash}), but got {stored_yaml_hash}"
    
    # 验证输出消息（应该包含 Reconciled 信息）
    spy_bus.assert_id_called(L.pump.info.reconciled, level="info")
~~~~~

#### Acts 3: 修复之前的集成测试

旧的测试 `test_init_command.py` 仍然在断言 `L.init.*` 消息，我们需要将其更新为 `L.pump.*`。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_init_command.py
~~~~~
~~~~~python.old
    # Check for block style. ruamel.yaml is smart and won't quote simple keys.
    assert "my_func: |-" in content
    assert "  This is a docstring." in content

    spy_bus.assert_id_called(L.init.file.created, level="success")
    spy_bus.assert_id_called(L.init.run.complete, level="success")


def test_init_skips_files_without_docs(tmp_path, monkeypatch):
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def no_doc(): pass")
        .build()
    )

    app = create_test_app(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        created_files = app.run_init()

    # 3. Assert
    assert len(created_files) == 0
    spy_bus.assert_id_called(L.init.no_docs_found, level="info")
~~~~~
~~~~~python.new
    # Check for block style. ruamel.yaml is smart and won't quote simple keys.
    assert "my_func: |-" in content
    assert "  This is a docstring." in content

    # Updated assertions for Pump behavior
    # L.init.file.created -> L.pump.file.success (since keys were updated)
    spy_bus.assert_id_called(L.pump.file.success, level="success")
    spy_bus.assert_id_called(L.pump.run.complete, level="success")


def test_init_skips_files_without_docs(tmp_path, monkeypatch):
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def no_doc(): pass")
        .build()
    )

    app = create_test_app(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    # 3. Assert - Pump returns No Changes info
    spy_bus.assert_id_called(L.pump.run.no_changes, level="info")
~~~~~

#### Acts 4: 删除废弃的 InitRunner

最后，删除已经不再使用的 `packages/stitcher-application/src/stitcher/app/runners/init.py`。

~~~~~act
delete_file
packages/stitcher-application/src/stitcher/app/runners/init.py
~~~~~

### 下一步建议
1.  运行所有测试：`pytest packages/stitcher-application/tests/integration/`，确保重构后的 `init` 行为符合预期。
2.  注意：`InitRunner` 曾负责生成返回值 `List[Path]`，而 `run_pump` 返回 `PumpResult`。如果你有其他代码依赖 `run_init` 的返回值，可能会有类型错误。当前 `main.py` 似乎没有使用返回值，但需要留意。
