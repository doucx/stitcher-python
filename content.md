好的，我们立即开始实施路线图的第二和第三阶段。我们将首先在 `stitcher-cli` 中构建用户界面的“呈现”部分，然后将它与 `stitcher-application` 的业务逻辑“缝合”在一起，并让应用层通过消息总线进行通信。

## [WIP] feat(cli,app): 实现 CLI 渲染器并连接应用层

### 用户需求
根据 `CLI_and_Messaging_Roadmap.md`，实现一个具体的 `CliRenderer`，修改 CLI 命令以调用 `StitcherApp`，并更新 `StitcherApp` 以使用消息总线报告其操作进度和结果。

### 评论
这是将我们之前构建的所有独立模块整合为一个功能性应用的时刻。通过在 CLI 入口点注入 `CliRenderer`，我们完成了依赖注入的关键一步。`StitcherApp` 现在可以专注于其核心职责，同时通过 `bus` 单例向外部世界广播事件，而完全不知道这些事件最终是如何呈现的。

### 目标
1.  在 `stitcher-cli` 中创建 `rendering.py` 并实现 `CliRenderer`。
2.  重构 `stitcher-cli` 的 `main.py`：
    *   注入 `CliRenderer`。
    *   将 `generate` 命令连接到 `StitcherApp.run_from_config()`。
    *   让 `init` 和 `check` 命令通过 `bus` 报告其“未实现”状态。
3.  修改 `StitcherApp` 以使用 `bus` 报告进度。

### 基本原理
我们遵循“配置-注入-执行”模式。应用的根（`main.py`）负责配置和注入依赖（`Renderer`）。一旦配置完成，应用的其他部分（`StitcherApp`）就可以透明地使用这些依赖（通过 `bus` 单例），而无需知道其具体实现。

### 标签
#intent/build #flow/ready #priority/high
#comp/cli #comp/app #concept/ui #ai/instruct
#task/domain/implementation #task/object/cli-wiring #task/action/implement
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 实现 CLI 渲染器
这是消息总线的“扬声器”，负责将消息意图转换为终端上的彩色文本。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/rendering.py
~~~~~
~~~~~python
import typer
from stitcher.common.messaging import MessageStore, protocols

class CliRenderer(protocols.Renderer):
    """
    Renders messages to the command line using Typer for colored output.
    """
    def __init__(self, store: MessageStore):
        self._store = store

    def render(self, msg_id: str, level: str, **kwargs):
        message = self._store.get(msg_id, **kwargs)
        
        color = None
        if level == "success":
            color = typer.colors.GREEN
        elif level == "warning":
            color = typer.colors.YELLOW
        elif level == "error":
            color = typer.colors.RED
            
        typer.secho(message, fg=color)
~~~~~

#### Acts 2: 添加新的消息模板
我们需要一个消息来报告未实现的功能。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/locales/en/cli.json
~~~~~
~~~~~json.old
{
    "app.run.start": "Stitcher running...",
    "generate.file.success": "✅ Generated stub: {path}",
    "generate.run.complete": "✨ Generation complete. {count} files created.",
    "error.config.not_found": "⚠️  No [tool.stitcher] config found in pyproject.toml. Nothing to do.",
    "error.generic": "❌ An unexpected error occurred: {error}"
}
~~~~~
~~~~~json.new
{
    "app.run.start": "Stitcher running...",
    "generate.file.success": "✅ Generated stub: {path}",
    "generate.run.complete": "✨ Generation complete. {count} files created.",
    "cli.command.not_implemented": "ℹ️  Command '{command}' is not yet implemented.",
    "error.config.not_found": "⚠️  No [tool.stitcher] config found in pyproject.toml. Nothing to do.",
    "error.generic": "❌ An unexpected error occurred: {error}"
}
~~~~~

#### Acts 3: 连接 CLI 与应用层
这是整个流程的“缝合”点。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python
from pathlib import Path
import typer

from stitcher.app import StitcherApp
from stitcher.common import bus
from .rendering import CliRenderer

app = typer.Typer(
    name="stitcher",
    help="Stitcher-Python: Bridging the gap between dynamic code and static analysis.",
    no_args_is_help=True,
)

