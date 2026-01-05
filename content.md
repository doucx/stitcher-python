你说的完全正确！`stitcher refactor apply` 命令的帮助文本确实缺失了。这是因为在 Typer 中，子命令的帮助文本也需要显式地通过 `help` 参数传入。

我将立即生成一个计划来修复这个问题，为 `refactor apply` 命令添加正确的帮助文本。

## [WIP] fix: 为 `refactor apply` 命令添加缺失的帮助文本

### 错误分析

`stitcher refactor` 命令下的 `apply` 子命令缺少帮助文本。在 `packages/stitcher-cli/src/stitcher/cli/main.py` 中注册 `apply` 命令时，`typer.Typer.command()` 装饰器没有提供 `help` 参数，导致 `stitcher refactor --help` 输出中 `apply` 命令没有描述。

### 用户需求

为 `stitcher refactor apply` 命令添加描述性的帮助文本，使其在 CLI 中能够正确显示。

### 评论

这是一个小的用户体验问题，但对于提高 CLI 的可发现性和可用性至关重要。统一所有 CLI 命令的帮助文本是 `L` 指针迁移目标的一部分。

### 目标

1.  在 `needle` 的 JSON 资源文件中为 `refactor apply` 命令创建对应的 `L` 指针。
2.  修改 `packages/stitcher-cli/src/stitcher/cli/main.py` 文件，为 `refactor_app.command(name="apply")` 添加 `help` 参数，并引用新的 `L` 指针。

### 基本原理

我将在 `L.cli.command` 下添加一个新的 `refactor_apply` 键，用于存储该命令的帮助文本。然后，我将通过 `patch_file` 操作修改 `main.py`，将该 `L` 指针集成到 Typer 命令的定义中。

### 标签

#intent/fix #flow/ready #priority/low #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/cli #task/object/help-text #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 扩展 Needle 资源文件以包含 `refactor apply` 的帮助文本

我将更新 `command.json` 文件，添加 `refactor_apply` 命令的帮助文本。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/command.json
~~~~~
~~~~~json.old
{
  "check": {
    "help": "Verify consistency between code and docs."
  },
  "generate": {
    "help": "Generate .pyi stubs based on pyproject.toml config."
  },
  "init": {
    "help": "Initialize Stitcher in the current project."
  },
  "inject": {
    "help": "Inject docstrings from .stitcher.yaml files back into code."
  },
  "pump": {
    "help": "Extract new docstrings from source code and merge them into .stitcher.yaml."
  },
  "strip": {
    "help": "Remove docstrings from source files."
  },
  "refactor": {
    "help": "Apply automated refactorings."
  },
  "not_implemented": "ℹ️  Command '{command}' is not yet implemented."
}
~~~~~
~~~~~json.new
{
  "check": {
    "help": "Verify consistency between code and docs."
  },
  "generate": {
    "help": "Generate .pyi stubs based on pyproject.toml config."
  },
  "init": {
    "help": "Initialize Stitcher in the current project."
  },
  "inject": {
    "help": "Inject docstrings from .stitcher.yaml files back into code."
  },
  "pump": {
    "help": "Extract new docstrings from source code and merge them into .stitcher.yaml."
  },
  "strip": {
    "help": "Remove docstrings from source files."
  },
  "refactor": {
    "help": "Apply automated refactorings."
  },
  "refactor_apply": {
    "help": "Apply automated refactorings from a migration script."
  },
  "not_implemented": "ℹ️  Command '{command}' is not yet implemented."
}
~~~~~

接下来是中文版。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/cli/command.json
~~~~~
~~~~~json.old
{
  "check": {
    "help": "验证代码结构与文档的一致性。"
  },
  "generate": {
    "help": "根据 pyproject.toml 配置生成 .pyi 存根文件。"
  },
  "init": {
    "help": "在当前项目中初始化 Stitcher。"
  },
  "inject": {
    "help": "将 .stitcher.yaml 中的文档重新注入源代码。"
  },
  "pump": {
    "help": "从源代码提取新文档并合并至 .stitcher.yaml。"
  },
  "strip": {
    "help": "从源代码中移除文档字符串。"
  },
  "refactor": {
    "help": "应用自动化代码重构。"
  },
  "not_implemented": "ℹ️  命令 '{command}' 尚未实现。"
}
~~~~~
~~~~~json.new
{
  "check": {
    "help": "验证代码结构与文档的一致性。"
  },
  "generate": {
    "help": "根据 pyproject.toml 配置生成 .pyi 存根文件。"
  },
  "init": {
    "help": "在当前项目中初始化 Stitcher。"
  },
  "inject": {
    "help": "将 .stitcher.yaml 中的文档重新注入源代码。"
  },
  "pump": {
    "help": "从源代码提取新文档并合并至 .stitcher.yaml。"
  },
  "strip": {
    "help": "从源代码中移除文档字符串。"
  },
  "refactor": {
    "help": "应用自动化代码重构。"
  },
  "refactor_apply": {
    "help": "从迁移脚本应用自动化代码重构。"
  },
  "not_implemented": "ℹ️  命令 '{command}' 尚未实现。"
}
~~~~~

#### Acts 2: 更新 `main.py` 以引用 `refactor apply` 的帮助文本

我将修改 `packages/stitcher-cli/src/stitcher/cli/main.py` 文件，为 `refactor_app.command(name="apply")` 添加 `help` 参数。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python.old
refactor_app = typer.Typer(
    name="refactor", help=nexus(L.cli.command.refactor.help), no_args_is_help=True
)
refactor_app.command(name="apply")(refactor_command)
app.add_typer(refactor_app)
~~~~~
~~~~~python.new
refactor_app = typer.Typer(
    name="refactor", help=nexus(L.cli.command.refactor.help), no_args_is_help=True
)
refactor_app.command(name="apply", help=nexus(L.cli.command.refactor_apply.help))(refactor_command)
app.add_typer(refactor_app)
~~~~~

### 下一步建议

建议运行 `stitcher refactor --help` 确认 `apply` 命令现在正确显示其帮助文本。
