简要回答：
你的观察非常准确，LSP (Pylance/Pyright) 确实没有“连接”到所有包。

**根本原因**：
根据你提供的 LSP 日志：
`Registering workspace: .../packages/stitcher-application`
`WARN LSP client does not support dynamic capability registration`

**lvim (LunarVim) 错误地将子目录 `stitcher-application` 识别为了项目根目录**，而不是整个 Monorepo 的根目录。因此，它只读取了子目录的配置，完全忽略了我们在根目录 `pyproject.toml` 中配置的 `extraPaths`（那些路径才是连接所有包的“桥梁”）。

**解决方案**：
1.  **强制配置 LSP**: 我们将在根目录创建一个 `pyrightconfig.json`。相比 `pyproject.toml`，这是 Pyright 的原生配置文件，通常具有更高的被发现优先级，且支持从子目录向上查找。
2.  **清理残留的命名空间污染**: 虽然我们删除了部分 `__init__.py`，但我将执行一次全扫描，确保没有任何一个 `src/stitcher/__init__.py` 幸存。
3.  **添加 `py.typed` 标记**: 这是一个标准做法，明确告知工具这些包包含类型信息。

## [WIP] fix: 添加 pyrightconfig.json 并清理所有命名空间残留

### 用户需求
用户在使用 lvim 时遇到 Pylance 无法解析跨包引用的问题，且日志显示 LSP 工作区根目录被错误识别为子包。用户希望修复此“断连”状态。

### 评论
这是一个常见的 Monorepo 开发环境问题。IDE 往往根据打开的文件或最近的 `pyproject.toml` 猜测根目录。通过提供明确的 `pyrightconfig.json`，我们不仅为 lvim 提供了指引，也为所有使用 VSCode/Pyright 的贡献者标准化了开发环境。

### 目标
1.  创建 `pyrightconfig.json`，内容与 `pyproject.toml` 中的 `tool.pyright` 一致。
2.  使用 `run_command` 彻底查找并删除任何残留的 `src/stitcher/__init__.py`（针对所有包）。
3.  在所有子包中创建 `py.typed` 文件，增强类型检查器的识别能力。

### 基本原理
-   **`pyrightconfig.json`**: 当编辑器在子目录启动 Pyright 时，Pyright 会尝试向上遍历目录查找此文件作为配置根。这能有效解决 lvim 根目录识别错误的问题。
-   **`py.typed`**: PEP 561 规定的标记文件，表明该包支持类型提示。这对于我们生成的 `.pyi` 文件生效至关重要。

### 标签
#intent/fix #flow/ready #priority/high #comp/build #scope/dx
#task/domain/config #task/object/pyright #task/action/configure
#task/state/continue

---

### Script

#### Acts 1: 创建 pyrightconfig.json

这将作为 LSP 的权威配置。

~~~~~act
write_file
pyrightconfig.json
~~~~~
~~~~~json
{
  "include": ["packages", "tests"],
  "exclude": ["**/node_modules", "**/__pycache__", "**/.git"],
  "extraPaths": [
    "packages/stitcher-spec/src",
    "packages/stitcher-common/src",
    "packages/stitcher-scanner/src",
    "packages/stitcher-io/src",
    "packages/stitcher-config/src",
    "packages/stitcher-application/src",
    "packages/stitcher-cli/src",
    "packages/stitcher-needle/src",
    "packages/stitcher-test-utils/src"
  ],
  "reportMissingImports": true,
  "reportMissingTypeStubs": false
}
~~~~~

#### Acts 2: 彻底清除命名空间污染

我们使用 `find` 命令来查找并删除任何 `packages/*/src/stitcher/__init__.py`。注意，我们**不**删除 `stitcher/app/__init__.py` 这种子包的 init，只删除 `stitcher` 这一层的。

~~~~~act
run_command
~~~~~
~~~~~
find packages -path "*/src/stitcher/__init__.py" -delete
~~~~~

同时删除对应的 `__init__.pyi`，以防万一。

~~~~~act
run_command
~~~~~
~~~~~
find packages -path "*/src/stitcher/__init__.pyi" -delete
~~~~~

#### Acts 3: 添加 py.typed 标记

为所有包添加 `py.typed` 标记。

~~~~~act
run_command
~~~~~
~~~~~
touch packages/stitcher-spec/src/stitcher/spec/py.typed
touch packages/stitcher-common/src/stitcher/common/py.typed
touch packages/stitcher-scanner/src/stitcher/scanner/py.typed
touch packages/stitcher-io/src/stitcher/io/py.typed
touch packages/stitcher-config/src/stitcher/config/py.typed
touch packages/stitcher-application/src/stitcher/app/py.typed
touch packages/stitcher-cli/src/stitcher/cli/py.typed
touch packages/stitcher-needle/src/stitcher/needle/py.typed
touch packages/stitcher-test-utils/src/stitcher/test_utils/py.typed
~~~~~

### 下一步建议
1.  **重启 lvim**: 新的 `pyrightconfig.json` 需要重启 LSP 服务器才能生效。
2.  **检查**: 打开 `core.py`，如果一切正常，Pylance 应该能通过 `extraPaths` 找到 `stitcher.scanner` 等模块，红线应消失。
3.  **Dogfooding**: 如果环境修复，你可以继续提交这些配置变更，并推进路线图。