# --- Dependency Injection at the very start ---
# The CLI is the composition root. It decides *which* renderer to use.
cli_renderer = CliRenderer(store=bus.store)
bus.set_renderer(cli_renderer)
# ---------------------------------------------

@app.command()
def generate():
    """Generate .pyi stubs based on pyproject.toml config."""
    project_root = Path.cwd()
    app_instance = StitcherApp(root_path=project_root)
    app_instance.run_from_config()

@app.command()
def init():
    """Initialize Stitcher in the current project."""
    bus.info("cli.command.not_implemented", command="init")

@app.command()
def check():
    """Verify consistency between code and docs."""
    bus.info("cli.command.not_implemented", command="check")

if __name__ == "__main__":
    app()
~~~~~

#### Acts 4: 在应用层使用消息总线
现在，`StitcherApp` 将通过 `bus` 报告其活动，而不是静默工作。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from stitcher.config import load_config_from_path

class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # The app 'has a' generator, it uses it as a tool.
        self.generator = StubGenerator()

    def run_from_config(self) -> List[Path]:
        """
        Loads config, discovers files, and generates stubs.
        """
        config = load_config_from_path(self.root_path)
        
        if not config.scan_paths:
            # Handle case where config is empty or not found.
            # We could default to scanning the root path, or do nothing.
            # Let's do nothing for now, to be explicit.
            return []
            
        files_to_scan = []
        for scan_path_str in config.scan_paths:
            scan_path = self.root_path / scan_path_str
            if scan_path.is_dir():
                # Recursively find all .py files in the directory
                files_to_scan.extend(scan_path.rglob("*.py"))
            elif scan_path.is_file():
                # If it's a single file, add it
                files_to_scan.append(scan_path)
        
        # Deduplicate in case of overlapping paths
        unique_files = sorted(list(set(files_to_scan)))
        
        # Delegate the actual generation to the already tested method
        return self.run_generate(files=unique_files)

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
~~~~~python.new
from stitcher.common import bus
from stitcher.config import load_config_from_path


class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # The app 'has a' generator, it uses it as a tool.
        self.generator = StubGenerator()

    def run_from_config(self) -> List[Path]:
        """
        Loads config, discovers files, and generates stubs.
        """
        config = load_config_from_path(self.root_path)
        
        if not config.scan_paths:
            bus.warning("error.config.not_found")
            return []
            
        files_to_scan = []
        for scan_path_str in config.scan_paths:
            scan_path = self.root_path / scan_path_str
            if scan_path.is_dir():
                files_to_scan.extend(scan_path.rglob("*.py"))
            elif scan_path.is_file():
                files_to_scan.append(scan_path)
        
        unique_files = sorted(list(set(files_to_scan)))
        
        generated_files = self.run_generate(files=unique_files)
        
        if generated_files:
            bus.success("generate.run.complete", count=len(generated_files))

        return generated_files

    def run_generate(self, files: List[Path]) -> List[Path]:
        """
        Scans the given files and generates .pyi stubs for them.
        Returns the list of generated .pyi file paths.
        """
        generated_files: List[Path] = []
        
        for source_file in files:
            try:
                content = source_file.read_text(encoding="utf-8")
                module_def = parse_source_code(content, file_path=str(source_file))
                pyi_content = self.generator.generate(module_def)
                
                output_path = source_file.with_suffix(".pyi")
                output_path.write_text(pyi_content, encoding="utf-8")
                
                bus.success("generate.file.success", path=output_path.relative_to(self.root_path))
                generated_files.append(output_path)
            except Exception as e:
                bus.error("error.generic", error=e)

        return generated_files
~~~~~

### 下一步建议
我们已经完成了一个功能完备、架构清晰的 CLI 工具。现在，我们应该遵循路线图的第四阶段：**更新测试以验证意图**。

我建议修改 `test_end_to_end.py`：
1.  使用 `monkeypatch` 来 Mock 全局 `bus` 对象。
2.  将测试断言从 `assert file.exists()` 和 `file.read_text()` 更改为 `mock_bus.success.assert_called_with(...)`。

这将使我们的测试更健壮、更专注于业务逻辑，而不再依赖于文件系统的具体实现。
