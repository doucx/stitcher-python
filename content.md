简要回答：
飘红的原因是 **IDE (VSCode/Pylance) 尚未理解 Monorepo 的目录结构**。虽然 `uv pip install -e` 在 Python 运行时层面打通了路径，但静态分析工具（如 Pylance）通常需要显式的配置才能正确解析分散在多个 `packages/*/src` 目录下的 Namespace Package (`stitcher.*`)。

既然 IDE 找不到源文件路径，它自然也找不到我们刚刚生成在源文件旁边的 `.pyi` 存根文件。解决这个问题的“最后一公里”就是配置 `pyproject.toml` 中的 `[tool.pyright]`，显式告知 IDE 源码在哪里。这也正是 **Dogfooding 计划任务 2.2** 的核心内容。

此外，关于 `typer[all]` 的警告，这是因为在该版本中可能不包含此 extra 标识，我们将修正为直接依赖 `typer`。

## [WIP] chore: 配置 IDE 路径解析并忽略构建产物

### 用户需求
1.  解决 IDE 中的 "unresolved import" 错误，确保 Pylance 能正确识别 `stitcher-python` 的 Monorepo 结构和生成的 `.pyi` 存根。
2.  执行 Dogfooding 计划任务 2.2：配置 `.gitignore` 以忽略生成的 `.pyi` 文件（但保留 `.stitcher.yaml`）。
3.  修复安装时的 `typer[all]` 警告。

### 评论
这是 Dogfooding 闭环的关键一步。生成存根只是第一步，**配置环境以消费存根**才是实现 DX 提升的关键。通过配置 `extraPaths`，我们手动完成了未来 `stitcher` 可能需要自动化完成的工作——让 IDE “看见”复杂的项目结构。

### 目标
1.  在根目录 `.gitignore` 中添加 `**/*.pyi`，防止构建产物污染仓库。
2.  在根目录 `pyproject.toml` 中添加 `[tool.pyright]` 配置，显式列出所有子包的 `src` 路径。
3.  修正 `packages/stitcher-cli/pyproject.toml` 中的依赖声明。

### 基本原理
-   **`.gitignore`**: `.pyi` 是由 `stitcher generate` 动态生成的构建产物，类似于 `.pyc` 或编译后的二进制文件，不应纳入版本控制。
-   **`tool.pyright.extraPaths`**: 这是 Pylance/Pyright 的标准配置项。在 Namespace Package 结构中，显式列出每个包的根目录（`packages/xxx/src`）能强制 IDE 将它们视为一级模块搜索路径，从而解决跨包引用的解析问题。

### 标签
#intent/tooling #flow/ready #priority/high #comp/build #scope/dx #human/lead
#task/domain/config #task/object/pyright #task/action/configure
#task/state/continue

---

### Script

#### Acts 1: 更新 .gitignore

我们忽略所有的 `.pyi` 文件，以及由 `stitcher` 可能生成的签名缓存目录。

~~~~~act
patch_file
.gitignore
~~~~~
~~~~~old
__pycache__/
*.py[codz]
*$py.class
~~~~~
~~~~~new
__pycache__/
*.py[codz]
*$py.class

# Stitcher generated artifacts
**/*.pyi
.stitcher/signatures/
~~~~~

#### Acts 2: 配置 Pyright (解决飘红)

在根目录 `pyproject.toml` 中添加 `tool.pyright` 配置。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~old
[tool.stitcher]
scan_paths = ["packages"]
~~~~~
~~~~~new
[tool.stitcher]
scan_paths = ["packages"]

[tool.pyright]
include = ["packages", "tests"]
# 显式告知 IDE 所有子包的源码位置，解决 Monorepo 解析问题
extraPaths = [
    "packages/stitcher-spec/src",
    "packages/stitcher-common/src",
    "packages/stitcher-scanner/src",
    "packages/stitcher-io/src",
    "packages/stitcher-config/src",
    "packages/stitcher-application/src",
    "packages/stitcher-cli/src",
    "packages/stitcher-needle/src",
    "packages/stitcher-test-utils/src",
]
~~~~~

#### Acts 3: 修正 Typer 依赖

修正 `stitcher-cli` 的依赖警告。

~~~~~act
patch_file
packages/stitcher-cli/pyproject.toml
~~~~~
~~~~~old
dependencies = [
    "stitcher-application",
    "stitcher-needle",
    "typer[all]",
]
~~~~~
~~~~~new
dependencies = [
    "stitcher-application",
    "stitcher-needle",
    "typer",
]
~~~~~

### 下一步建议
1.  **重启 IDE**: 修改 `pyproject.toml` 后，通常需要重启 VSCode 或执行 `Developer: Reload Window` 才能让 Pylance 加载新的配置。
2.  **验证**: 重启后，再次打开 `core.py`，红色的波浪线应该会消失。此外，尝试按住 Ctrl 点击某个函数名（如 `StubGenerator`），应该能跳转到刚刚生成的 `.pyi` 文件（如果 IDE 优先索引 Stub）或源码。
3.  **提交文档**: 既然 `.pyi` 已被忽略，你可以安全地执行 `git add .` 来提交新生成的 `.stitcher.yaml` 文档文件（Dogfooding 任务 1.2）。
