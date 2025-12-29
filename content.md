## [WIP] fix(stubs): 修正 needle-stubs 包内部命名空间

### 用户需求
让 `pyright` 能够正确识别并使用 `needle-stubs` 包，解决当前遇到的 `missing-import` 错误。

### 评论
这是一个关键的修复。存根包的价值完全取决于类型检查器能否自动发现并正确映射它。当前的目录结构与运行时包的导入路径不匹配，导致整个存根包无效。这个修复将使其恢复功能。

### 目标
1.  将存根包内部的顶层目录从 `needle-stubs` 重命名为 `needle`，以匹配运行时的导入路径。
2.  更新 `needle-stubs` 的 `pyproject.toml` 文件，确保构建系统打包正确的目录。

### 基本原理
PEP 561 规定，一个名为 `foo-stubs` 的存根包，其内部结构必须镜像 `foo` 包。当 `pyright` 看到 `import foo.bar` 时，它会在 `foo-stubs` 包里寻找 `foo/bar.pyi`。我们当前的结构是 `foo-stubs/foo-stubs/bar.pyi`，这是不正确的。通过重命名目录并更新构建配置，我们使存根包的物理结构与 `needle` 包的逻辑导入路径保持一致，从而允许 `pyright` 等工具进行自动映射和解析。

### 标签
#intent/fix #flow/ready #priority/high #comp/build #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/stub-resolution #task/action/bug-fix #task/state/begin

---
### Script

#### Acts 1: 修正存根包的目录结构和构建配置

首先，我们将 `src` 目录下的 `needle-stubs` 文件夹重命名为 `needle`。

~~~~~act
move_file
packages/needle-stubs/src/needle-stubs
packages/needle-stubs/src/needle
~~~~~

接着，更新 `pyproject.toml` 文件，将 `packages` 指令从指向旧目录名改为指向新的 `needle` 目录。

~~~~~act
patch_file
packages/needle-stubs/pyproject.toml
~~~~~
~~~~~toml.old
[tool.hatch.build.targets.wheel]
packages = [
    "src/needle-stubs",
]
~~~~~
~~~~~toml.new
[tool.hatch.build.targets.wheel]
packages = [
    "src/needle",
]
~~~~~

### 下一步建议
在应用此计划后，你的静态分析工具应该能够立即找到 `needle.pointer` 的导入。你可以通过我之前描述的 "Go to Definition" 或引入故意类型错误的方法来验证 `pyright` 是否已经正确地使用了存根文件。
