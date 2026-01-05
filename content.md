You are absolutely right. The test failed, and the traceback provides the crucial clue. My apologies, I missed a fundamental detail in how `Griffe` resolves modules within different project layouts.

The traceback clearly shows a `ModuleNotFoundError: cascade`. Here's a breakdown of why this happened:

1.  **Project Structure**: In the test, I created a standard `src` layout: `tmp_path/src/cascade`.
2.  **`SemanticGraph` Configuration**: My current implementation of `SemanticGraph` initializes `GriffeLoader` with a search path of `[self.root_path]`, which in this case is `tmp_path`.
3.  **Griffe's Perspective**: When I call `graph.load("cascade")`, Griffe looks for a top-level module named `cascade` inside `tmp_path`. It does not find one. What exists is a directory named `src`, which *contains* the `cascade` package.
4.  **The Correct Path**: For Griffe to find the `cascade` module, its search path needs to include `tmp_path/src`.

The root cause is that my `SemanticGraph` is not "src-layout aware". It assumes all packages are at the project root, which is an incorrect assumption for many modern Python projects.

The fix is to make `SemanticGraph` smarter. It needs to detect if a `src` layout is being used and configure Griffe's search paths accordingly. The search path should include both the `src` directory (for packages like `cascade`) and the project root (for top-level modules like `app.py`).

I will generate a plan to first fix this bug in `SemanticGraph` and then re-run the test I previously wrote, which should now pass.

## [WIP] fix(refactor): Make SemanticGraph src-layout aware to fix module resolution

### 错误分析

The test `test_move_deeply_nested_directory_updates_all_references_and_sidecars` fails with `ModuleNotFoundError: cascade`. This is because `SemanticGraph` was configured to search for modules only in the project's root directory (`tmp_path`). It did not look inside the `src` directory, where the `cascade` package was located, leading to Griffe being unable to find and load the module.

### 用户需求

修复因 `SemanticGraph` 无法正确处理 `src` 布局而导致的测试失败。

### 评论

这是一个非常重要的修复。不支持 `src` 布局是一个严重的缺陷，会使重构引擎在许多真实世界的项目中无法使用。通过让 `SemanticGraph` 自动检测并适应 `src` 布局，我们不仅修复了这个 Bug，还显著增强了工具的健壮性和实用性。

### 目标

1.  修改 `stitcher.refactor.engine.graph.SemanticGraph.__init__` 方法。
2.  使其能够检测 `root_path / "src"` 是否存在。
3.  如果存在，则将 `src` 目录和根目录都添加到 Griffe 的搜索路径中。
4.  确保修复后，之前失败的深层嵌套目录移动测试能够成功通过。

### 基本原理

我们将修改 `SemanticGraph` 的构造函数。它会检查 `self.root_path / "src"` 是否是一个目录。如果是，它将初始化 `GriffeLoader` 时传入 `search_paths=[self.root_path / "src", self.root_path]`。这使得 Griffe 能够无缝地解析两种类型的模块：
-   位于 `src` 目录下的包（如 `cascade`）。
-   位于项目根目录下的独立模块（如 `app.py`）。

这个改动对 `SemanticGraph` 的调用者是透明的，它会自动适应不同的项目结构。

### 标签

#intent/fix #flow/ready #priority/critical #comp/engine #scope/core #ai/instruct #task/domain/testing #task/object/test-coverage #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `SemanticGraph` 以支持 `src` 布局

我将 `patch_file` 来更新 `SemanticGraph` 的 `__init__` 方法，使其能够正确设置 Griffe 的搜索路径。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
class SemanticGraph:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self._griffe_loader = griffe.GriffeLoader(search_paths=[self.root_path])
        self._modules: Dict[str, griffe.Module] = {}
        self.registry = UsageRegistry()
~~~~~
~~~~~python.new
class SemanticGraph:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        search_paths = [self.root_path]
        src_path = self.root_path / "src"
        if src_path.is_dir():
            search_paths.insert(0, src_path)

        self._griffe_loader = griffe.GriffeLoader(search_paths=search_paths)
        self._modules: Dict[str, griffe.Module] = {}
        self.registry = UsageRegistry()
~~~~~

### 下一步建议

现在 `SemanticGraph` 的核心缺陷已经修复。我将再次运行 `test_move_deeply_nested_directory_updates_all_references_and_sidecars` 测试。根据我的分析，这次它应该会成功通过。

一旦测试通过，我们就可以将这个修复和新增的测试用例一起提交。请确认我是否可以继续。
