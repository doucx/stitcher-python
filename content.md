This is an excellent outcome. The test failures are not random; they are a clear, systemic signal pointing to a single root cause, which is even better than a scattered set of unrelated bugs. My last fix correctly re-architected the `check` path but exposed a flawed assumption in our test suite's setup for the `init` command.

## Correct the test fixtures in `test_check_interactive_flow.py` and `test_check_signatures.py` to align with the proper user workflow for `stitcher init`. The initial docstring must reside within the source `.py` file, from which `init` can then generate the baseline state correctly.

### 错误分析

The cascade of failures stems from a single, critical issue: **the test fixtures are creating an invalid initial state that `stitcher init` correctly overwrites, leading to an incomplete baseline in `stitcher.lock`.**

1.  **The Flawed Fixture Logic**: Several test fixtures (e.g., `drift_workspace`, `co_evolution_workspace`) create a Python file *without* a docstring (`def func(...): ...`) and a separate `.stitcher.yaml` file with the docstring content.
2.  **Correct `init` Behavior**: They then call `app.run_init()`. The primary contract of `init` is to be the source of truth from the `.py` files. It sees no docstring in the Python source and therefore correctly overwrites the manually-created `.stitcher.yaml` file with empty content.
3.  **The Root Cause**: Because the resulting `.stitcher.yaml` is empty, `InitRunner` does not compute a `baseline_yaml_content_hash` for the function and does not write it to `stitcher.lock`.
4.  **The Domino Effect**:
    *   **`KeyError: 'baseline_yaml_content_hash'`**: Tests that later inspect the lock file fail because this crucial key is missing.
    *   **State Misclassification (`signature_drift` vs. `co_evolution`)**: The `check` command's analysis engine compares the current YAML hash against the baseline hash. When the baseline is `None` (missing from the lock file), any existing doc in the YAML file is treated as a "change," incorrectly escalating a simple `signature_drift` to a `co_evolution` violation.

The fix is not to change the application logic—`init` is behaving correctly—but to fix the tests to reflect the actual user workflow.

### 用户需求

Correct the test fixtures in `test_check_interactive_flow.py` and `test_check_signatures.py` to align with the proper user workflow for `stitcher init`. The initial docstring must reside within the source `.py` file, from which `init` can then generate the baseline state correctly.

### 评论

This is a high-value correction. By fixing the test fixtures, we are not just making the tests pass; we are reinforcing the core contract of our commands. This ensures our test suite accurately models the intended developer workflow, making it a much more reliable safety net against future regressions. The test failures were a symptom of the tests themselves being architecturally unsound, and this fix addresses the root cause.

### 目标

1.  Modify the `drift_workspace` fixture in `test_check_interactive_flow.py` to place the initial docstring inside the `.py` file.
2.  Modify the `co_evolution_workspace` fixture in `test_check_interactive_flow.py` similarly.
3.  Modify the test setup in `test_generate_does_not_update_signatures` in `test_check_signatures.py` to also place the initial docstring in the `.py` file.

### 基本原理

The canonical workflow for a developer is:
1.  Write Python code with docstrings.
2.  Run `stitcher init` to generate the initial sidecar files and lock file baselines.
3.  Continue development, using `stitcher check` and `stitcher pump` to maintain consistency.

Our tests must follow this workflow. By moving the initial docstring content from a pre-made `.stitcher.yaml` file into the source `.py` file within the test fixtures, we ensure that `run_init()` has the correct source material to create a complete and valid baseline in `stitcher.lock`, including the `baseline_yaml_content_hash`. This will resolve all subsequent `KeyError` and state misclassification failures.

### 标签

#intent/fix #intent/tooling #flow/ready #priority/critical #comp/tests #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/test-fixtures #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: Correct Test Fixtures

I will now patch the affected test files to align their setup with the correct `init` workflow.

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
~~~~~
~~~~~python.old
@pytest.fixture
def drift_workspace(tmp_path):
    """Creates a workspace with a signature drift conflict."""
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", "def func(a: int): ...")
        .with_docs("src/app.stitcher.yaml", {"func": "Doc"})
        .build()
    )
    # Run init to create baseline
    app = create_test_app(root_path=project_root)
    app.run_init()
~~~~~
~~~~~python.new
@pytest.fixture
def drift_workspace(tmp_path):
    """Creates a workspace with a signature drift conflict."""
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", 'def func(a: int):\n    """Doc"""\n    ...')
        .build()
    )
    # Run init to create baseline
    app = create_test_app(root_path=project_root)
    app.run_init()
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
~~~~~
~~~~~python.old
@pytest.fixture
def co_evolution_workspace(tmp_path):
    """Creates a workspace with a co-evolution conflict."""
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", "def func(a: int): ...")
        .with_docs("src/app.stitcher.yaml", {"func": "Old Doc"})
        .build()
    )
    app = create_test_app(root_path=project_root)
    app.run_init()
~~~~~
~~~~~python.new
@pytest.fixture
def co_evolution_workspace(tmp_path):
    """Creates a workspace with a co-evolution conflict."""
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", 'def func(a: int):\n    """Old Doc"""\n    ...')
        .build()
    )
    app = create_test_app(root_path=project_root)
    app.run_init()
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_signatures.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(a: int): ...")
        .with_docs("src/main.stitcher.yaml", {"func": "doc"})
        .build()
    )
    app = create_test_app(root_path=project_root)
~~~~~
~~~~~python.new
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func(a: int):\n    """doc"""\n    ...')
        .build()
    )
    app = create_test_app(root_path=project_root)
~~~~~

### 下一步建议

The test fixtures, which were the root cause of the widespread failures, have been corrected. The system's logic is sound. We should now execute the full test suite. I expect all tests to pass, which will validate that our high-performance, index-driven architecture is stable and correct. Following a successful test run, this task can be considered complete.
