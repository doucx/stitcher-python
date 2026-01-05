Your intuition is spot on. This is a classic namespace packaging problem, but with a subtle twist. You are absolutely correct that `pkgutil.extend_path` is the right mechanism, and our `pyneedle-*` packages are already using it.

The root cause is slightly different and more specific to the refactor command's logic: it's mistakenly trying to load the *distribution package name* (e.g., `pyneedle-pointer`) as if it were an *importable package name*. Griffe, correctly, cannot find a module named `pyneedle-pointer`.

The fix is to make the `refactor` command smarter. Instead of loading every distribution name it finds in `pyproject.toml`, it should discover the actual top-level *importable* packages (like `needle` and `stitcher`) and load those once. Griffe, combined with our correct `pkgutil` setup, will then properly assemble the full namespace.

I will generate a plan to fix this loading logic.

## [WIP] fix: Correct namespace package loading in refactor command

### 错误分析

用户在运行 `stitcher refactor apply` 时遇到 `ModuleNotFoundError`。

1.  **根本原因**: `refactor_command` 的实现逻辑有误。它扫描 `packages/` 目录，读取每个子项目的 `pyproject.toml` 文件，并将其 `[project].name` (例如, `pyneedle-pointer`) 直接传递给 `SemanticGraph.load()`。
2.  **问题点**: `pyneedle-pointer` 是一个**分发包 (distribution package)** 的名称，而不是一个**可导入包 (import package)** 的名称。Python 的导入系统（以及 Griffe）寻找的是名为 `needle` 的模块，而不是 `pyneedle-pointer`。
3.  **结论**: 我们错误地将分发包名称当作了导入路径，导致 Griffe 无法找到模块。虽然我们正确地使用了 `pkgutil` 来创建 `needle` 命名空间包，但我们从未正确地指示 Griffe 去加载 `needle` 这个命名空间本身。

### 用户需求

修复 `refactor` 命令，使其能够正确理解并加载由多个分发包组成的命名空间包（如 `needle`），从而成功构建完整的语义图谱。

### 评论

这是一个非常关键的修复。一个健壮的重构引擎必须能够准确理解项目的模块结构，特别是像我们这样使用命名空间包的复杂单体仓库。修复这个问题将使重构引擎能够真正“看懂”整个项目。

### 目标

修改 `packages/stitcher-cli/src/stitcher/cli/commands/refactor.py` 文件中的加载逻辑。新的逻辑将：
1.  扫描 `packages` 目录。
2.  识别出每个分发包提供的顶层可导入模块（例如，`pyneedle-pointer` 提供 `needle`）。
3.  收集所有唯一的顶层模块名。
4.  指示 `SemanticGraph` 加载这些唯一的顶层模块（`needle`, `stitcher`），而不是分发包的名称。

### 基本原理

我们将修改 `refactor_command` 中的循环。与其在循环中直接调用 `graph.load(pkg_name)`，我们将首先收集所有唯一的顶层包名到一个 `set` 中。这可以通过检查每个包的 `src/` 目录下的内容来确定。最后，在循环结束后，我们再遍历这个 `set`，一次性加载所有发现的顶层包。这将确保我们只加载 `needle` 一次，并让 `pkgutil` 和 Griffe 发挥作用，将所有 `pyneedle-*` 的部分组合成一个统一的 `needle` 命名空间。

### 标签

#intent/fix #flow/ready #priority/critical #comp/cli #comp/refactor #concept/state #scope/core #ai/brainstorm #task/domain/tooling #task/object/refactor-engine #task/action/dogfooding #task/state/continue

---

### Script

#### Acts 1: 修正 `refactor` 命令的包加载逻辑

我们将修补 `refactor.py` 文件，使其能够正确地发现并加载命名空间包。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/commands/refactor.py
~~~~~
~~~~~python.old
        # Discover packages to load from the monorepo structure
        packages_dir = root_path / "packages"
        if packages_dir.is_dir():
            for pkg_path in packages_dir.iterdir():
                pyproject_path = pkg_path / "pyproject.toml"
                if pyproject_path.exists():
                    with pyproject_path.open("rb") as f:
                        data = tomllib.load(f)
                        pkg_name = data.get("project", {}).get("name")
                        if pkg_name:
                            graph.load(pkg_name)

        ctx = RefactorContext(graph)
~~~~~
~~~~~python.new
        # Discover packages to load from the monorepo structure
        top_level_imports = set()
        packages_dir = root_path / "packages"
        if packages_dir.is_dir():
            for pkg_path in packages_dir.iterdir():
                src_dir = pkg_path / "src"
                if src_dir.is_dir():
                    for item in src_dir.iterdir():
                        if item.is_dir() and (item / "__init__.py").exists():
                            top_level_imports.add(item.name)

        for pkg_name in sorted(list(top_level_imports)):
            bus.debug(L.debug.log.msg, msg=f"Loading top-level package: {pkg_name}")
            graph.load(pkg_name)

        ctx = RefactorContext(graph)
~~~~~

### 下一步建议

这个补丁修正了加载逻辑。现在，请再次运行之前的迁移脚本：

```bash
stitcher refactor apply migrations/001_refactor_cli_l_pointers.py
```

这次它应该能够成功加载 `needle` 和 `stitcher` 命名空间，并正确地执行重构计划。
