**Bug 就在这里！**
1.  我调用了 `.with_project_name("my-project-plugin")`，这向 `self._pyproject_data` 添加了数据。
2.  我也调用了 `.with_source("pyproject.toml", ...)`，这向 `self._files_to_create` 添加了一个条目。
3.  在 `build()` 中，因为 `_pyproject_data` 不为空，它向 `_files_to_create` **追加**了另一个 `pyproject.toml` 条目（只包含 `name`，**没有 `version`**）。
4.  在写入文件循环中，由于这两个条目都针对 `pyproject.toml`，后一个条目（自动生成的、不完整的那个）**覆盖**了前一个条目（我手动提供的、完整的那个）。
5.  结果：磁盘上的 `pyproject.toml` 只包含 `[project] name="..."`，缺少 `version` 和 `build-system`，导致 `setuptools` 报错。

### [WIP] fix(test): 修复测试中的 pyproject.toml 覆盖问题

#### 错误分析
测试失败的根本原因是 `WorkspaceFactory` 的使用方式与实现逻辑冲突。同时使用 `.with_project_name()`（填充内部字典）和 `.with_source("pyproject.toml")`（提供原始文件）会导致生成两个 `pyproject.toml` 写入操作，后者覆盖前者，从而生成了一个不完整、无效的配置文件。

#### 用户需求
修复 `test_namespace_coexistence` 测试，确保生成的 `pyproject.toml` 是正确且完整的。

#### 目标
1.  修改 `tests/integration/test_stub_package_namespace.py`。
2.  **移除** 对 `factory_runtime.with_project_name("my-project-plugin")` 的调用。既然我们已经通过 `.with_source("pyproject.toml", ...)` 提供了完整的配置，就不需要再使用辅助 API 了。
3.  这将防止 `WorkspaceFactory` 自动生成那个覆盖性的、不完整的 `pyproject.toml`。

#### 基本原理
消除配置来源的二义性。如果我们在测试中手动提供了 `pyproject.toml` 的完整内容，就不应该再混合使用构建该文件的辅助方法。这将确保写入磁盘的正是我们定义的内容。

#### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/namespace-test #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 移除冗余的 with_project_name 调用

~~~~~act
patch_file
tests/integration/test_stub_package_namespace.py
~~~~~
~~~~~python.old
    factory_runtime = WorkspaceFactory(tmp_path / "proj_with_runtime")
    project_root_runtime = (
        factory_runtime.with_project_name("my-project-plugin")
        # This project provides the my_project.plugin namespace
        .with_source(
            "src/my_project/plugin.py",
~~~~~
~~~~~python.new
    factory_runtime = WorkspaceFactory(tmp_path / "proj_with_runtime")
    project_root_runtime = (
        # We manually provide pyproject.toml below, so we don't need with_project_name
        # This project provides the my_project.plugin namespace
        factory_runtime.with_source(
            "src/my_project/plugin.py",
~~~~~

### 下一步建议

这个修复应该能彻底解决 `pip install` 的问题。既然我们找到了确切的根本原因（文件覆盖），我对这次修复充满信心。

请再次运行 `pytest`。
-   **如果测试通过**：我们终于可以庆祝 Monorepo 命名空间测试的成功了。
-   **如果测试失败**：我会非常惊讶，并会仔细检查 `WorkspaceFactory` 是否还有其他副作用。
