Excellent. This is a perfect real-world test case for the new refactoring engine. The goal is to move the JSON files that define the `L.cli.*` pointers into a new `commands` subdirectory, and trust the engine to automatically update all Python code that references them.

I will now create the necessary Stitcher Migration Pack (SMP) script.

## [WIP] feat: Create SMP script to refactor L.cli pointers

### 用户需求

用户希望重构 `L` 对象的结构，将所有 `cli.*` 相关的语言资源指针移动到 `cli.commands.*` 下。这要求将 `packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/` 目录下的 JSON 文件移动到新的 `.../cli/commands/` 子目录中，并自动更新所有 Python 代码中对这些指针的引用。

### 评论

这是一个极佳的“吃自己的狗粮”(Dogfooding) 的实践。它不仅能提升项目结构清晰度，还能有效验证 `stitcher-refactor` 引擎的核心能力：处理文件系统操作（移动文件）并自动重构代码库中所有相关的符号引用，特别是对于 `L` 对象这种动态结构。

### 目标

1.  创建 `migrations` 目录（如果尚不存在）。
2.  在该目录中创建一个名为 `001_refactor_cli_l_pointers.py` 的迁移脚本。
3.  脚本将包含将 `cli/*.json` 文件移动到 `cli/commands/*.json` 的逻辑。

### 基本原理

我将使用 `stitcher.refactor.migration.Move` 操作。根据 `stitcher-refactor` 的设计，`MoveFileOperation` 足够智能，能够：
1.  根据文件的移动（从 `cli/` 到 `cli/commands/`），计算出 `L` 对象指针对应的 FQN 变更（从 `L.cli.*` 到 `L.cli.commands.*`）。
2.  自动触发一个隐式的 `RenameSymbolOperation`，查找并更新代码库中所有对旧 FQN 的引用。

这种方法将文件系统的变更作为“单一事实来源”，并让引擎自动处理代码层面的同步，是实现此重构任务最直接和最健壮的方式。

### 标签

#intent/build #flow/ready #priority/high #comp/cli #comp/common #concept/state #scope/dx #ai/instruct #task/domain/tooling #task/object/refactor-engine #task/action/dogfooding #task/state/begin

---

### Script

#### Acts 1: 创建迁移脚本目录和文件

首先，确保 `migrations` 目录存在，然后创建我们的迁移脚本。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p migrations
~~~~~

~~~~~act
write_file
migrations/001_refactor_cli_l_pointers.py
~~~~~
~~~~~python
from pathlib import Path
from stitcher.refactor.migration import MigrationSpec, Move


def upgrade(spec: MigrationSpec):
    """
    Refactors L.cli.* pointers to L.cli.commands.*.

    This is achieved by moving the underlying JSON asset files. The
    Stitcher refactor engine will automatically update all Python code
    references.
    """
    base_path = Path("packages/stitcher-common/src/stitcher/common/assets/needle/en/cli")
    target_dir = base_path / "commands"

    # List of files to move.
    files_to_move = ["app.json", "command.json", "option.json"]

    for filename in files_to_move:
        src_path = base_path / filename
        dest_path = target_dir / filename

        spec.add(Move(src=src_path, dest=dest_path))
~~~~~

### 下一步建议

脚本已创建。现在，请你手动执行以下命令来应用这个重构：

```bash
stitcher refactor apply migrations/001_refactor_cli_l_pointers.py
```

执行后，请检查以下几点以验证结果：
1.  `packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/` 目录下的 JSON 文件是否已移动到 `commands` 子目录中。
2.  `packages/stitcher-cli/src/stitcher/cli/` 下的 Python 文件中，类似 `L.cli.option.*` 的引用是否已自动更新为 `L.cli.commands.option.*`。
