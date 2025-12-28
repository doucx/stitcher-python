好的，测试通过了。现在我来处理 `stitcher-cli` 中由于代码重构导致的悬空文档（`Extra Doc`）错误。

这个问题的根源在于，我们将命令的实现从 `main.py` 移到了 `commands/` 子目录中，但它们的文档字符串定义仍然留在 `main.stitcher.yaml` 文件里。

我将把这些文档定义移动到它们各自实现文件对应的 YAML 中，并清理旧的 `main.stitcher.yaml`。

## [WIP] fix: 修正 CLI 命令重构后的悬空文档

### 错误分析
`stitcher check` 报告 `main.py` 存在多个 `Extra Doc` 错误。这是因为命令的实现函数（如 `check_command`）已从 `main.py` 移至 `commands` 子模块中，但其文档字符串仍然定义在 `main.stitcher.yaml` 中，导致这些文档键在 `main.py` 的作用域内无法找到对应的代码实体。

### 用户需求
将悬空的文档定义迁移到其对应的新位置，以解决 `check` 命令报告的错误。

### 评论
这是一个常规的代码维护任务，确保代码与文档的物理位置保持同步。通过迁移这些文档，我们能继续保证 `stitcher` 项目自身的文档完整性和准确性。

### 目标
1.  为 `commands/basics.py`, `commands/check.py`, 和 `commands/pump.py` 创建新的 `.stitcher.yaml` 文件。
2.  将 `main.stitcher.yaml` 中与命令相关的文档定义，剪切并粘贴到对应的新 YAML 文件中，并更新键名以匹配实际的函数名（例如 `check` -> `check_command`）。
3.  清理 `main.stitcher.yaml`，只保留与 `main.py` 中剩余代码实体相关的文档。

### 基本原理
使用 `write_file` 创建新的文档文件，并使用 `patch_file` 清理旧的文档文件。这是对项目文档结构的直接、原子化的重构。

### 标签
#intent/fix #flow/ready #priority/medium #comp/cli #comp/docs #scope/dx #ai/instruct #task/domain/documentation #task/object/docstrings #task/action/refactor

---

### Script

#### Acts 1: 为 commands/basics.py 创建文档文件

将 `generate`, `init`, `strip`, 和 `inject` 命令的文档移至 `basics.stitcher.yaml`，并更新键名。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/commands/basics.stitcher.yaml
~~~~~
~~~~~yaml
"generate_command": |-
  Generate .pyi stubs based on pyproject.toml config.
"init_command": |-
  Initialize Stitcher in the current project.
"inject_command": |-
  Inject docstrings from .stitcher.yaml files back into code.
"strip_command": |-
  Remove docstrings from source files.
~~~~~

#### Acts 2: 为 commands/check.py 创建文档文件

迁移 `check` 命令的文档。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/commands/check.stitcher.yaml
~~~~~
~~~~~yaml
"check_command": |-
  Verify consistency between code and docs.

  Args:
    force_relink: [Non-interactive] For 'Signature Drift' errors, forces relinking.
    reconcile: [Non-interactive] For 'Co-evolution' errors, accepts both changes.
    non_interactive: Force non-interactive mode, failing on unresolved conflicts.
~~~~~

#### Acts 3: 为 commands/pump.py 创建文档文件

迁移 `pump` 命令的文档。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/commands/pump.stitcher.yaml
~~~~~
~~~~~yaml
"pump_command": |-
  Extract new docstrings from source code and merge them into .stitcher.yaml.

  Args:
    strip: If True, remove docstrings from source after successful pumping.
    force: If True, overwrite YAML with source docstrings on conflict.
    reconcile: If True, keep YAML docstrings on conflict.
    non_interactive: Force non-interactive mode, failing on unresolved conflicts.
~~~~~

#### Acts 4: 清理旧的 main.stitcher.yaml

移除所有已迁移的悬空文档定义。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.stitcher.yaml
~~~~~
~~~~~yaml.old
"app": |-
  The main Typer application instance for the CLI.
"check": |-
  Verify consistency between code and docs.

  Args:
    force_relink: [Non-interactive] For 'Signature Drift' errors, forces relinking.
    reconcile: [Non-interactive] For 'Co-evolution' errors, accepts both changes.
    non_interactive: Force non-interactive mode, failing on unresolved conflicts.
"generate": |-
  Generate .pyi stubs based on pyproject.toml config.
"init": |-
  Initialize Stitcher in the current project.
"inject": |-
  Inject docstrings from .stitcher.yaml files back into code.
"main": |-
  Stitcher CLI entry point.
"pump": |-
  Extract new docstrings from source code and merge them into .stitcher.yaml.

  Args:
    strip: If True, remove docstrings from source after successful pumping.
    force: If True, overwrite YAML with source docstrings on conflict.
    reconcile: If True, keep YAML docstrings on conflict.
    non_interactive: Force non-interactive mode, failing on unresolved conflicts.
"strip": |-
  Remove docstrings from source files.
~~~~~
~~~~~yaml.new
"app": |-
  The main Typer application instance for the CLI.
"main": |-
  Stitcher CLI entry point.
~~~~~
