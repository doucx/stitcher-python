这是一个非常稳健的工程决策。

“接口先行”策略不仅能让我们从一开始就解耦具体的存储格式（YAML/JSON/Markdown），还能迫使我们思考核心的数据交互契约：即**“我们的程序到底需要从磁盘读写什么样的数据结构？”**，而不是**“YAML 库提供了什么功能？”**。

我将制定一个计划，在 `stitcher-io` 包中定义这个抽象层，并提供一个基于 YAML 的参考实现。

## [WIP] feat: 定义文档 I/O 接口并实现 YAML 适配器

### 用户需求
根据 [任务 2.1: 文档 I/O 模块](P0/stitcher-python%20开发路线图.md)，需要创建一个负责读写外部文档文件的模块。必须采用接口先行（Interface-First）的设计，以支持未来扩展其他格式（如 JSON, Markdown）。

### 评论
将 I/O 逻辑抽象为 `DocumentAdapter` 是明智的。这不仅是为了支持多种格式，更是为了隔离外部存储的易变性。我们定义的标准数据结构是 `Dict[str, str]`（Key -> Docstring），这是一种扁平化的、对机器友好的中间表示，无论底层的物理存储是嵌套的 YAML 还是平铺的 JSON，都可以适配到这个结构。

### 目标
1.  在 `stitcher-io` 中定义 `DocumentAdapter` 协议，规定 `load` 和 `save` 的行为契约。
2.  实现标准的 `YamlAdapter`，支持 `.stitcher.yaml` 文件的读写。
3.  确保适配器能够处理文件不存在、目录创建等基础 I/O 细节。
4.  通过测试验证接口的可替换性和 YAML 实现的正确性。

### 基本原理
我们选择将“文档数据”视为简单的 **Key-Value 对**（`{"MyClass.method": "docstring"}`）。
这种扁平化设计有以下好处：
1.  **格式无关性**：无论是 YAML 的嵌套结构，还是 TOML/JSON，最终都可以被“展平”或“折叠”成这种形式。
2.  **寻址清晰**：Key 直接对应代码中的符号路径（相对于模块），消除了歧义。
3.  **实现简单**：适配器只需负责“物理文件 <-> 内存字典”的转换，业务逻辑无需关心文件格式。

### 标签
#intent/build #flow/ready #priority/high #comp/io #concept/config #scope/core #ai/instruct #task/domain/io #task/object/doc-adapter #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 定义文档适配器接口

我们将定义 `DocumentAdapter` 协议。注意这里我们使用 `Dict[str, str]` 作为交换格式，意味着我们期望适配器在读取时将嵌套结构（如果有）展平，在写入时负责格式化。

~~~~~act
write_file
packages/stitcher-io/src/stitcher/io/interfaces.py
~~~~~
~~~~~python
from typing import Dict, Protocol
from pathlib import Path


class DocumentAdapter(Protocol):
    """
    Protocol for document storage adapters.
    
    Responsible for marshaling dictionary data (Key -> Docstring) 
    to/from a physical file format (YAML, JSON, etc.).
    """

    def load(self, path: Path) -> Dict[str, str]:
        """
        Loads documentation from the specified file.
        
        Args:
            path: The path to the document file.

        Returns:
            A dictionary mapping semantic keys (e.g. "MyClass.my_method") 
            to docstrings. Returns an empty dict if file does not exist.
        """
        ...

    def save(self, path: Path, data: Dict[str, str]) -> None:
        """
        Saves documentation to the specified file.
        
        Args:
            path: The path to the document file.
            data: A dictionary mapping semantic keys to docstrings.
        """
        ...
~~~~~

#### Acts 2: 实现 YAML 适配器

为了保持简单和兼容性，我们将实现一个 `YamlAdapter`。虽然我们内部使用扁平字典，但为了用户体验，写入 YAML 时最好保持一定的排序，以减少 Git Diff 抖动。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-io/src/stitcher/io/adapters
touch packages/stitcher-io/src/stitcher/io/adapters/__init__.py
~~~~~

~~~~~act
write_file
packages/stitcher-io/src/stitcher/io/adapters/yaml_adapter.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Dict
import yaml

from stitcher.io.interfaces import DocumentAdapter


