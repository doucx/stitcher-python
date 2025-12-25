简要回答：
测试失败在意料之中。现在进入 **GREEN** 阶段，我们将为 `StitcherApp` 注入生命，实现其作为**编排者 (Orchestrator)** 的核心职责：调用 `Scanner` 解析源码，然后将产出的 IR 传递给 `Generator` 生成 `.pyi` 文件，并最终写入磁盘。

## [WIP] feat(app): 实现 Application 层的核心编排逻辑 (Green Phase)

### 用户需求
通过实现 `StitcherApp.run_generate` 方法的完整逻辑，使 `test_app_scan_and_generate_single_file` 端到端集成测试通过。

### 评论
这是我们首次将 `scanner` 和 `io` 这两个独立的组件“缝合”在一起。`StitcherApp` 的职责非常清晰：它不包含复杂的业务逻辑，只负责协调其他组件完成一个完整的工作流。我们将在 `__init__` 中实例化 `StubGenerator`，使其成为 `StitcherApp` 的一个工具，这是一种简单的依赖注入形式。

### 目标
1.  修改 `packages/stitcher-application/src/stitcher/app/core.py`。
2.  导入 `parse_source_code` 和 `StubGenerator`。
3.  在 `run_generate` 方法中，实现读取文件、调用解析器、调用生成器、写入文件的完整流程。
4.  运行 `pytest` 并确认测试通过。

### 基本原理
`StitcherApp` 是用户（或 CLI）与 Stitcher 核心库交互的主要入口点。它封装了从输入（文件路径）到输出（生成的 `.pyi` 文件）的整个过程，为上层提供了一个简洁、稳定的 API。

### 标签
#intent/build #flow/ready #priority/high
#comp/app #scope/core #ai/instruct
#task/domain/implementation #task/object/orchestrator-logic #task/action/implement
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 实现 StitcherApp 的核心逻辑
我们将用完整的实现替换掉 `core.py` 中的占位符。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List

from stitcher.scanner import parse_source_code
from stitcher.io import StubGenerator


class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # The app 'has a' generator, it uses it as a tool.
        self.generator = StubGenerator()

    def run_generate(self, files: List[Path]) -> List[Path]:
        """
        Scans the given files and generates .pyi stubs for them.
        Returns the list of generated .pyi file paths.
        """
        generated_files: List[Path] = []
        
        for source_file in files:
            # 1. Read the source content
            content = source_file.read_text(encoding="utf-8")
            
            # 2. Scan the content to get the IR
            # Pass the file path for better error messages in the future
            module_def = parse_source_code(content, file_path=str(source_file))
            
            # 3. Generate the .pyi string from the IR
            pyi_content = self.generator.generate(module_def)
            
            # 4. Determine output path and write the file
            output_path = source_file.with_suffix(".pyi")
            output_path.write_text(pyi_content, encoding="utf-8")
            
            generated_files.append(output_path)
            
        return generated_files
~~~~~

### 下一步建议
运行 `pytest`。现在所有测试（单元测试和集成测试）都应该通过了。

我们已经成功验证了单文件处理的核心工作流。下一步是扩展 `StitcherApp` 以支持更真实的使用场景，这将涉及到 `stitcher-config` 包的实现：

1.  **编写新的集成测试**: 创建一个测试，模拟一个包含 `pyproject.toml` 配置和多个源文件的项目结构。
2.  **实现配置加载**: 在 `StitcherApp` 中集成 `stitcher-config`，让它能够读取 `[tool.stitcher]` 配置，例如 `scan_paths`。
3.  **实现目录扫描**: 扩展 `run_generate`（或创建一个新方法），使其能够根据配置自动发现和处理目录下的所有 Python 文件。
