You are absolutely right to ask, "How did the test environment leak?" That is the core of the problem.

My previous fix addressed the file creation order, but now we're hitting a more subtle issue. The test runner (`pytest`) modifies `sys.path` to include all the packages from your development monorepo. When the `refactor` command runs our code analysis engine (`griffe`), the engine sees this global `sys.path` and attempts to scan your *entire* development workspace, not just the isolated temporary directory created for the test. This breaks test isolation and causes the `ModuleNotFoundError` when it tries to load a workspace package it doesn't fully understand.

The solution is to explicitly tell our analysis engine to *only* look for code inside the test directory, effectively isolating it from the leaky environment.

## [WIP] fix(refactor): Isolate analysis engine from global sys.path

### 错误分析

The integration tests for the `refactor` command are failing because the underlying analysis engine (`griffe`) is "leaking" out of the isolated test environment. It is inheriting the `sys.path` from the `pytest` runner, which includes all packages from the development monorepo. This causes it to try and analyze the entire development workspace instead of just the self-contained project within `tmp_path`, leading to a `ModuleNotFoundError` when it encounters a workspace package it cannot resolve. This breaks the fundamental principle of test isolation.

### 用户需求

The user needs to fix the new failures in `test_refactor_command.py` by preventing the test environment from leaking into the application code being tested.

### 评论

This is a critical fix for test stability and correctness. By ensuring the code analysis engine is strictly confined to the test workspace, we make the tests more robust, deterministic, and independent of the environment in which they are run. This change enforces proper test isolation at the application level.

### 目标

1.  Modify the `SemanticGraph` class within the `stitcher-refactor` package.
2.  When initializing `griffe.GriffeLoader`, explicitly provide the `sys_path` argument, setting it to the same search paths derived from the test project's root. This will prevent `griffe` from using the global `sys.path`.

### 基本原理

The `griffe.GriffeLoader` constructor accepts an optional `sys_path` argument. If not provided, it defaults to using the `sys.path` of the current process. By explicitly setting `sys_path=self.search_paths`, we constrain `griffe`'s module discovery mechanism to operate solely within the boundaries of the project being analyzed (in this case, the temporary test directory). This effectively seals the environment leak and restores proper test isolation.

### 标签

#intent/fix #flow/ready #priority/high #comp/engine #comp/tests #concept/state #ai/instruct #task/domain/testing #task/object/environment-isolation #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: Constrain the analysis engine to the test workspace

I will patch `stitcher-refactor/src/stitcher/refactor/engine/graph.py` to correctly configure the `griffe` loader, ensuring it operates only within the provided search paths.

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
        # Store unique, sorted paths for deterministic behavior
        self.search_paths = sorted(list(set(search_paths)))

        self._griffe_loader = griffe.GriffeLoader(search_paths=self.search_paths)
        self._modules: Dict[str, griffe.Module] = {}
        self.registry = UsageRegistry()
~~~~~
~~~~~python.new
        # Store unique, sorted paths for deterministic behavior
        self.search_paths = sorted(list(set(search_paths)))

        self._griffe_loader = griffe.GriffeLoader(
            search_paths=self.search_paths,
            # Crucially, tell Griffe to ONLY look in our search paths
            # and not leak into the test runner's global sys.path.
            sys_path=self.search_paths,
        )
        self._modules: Dict[str, griffe.Module] = {}
        self.registry = UsageRegistry()
~~~~~

### 下一步建议

This change should fully resolve the test failures. Please run the test suite again. If it passes, we can proceed to create a `[COMMIT]` plan to finalize this fix.