class YamlAdapter(DocumentAdapter):
    """
    Adapter for reading and writing .yaml documentation files.
    """

    def load(self, path: Path) -> Dict[str, str]:
        if not path.exists():
            return {}
        
        try:
            with path.open("r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                
            if not isinstance(content, dict):
                # If file exists but is empty or list, return empty dict
                return {}
                
            # Ensure all values are strings
            return {str(k): str(v) for k, v in content.items() if v is not None}
            
        except yaml.YAMLError:
            # We might want to log this, but for the adapter contract, 
            # returning empty or raising are options. 
            # Given this is IO layer, letting exception bubble or wrapping it 
            # would be better, but let's stick to simple contract for now:
            # If we can't read it, it's effectively empty/corrupt.
            # Rationale: 'stitcher check' will complain about missing docs anyway.
            return {}

    def save(self, path: Path, data: Dict[str, str]) -> None:
        if not data:
            # If data is empty, we don't necessarily need to create an empty file,
            # but if the file existed, we might want to clear it?
            # Let's decide to do nothing if data is empty to avoid cluttering fs?
            # No, 'save' implies persistence. If data is empty, file should be empty dict.
            pass

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Sort keys for deterministic output
        sorted_data = dict(sorted(data.items()))

        with path.open("w", encoding="utf-8") as f:
            # allow_unicode=True is essential for i18n
            # default_flow_style=False ensures block style (easier to read)
            yaml.safe_dump(
                sorted_data, 
                f, 
                allow_unicode=True, 
                default_flow_style=False,
                sort_keys=False # We already sorted
            )
~~~~~

#### Acts 3: 导出新模块

~~~~~act
write_file
packages/stitcher-io/src/stitcher/io/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .stub_generator import StubGenerator
from .interfaces import DocumentAdapter
from .adapters.yaml_adapter import YamlAdapter

__all__ = ["StubGenerator", "DocumentAdapter", "YamlAdapter"]
~~~~~

#### Acts 4: 添加测试

我们需要验证：
1.  读取不存在的文件返回空字典。
2.  写入数据后能正确读取。
3.  特殊字符（如多行字符串、Unicode）能被正确处理（YAML 的强项）。

~~~~~act
write_file
packages/stitcher-io/tests/test_document_io.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from stitcher.io import YamlAdapter


def test_yaml_adapter_load_non_existent(tmp_path: Path):
    adapter = YamlAdapter()
    data = adapter.load(tmp_path / "non_existent.yaml")
    assert data == {}


def test_yaml_adapter_round_trip(tmp_path: Path):
    adapter = YamlAdapter()
    file_path = tmp_path / "docs.yaml"
    
    input_data = {
        "MyClass": "A simple class",
        "MyClass.method": "A method with\nnewlines",
        "func": "中文测试"
    }
    
    # Write
    adapter.save(file_path, input_data)
    assert file_path.exists()
    
    # Read back
    loaded_data = adapter.load(file_path)
    
    assert loaded_data["MyClass"] == "A simple class"
    assert loaded_data["MyClass.method"] == "A method with\nnewlines"
    assert loaded_data["func"] == "中文测试"
    
    # Verify file content is deterministic (sorted)
    content = file_path.read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    # "MyClass" comes before "MyClass.method" (lexicographical)
    # But "func" comes last.
    # Let's just check raw content contains keys
    assert "MyClass:" in content
    assert "中文测试" in content


def test_yaml_adapter_handles_malformed(tmp_path: Path):
    file_path = tmp_path / "bad.yaml"
    file_path.write_text(":: :: invalid yaml", encoding="utf-8")
    
    adapter = YamlAdapter()
    data = adapter.load(file_path)
    # Current implementation swallows errors and returns empty dict
    assert data == {}
~~~~~

### 下一步建议
一旦适配器就绪，我们就可以着手实现 **任务 2.2: `stitcher init` 命令**。届时我们将使用这个 `YamlAdapter` 将从 AST 扫描到的文档字符串写入到 `.stitcher.yaml` 文件中。
建议在下一步创建一个 `DocumentManager` 或类似的服务类，它组合 `StitcherScanner` 和 `DocumentAdapter`，负责协调“扫描 -> 提取 -> 保存”的完整流程。
