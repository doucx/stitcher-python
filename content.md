简洁回答
`pyrightconfig.json` 文件包含过时且错误的路径配置（引用了不存在的 `stitcher-needle`），这与 `pyproject.toml` 中的正确配置冲突，导致静态分析工具无法正确解析项目结构。

## [WIP] fix: 删除过时且冲突的 pyrightconfig.json 配置文件

### 错误分析
用户遇到了 `pyrefly check` 产生的大量 `missing-import` 错误。
虽然 `pyrefly` 声称从 `pyproject.toml` 加载配置，但项目根目录下存在一个 `pyrightconfig.json` 文件。
1.  **路径错误**: `pyrightconfig.json` 中的 `extraPaths` 包含 `packages/stitcher-needle/src`，该目录在文件系统中**不存在**（正确的应该是 `packages/pyneedle/src` 等）。
2.  **配置冲突**: Pyright/Pyrefly 通常优先读取或受根目录下的 `pyrightconfig.json` 影响。该文件的存在干扰了 `pyproject.toml` 中正确路径的加载，导致无法解析 `needle.pointer` 等模块。
3.  **冗余**: `pyproject.toml` 已经包含了完整且正确的 `[tool.pyright]` 配置。

### 用户需求
修复 `pyrefly check` 报错，确保开发环境的静态分析工具能正确解析 monorepo 中的 Python 包路径。

### 评论
这是一个典型的配置漂移问题。删除过时的配置文件将强制工具使用 `pyproject.toml` 中的单一事实来源 (Single Source of Truth)。

### 目标
- 删除 `pyrightconfig.json`。
- 恢复静态分析工具的正常解析能力。

### 基本原理
`pyproject.toml` 中的 `tool.pyright.extraPaths` 已经正确列出了所有子包的 `src` 目录。删除错误的 `pyrightconfig.json` 可以消除歧义，使工具回退到正确的配置上。

### 标签
#intent/fix #flow/ready #priority/high
#comp/build #concept/config #scope/dx
#ai/instruct
#task/domain/testing #task/object/static-analysis #task/action/fix-config
#task/state/begin #task/status/active

---

### Script

#### Acts 1: 删除配置文件
删除根目录下的过时配置文件。

~~~~~act
delete_file
pyrightconfig.json
~~~~~

### 下一步建议
执行完此计划后，请再次运行 `pyrefly check`。
如果错误仍然存在，那可能是因为 `packages/pyneedle/src/needle/__init__.py` 的存在使 `needle` 被 Pyright 识别为普通包而非命名空间包，从而屏蔽了其他路径下的 `needle.*` 子包。如果是这种情况，我们可能需要调整包结构（例如移除顶层 `__init__.py` 或调整 `extraPaths` 顺序），但首先必须排除配置文件的干扰。
