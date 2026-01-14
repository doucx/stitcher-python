My apologies. It seems my previous fix was incomplete. The error is still occurring, but now only in two specific test files within the `stitcher-cli` package.

This pattern strongly indicates that these tests are not using the test helpers I previously patched and are instead instantiating the application in a way that bypasses the database initialization. I will now implement a more robust and centralized fix to resolve this permanently.

## [WIP] fix: Centralize DB initialization in StitcherApp constructor

### 错误分析
The remaining `sqlite3.OperationalError: no such table: symbols` failures are isolated to tests in `stitcher-cli`. These tests import and use a global `StitcherApp` instance. My previous fix correctly added database initialization to a test helper (`create_test_app`), but these failing tests do not use that helper. The root cause is that the `StitcherApp` constructor itself does not guarantee that the database is initialized, making its instances unreliable without an explicit, external call to `initialize()`.

### 用户需求
Fix the final two test failures by ensuring any instance of `StitcherApp` is created with a fully initialized database, making the test environment and production behavior consistent and robust.

### 评论
This is the definitive fix for this class of errors. By moving the initialization logic into the `StitcherApp` constructor, we establish a class invariant: any `StitcherApp` object is guaranteed to have a ready-to-use database. This is a cleaner, more reliable design that prevents similar errors in the future, regardless of how the application is instantiated in tests or production.

### 目标
1.  Modify `StitcherApp.__init__` to call `self.db_manager.initialize()` immediately after the database manager is created.
2.  Remove the now-redundant `initialize()` call from the `create_test_app` test helper to avoid duplication.

### 基本原理
By making database initialization a responsibility of the `StitcherApp` constructor, we ensure that every instance of the application is created in a valid, usable state. The `initialize` method is idempotent (`CREATE TABLE IF NOT EXISTS`), so this change is safe and has negligible performance impact. This change centralizes the setup logic and makes the system more predictable.

### 标签
#intent/fix #flow/ready #priority/critical #comp/application #comp/tests #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/database #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: Centralize database initialization in the application core
I will add the `initialize()` call to `StitcherApp.__init__`, ensuring every instance is created with a valid database schema.

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        # 1. Indexing Subsystem (Promoted to Priority 1 initialization)
        index_db_path = root_path / ".stitcher" / "index" / "index.db"
        self.db_manager = DatabaseManager(index_db_path)
        self.index_store = IndexStore(self.db_manager)
        self.file_indexer = FileIndexer(root_path, self.index_store)
~~~~~
~~~~~python.new
        # 1. Indexing Subsystem (Promoted to Priority 1 initialization)
        index_db_path = root_path / ".stitcher" / "index" / "index.db"
        self.db_manager = DatabaseManager(index_db_path)
        self.db_manager.initialize()
        self.index_store = IndexStore(self.db_manager)
        self.file_indexer = FileIndexer(root_path, self.index_store)
~~~~~

#### Acts 2: Remove redundant initialization from test helper
Now that the constructor handles initialization, I will clean up the `create_test_app` helper to remove the duplicate call.

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py
~~~~~
~~~~~python.old
def create_test_app(
    root_path: Path, interaction_handler: Optional[InteractionHandler] = None
) -> StitcherApp:
    parser = GriffePythonParser()
    transformer = PythonTransformer()
    strategy = PythonFingerprintStrategy()
    app = StitcherApp(
        root_path=root_path,
        parser=parser,
        transformer=transformer,
        fingerprint_strategy=strategy,
        interaction_handler=interaction_handler,
    )
    # Eagerly initialize the database for test reliability.
    # It's idempotent (CREATE TABLE IF NOT EXISTS), so it's safe to call.
    app.db_manager.initialize()
    return app
~~~~~
~~~~~python.new
def create_test_app(
    root_path: Path, interaction_handler: Optional[InteractionHandler] = None
) -> StitcherApp:
    parser = GriffePythonParser()
    transformer = PythonTransformer()
    strategy = PythonFingerprintStrategy()
    app = StitcherApp(
        root_path=root_path,
        parser=parser,
        transformer=transformer,
        fingerprint_strategy=strategy,
        interaction_handler=interaction_handler,
    )
    # Database is now initialized in StitcherApp constructor.
    return app
~~~~~

### 下一步建议
This should resolve all database-related test failures. After confirming the test suite passes, we can finally proceed to the last step of the architectural refactor: modifying the `CheckRunner` to consume data from the index, which will fully realize the planned performance improvements.
