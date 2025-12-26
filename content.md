简单回答
测试失败的原因非常明确：我们在逻辑中将 `MISSING` 从错误降级为了警告，但现有的集成测试仍在断言其为 `error` 级别；同时，由于恢复了属性值的输出，单元测试中的预期“黄金标准”字符串也需要同步更新。

## [WIP] test: 同步测试用例以适配 check 降级逻辑与属性值输出

### 错误分析
**1. 集成测试失败 (`test_check_detects_missing_and_extra`)**:
*   **原因**: 上一个计划将 `MISSING` 消息的发送级别从 `bus.error` 改为了 `bus.warning`。
*   **断言冲突**: 测试用例第 36 行 `spy_bus.assert_id_called(L.check.issue.missing, level="error")` 显式要求级别为 `error`，导致断言失败。

**2. 单元测试失败 (`test_generate_simple_pyi`)**:
*   **原因**: 我们恢复了 `StubGenerator` 中对 `attr.value` 的输出（例如 `VERSION: str = "0.1.0"`）。
*   **预期不符**: 测试用例中的 `expected_pyi` 字符串仍停留在旧的逻辑，认为属性不应包含赋值部分（`VERSION: str`）。

### 用户需求
修复受逻辑变更影响的测试用例，确保测试套件能正确验证新的行为。

### 评论
测试用例的失效正是由于代码逻辑发生了**符合预期**的变更。在调整了业务逻辑（降级警告、增加输出保真度）后，及时同步测试基准是保持 CI/CD 健康的必要步骤。

### 目标
1.  更新 `test_check_command.py`，将针对 `MISSING` 的断言级别改为 `warning`。
2.  更新 `test_stub_generator.py`，在预期字符串中补全属性赋值。

### 基本原理
- **语义对齐**: 将测试中的 `level="error"` 改为 `level="warning"`，使其与 `StitcherApp.run_check` 中的新路由逻辑一致。
- **基准更新**: 更新黄金标准文件（Golden Files），将 `VERSION: str` 修正为 `VERSION: str = "0.1.0"`，将 `CLASS_VAR: Optional[int]` 修正为 `CLASS_VAR: Optional[int] = None`。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/test-synchronization #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 修正集成测试断言级别

修改 `test_check_command.py`，将缺失文档的级别断言改为 `warning`。

~~~~~act
patch_file
tests/integration/test_check_command.py
~~~~~
~~~~~python.old
    # 3. Assert
    assert success is False

    spy_bus.assert_id_called(L.check.file.fail, level="error")
    spy_bus.assert_id_called(L.check.issue.missing, level="error")
    spy_bus.assert_id_called(L.check.issue.extra, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")
~~~~~
~~~~~python.new
    # 3. Assert
    assert success is False

    spy_bus.assert_id_called(L.check.file.fail, level="error")
    spy_bus.assert_id_called(L.check.issue.missing, level="warning")
    spy_bus.assert_id_called(L.check.issue.extra, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")
~~~~~

#### Acts 2: 修正生成器单元测试基准

修改 `test_stub_generator.py`，更新预期生成的 `.pyi` 内容，补全属性赋值。

~~~~~act
patch_file
packages/stitcher-io/tests/test_stub_generator.py
~~~~~
~~~~~python.old
    # 2. Arrange: Define the expected golden .pyi output string.
    expected_pyi = dedent("""
        \"\"\"This is a test module.\"\"\"
        
        VERSION: str
        
        @my_decorator
        async def my_function(arg1: int, arg2: str = 'default') -> bool:
            \"\"\"A test function.\"\"\"
            ...

        class MyClass(Base):
            \"\"\"A test class.\"\"\"
            CLASS_VAR: Optional[int]
            
            def __init__(self, val: float) -> None: ...
            
            def do_work(self) -> str:
                \"\"\"Does some work.\"\"\"
                ...
    """).strip()
~~~~~
~~~~~python.new
    # 2. Arrange: Define the expected golden .pyi output string.
    expected_pyi = dedent("""
        \"\"\"This is a test module.\"\"\"

        VERSION: str = "0.1.0"

        @my_decorator
        async def my_function(arg1: int, arg2: str = 'default') -> bool:
            \"\"\"A test function.\"\"\"
            ...

        class MyClass(Base):
            \"\"\"A test class.\"\"\"
            CLASS_VAR: Optional[int] = None

            def __init__(self, val: float) -> None: ...

            def do_work(self) -> str:
                \"\"\"Does some work.\"\"\"
                ...
    """).strip()
~~~~~

### 下一步建议
重新运行测试套件。预期结果是所有 48 个测试文件均通过，且 `stitcher check` 在项目根目录运行时将返回成功。这意味着 Dogfooding 阶段的所有技术阻碍已完全清除。
