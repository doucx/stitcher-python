简单回答
修复测试中因命名空间包配置不当导致的模块加载不全问题。

## [WIP] fix: 修复 monorepo 测试中命名空间包的声明方式

### 错误分析

集成测试 `test_move_directory_monorepo_e2e.py` 失败，断言错误显示跨包引用未被更新。

根本原因是测试环境构建的 monorepo 结构不正确。测试使用了两个同名的顶层包 `cascade`（分别位于 `cascade-engine` 和 `cascade-runtime`），但将它们的 `__init__.py` 内容设置为空字符串 `""`。在 Python 导入机制中，这会将它们定义为**常规包**（Regular Package）而非**命名空间包**（Namespace Package）。这导致了包遮蔽（Shadowing）：工具链（包括 Griffe）只加载了它在搜索路径中找到的第一个 `cascade` 包，而忽略了第二个。因此，位于第二个包中的 `app.py` 从未被加载进语义图谱，重构引擎也就无法发现并更新其中的引用。

### 用户需求

修复 `tests/integration/test_move_directory_monorepo_e2e.py` 中的 `AssertionError`，确保目录移动操作能正确更新跨包引用。

### 评论

这是一个典型的 Python 打包陷阱。在模拟 monorepo 环境时，必须显式地将共享命名空间的包声明为 Namespace Package（通常使用 `pkgutil` 风格），以确保所有分布在不同目录下的子模块都能被正确发现和合并。

### 目标

修改测试文件 `packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py`，在构建测试工作区时，向 `cascade/__init__.py` 注入标准的 `pkgutil` 命名空间声明代码。

### 基本原理

通过将 `__init__.py` 的内容从空字符串修改为 `__path__ = __import__('pkgutil').extend_path(__path__, __name__)`，我们明确告知 Python 解释器和静态分析工具这是一个命名空间包。这将允许 `SemanticGraph` 正确地从多个源目录聚合 `cascade` 包的所有内容，从而使重构引擎能够看到全局视图并正确应用变更。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/monorepo-support #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 注入 pkgutil 命名空间声明

我们将修改测试文件中两处创建 `cascade/__init__.py` 的代码，添加 `pkgutil` 扩展路径的逻辑。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py
~~~~~
~~~~~python
        .with_pyproject("cascade-engine")
        .with_source("cascade-engine/src/cascade/__init__.py", "")
        .with_source("cascade-engine/src/cascade/engine/__init__.py", "")
~~~~~
~~~~~python
        .with_pyproject("cascade-engine")
        .with_source(
            "cascade-engine/src/cascade/__init__.py",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
        )
        .with_source("cascade-engine/src/cascade/engine/__init__.py", "")
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py
~~~~~
~~~~~python
        .with_pyproject("cascade-runtime")
        .with_source("cascade-runtime/src/cascade/__init__.py", "")
        .with_source("cascade-runtime/src/cascade/runtime/__init__.py", "")
~~~~~
~~~~~python
        .with_pyproject("cascade-runtime")
        .with_source(
            "cascade-runtime/src/cascade/__init__.py",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
        )
        .with_source("cascade-runtime/src/cascade/runtime/__init__.py", "")
~~~~~

### 下一步建议

执行此计划后，再次运行 `pytest packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py`。如果测试通过，说明问题已解决，可以进行代码提交。如果仍有其他问题，可能需要检查 `SemanticGraph` 对命名空间包的加载逻辑是否还有其他假设。
