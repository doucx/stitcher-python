Excellent catch. You are absolutely right. The traceback clearly indicates an `AttributeError` because I attempted to use `self.index_store` before it was assigned in the `StitcherApp` constructor. This is a classic dependency injection error caused by incorrect initialization order.

My previous plan failed because it didn't account for this. I will now generate a focused plan to correct this single issue.

## [WIP] fix(app): Correct initialization order in StitcherApp

### 错误分析

`AttributeError: 'StitcherApp' object has no attribute 'index_store'`

错误发生在 `StitcherApp` 的 `__init__` 方法中。`PumpRunner` 的构造函数需要 `index_store` 参数，但我传递了 `self.index_store`。然而，`self.index_store` 的赋值操作位于 `__init__` 方法的 "Indexing Subsystem" 代码块中，该代码块在 "Runners" 代码块之后。这导致在实例化 `PumpRunner` 时，`self.index_store` 尚未存在。

### 用户需求

应用程序需要能够正确初始化，确保 `PumpRunner` 在被创建时可以访问到 `IndexStore` 实例。

### 评论

这是一个典型的依赖注入顺序问题。修复这个问题可以确保应用组件图的稳定性，即所有服务的消费者在实例化时都能获得其所依赖的实例。

### 目标

调整 `StitcherApp.__init__` 方法内部代码块的顺序，确保 "Indexing Subsystem" 在所有依赖它的 "Runners" 之前被初始化。

### 基本原理

由于 `PumpRunner` 现在依赖于 `IndexStore`，作为应用程序组合根的 `StitcherApp.__init__` 方法必须遵循这个依赖关系。我将把负责设置 `self.db_manager`、`self.index_store` 和 `self.file_indexer` 的 "Indexing Subsystem" 代码块移动到实例化任何 Runner 之前。

### 标签

#intent/fix #flow/ready #priority/critical #comp/engine #scope/core #ai/instruct #task/domain/refactor #task/object/pump-runner #task/action/index-first-optimization #task/state/continue

---

### Script

#### Acts 1: 调整 StitcherApp 的初始化顺序

我们将修改 `core.py`，将索引子系统的初始化逻辑提前。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        self.root_path = root_path
        self.workspace = Workspace(root_path)
        self.fingerprint_strategy = fingerprint_strategy
        # 1. Core Services
        self.doc_manager = DocumentManager(root_path)
        self.sig_manager = SignatureManager(root_path)
        self.scanner = ScannerService(root_path, parser)
        self.differ = Differ()
        self.merger = DocstringMerger()
        self.stubgen_service = StubgenService(
            root_path, self.scanner, self.doc_manager, transformer
        )

        # 2. Runners (Command Handlers)
        self.check_runner = CheckRunner(
            root_path,
            parser,
            self.doc_manager,
            self.sig_manager,
            self.differ,
            interaction_handler,
            fingerprint_strategy=self.fingerprint_strategy,
        )
        self.pump_runner = PumpRunner(
            root_path,
            self.doc_manager,
            self.sig_manager,
            transformer,
            self.differ,
            self.merger,
            interaction_handler,
            fingerprint_strategy=self.fingerprint_strategy,
            index_store=self.index_store,
        )
        self.init_runner = InitRunner(
            root_path,
            self.doc_manager,
            self.sig_manager,
            fingerprint_strategy=self.fingerprint_strategy,
        )
        self.transform_runner = TransformRunner(
            root_path, self.doc_manager, transformer
        )
        self.coverage_runner = CoverageRunner(root_path, self.doc_manager)

        # 3. Indexing Subsystem
        index_db_path = root_path / ".stitcher" / "index" / "index.db"
        self.db_manager = DatabaseManager(index_db_path)
        self.index_store = IndexStore(self.db_manager)
        self.file_indexer = FileIndexer(root_path, self.index_store)

        # Register Adapters
        search_paths = self.workspace.get_search_paths()
        self.file_indexer.register_adapter(
            ".py", PythonAdapter(root_path, search_paths)
        )

        self.index_runner = IndexRunner(self.db_manager, self.file_indexer)

        # 4. Refactor Runner (depends on Indexing)
        self.refactor_runner = RefactorRunner(
            root_path, self.index_store, self.file_indexer
        )
~~~~~
~~~~~python.new
        self.root_path = root_path
        self.workspace = Workspace(root_path)
        self.fingerprint_strategy = fingerprint_strategy
        # 1. Core Services
        self.doc_manager = DocumentManager(root_path)
        self.sig_manager = SignatureManager(root_path)
        self.scanner = ScannerService(root_path, parser)
        self.differ = Differ()
        self.merger = DocstringMerger()
        self.stubgen_service = StubgenService(
            root_path, self.scanner, self.doc_manager, transformer
        )

        # 2. Indexing Subsystem (Must be initialized before runners that use it)
        index_db_path = root_path / ".stitcher" / "index" / "index.db"
        self.db_manager = DatabaseManager(index_db_path)
        self.index_store = IndexStore(self.db_manager)
        self.file_indexer = FileIndexer(root_path, self.index_store)

        # Register Adapters
        search_paths = self.workspace.get_search_paths()
        self.file_indexer.register_adapter(
            ".py", PythonAdapter(root_path, search_paths)
        )

        # 3. Runners (Command Handlers)
        self.check_runner = CheckRunner(
            root_path,
            parser,
            self.doc_manager,
            self.sig_manager,
            self.differ,
            interaction_handler,
            fingerprint_strategy=self.fingerprint_strategy,
        )
        self.pump_runner = PumpRunner(
            root_path,
            self.doc_manager,
            self.sig_manager,
            transformer,
            self.differ,
            self.merger,
            interaction_handler,
            fingerprint_strategy=self.fingerprint_strategy,
            index_store=self.index_store,
        )
        self.init_runner = InitRunner(
            root_path,
            self.doc_manager,
            self.sig_manager,
            fingerprint_strategy=self.fingerprint_strategy,
        )
        self.transform_runner = TransformRunner(
            root_path, self.doc_manager, transformer
        )
        self.coverage_runner = CoverageRunner(root_path, self.doc_manager)
        self.index_runner = IndexRunner(self.db_manager, self.file_indexer)

        # 4. Refactor Runner (depends on Indexing)
        self.refactor_runner = RefactorRunner(
            root_path, self.index_store, self.file_indexer
        )
~~~~~

### 下一步建议

这个修复是继续我们重构工作的关键。一旦此补丁应用成功，`PumpRunner` 应该就能正确初始化了。

我建议在此之后，我们重新运行之前的计划来完成 `PumpRunner` 的重构。如果那个计划执行成功，我们就可以继续路线图上的下一个主要目标：**重构 `CheckRunner`**。
