简要回答：
好的，我们现在从单元测试升级到集成测试。这将是项目的第一个端到端 (E2E) 测试，它不仅验证各个组件的逻辑，还验证它们之间的协同工作以及对文件系统的实际操作。

**RED 阶段**：我们将编写一个测试，它创建一个临时的 Python 源文件，然后调用 `stitcher-application`（我们还没实现）去扫描它并在旁边生成一个 `.pyi` 文件。

## [WIP] test(e2e): 添加 Application 层端到端集成测试 (Red Phase)

### 用户需求
开始 Application 层的开发。首先创建一个 E2E 集成测试，该测试通过验证从源文件到 `.pyi` 文件的完整生成流程，来驱动 `StitcherApp` 类的设计与实现。

### 评论
**测试策略**：
我们将使用 `pytest` 的 `tmp_path` fixture 来创建一个隔离的测试环境。
1.  **Arrange**: 在 `tmp_path` 中写入一个 `source.py` 文件。
2.  **Act**: 初始化 `StitcherApp` 并调用其 `run_scan_and_generate(file_path)` 方法。
3.  **Assert**: 检查 `source.pyi` 是否被创建，且内容包含预期的函数签名和文档字符串。

这个测试不仅验证了逻辑，还隐式地验证了文件 I/O 操作。

### 目标
1.  创建 `tests/integration/test_end_to_end.py`。
2.  编写 `test_app_scan_and_generate_single_file` 测试用例。
3.  引用 `stitcher.app.StitcherApp`（即使它还不存在）。
4.  运行 `pytest` 并预期失败。

### 基本原理
通过在集成层进行 TDD，我们确保了所有组件（Scanner, IO, Config, App）能够正确地“缝合”在一起，形成一个可交付的功能。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/tests #comp/app #scope/core #ai/instruct
#task/domain/testing #task/object/e2e-tests #task/action/create-case
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 创建集成测试文件 (RED)
~~~~~act
write_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from textwrap import dedent

# This module doesn't exist yet, driving its creation
from stitcher.app import StitcherApp

def test_app_scan_and_generate_single_file(tmp_path):
    # 1. Arrange: Create a source python file
    source_content = dedent("""
        def greet(name: str) -> str:
            \"\"\"Returns a greeting.\"\"\"
            return f"Hello, {name}!"
    """)
    source_file = tmp_path / "greet.py"
    source_file.write_text(source_content, encoding="utf-8")
    
    # 2. Act: Initialize App and run generation
    app = StitcherApp(root_path=tmp_path)
    # We expect this method to scan the file and generate a .pyi next to it
    generated_files = app.run_generate(files=[source_file])
    
    # 3. Assert: Verify the .pyi file exists and has correct content
    expected_pyi_path = tmp_path / "greet.pyi"
    
    assert expected_pyi_path.exists()
    assert expected_pyi_path in generated_files
    
    pyi_content = expected_pyi_path.read_text(encoding="utf-8")
    
    # Verify core components are present
    assert "def greet(name: str) -> str:" in pyi_content
    assert '"""Returns a greeting."""' in pyi_content
    assert "..." in pyi_content
~~~~~

#### Acts 2: 创建 App 占位符
为了让导入不报错（或者是为了让测试更进一层），我们需要创建 `StitcherApp` 的骨架。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List

class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path

    def run_generate(self, files: List[Path]) -> List[Path]:
        """
        Scans the given files and generates .pyi stubs for them.
        Returns the list of generated .pyi file paths.
        """
        # TODO: Implement orchestration logic
        return []
~~~~~

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .core import StitcherApp

__all__ = ["StitcherApp"]
~~~~~

### 下一步建议
运行 `pytest`。测试将因断言失败（返回空列表或文件不存在）而失败。
接下来，我们将进入 **GREEN** 阶段：在 `StitcherApp.run_generate` 中编排 Scanner 和 StubGenerator，真正地实现文件生成逻辑。
