简要回答：
测试失败的原因是作为输入的 `source_content` 缺少类型注解，导致 Stitcher 生成的 Stub 也不包含返回类型，Pyright 自然解析为 `Unknown`。我将修改测试数据，添加明确的类型注解。

## [WIP] fix(tests): 为 IDE Proxy 测试添加缺失的类型注解

### 错误分析
在 `test_pyright_resolves_types_from_stubs` 测试中，Pyright 报告 `instance.get_id()` 的类型为 `Unknown`，导致断言失败。

根本原因在于测试数据 `source_content`：
```python
source_content = "class ProxyModel:\n    def get_id(self):\n        return 1"
```
这段代码没有任何类型注解。Stitcher 的扫描器基于 AST 提取类型信息，如果源码没有注解，生成的 `.pyi` 文件中该方法也会缺少返回类型注解（即 `def get_id(self): ...`）。

因此，Pyright 无法从 Stub 中推断出 `int` 是符合预期的正确行为（Garbage In, Garbage Out）。要验证 Pyright 能从 Stub **读取** 类型，我们必须先确保 Stub **包含** 类型。

### 用户需求
修复 `tests/integration/test_ide_proxy.py` 中的测试数据，使其包含类型注解，从而验证端到端的类型解析流程。

### 评论
这是一个典型的测试数据质量问题。通过为输入数据添加 `-> int`，我们可以确保生成的 Stub 包含 `def get_id(self) -> int: ...`，从而使 Pyright 能够正确解析。

为了增强测试的说服力，理论上运行时代码可以不带注解（模拟发布后的纯代码），但即使两者都有注解，根据 PEP 561，Stub 包的存在也应被优先读取。最简单的修复是统一添加注解。

### 目标
1.  修改 `test_pyright_resolves_types_from_stubs` 中的 `source_content` 变量，添加 `-> int` 返回类型注解。

### 基本原理
只有当 Stitcher 能够扫描到类型信息时，它才能将其放入 Stub 中。Pyright 依赖 Stub 中的显式注解来解析类型。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/ide-proxy #task/action/fix-test-data #task/state/continue

---

### Script

#### Acts 1: 修正测试数据

为 `source_content` 添加 `-> int` 类型注解。

~~~~~act
patch_file
tests/integration/test_ide_proxy.py
~~~~~
~~~~~python.old
    source_content = "class ProxyModel:\n    def get_id(self):\n        return 1"

    # 1. Create the source project for Stitcher to scan.
~~~~~
~~~~~python.new
    source_content = "class ProxyModel:\n    def get_id(self) -> int:\n        return 1"

    # 1. Create the source project for Stitcher to scan.
~~~~~

### 下一步建议
运行测试，确认 Pyright 现在能够正确解析出 `int` 类型。如果测试通过，说明整个 Stub 生成、安装和解析的链路是畅通的。
