好的，我已经完成了对当前文件树中所有 `pyproject.toml` 文件的审计。

根据分析，在文件移动（特别是将代码拆分为多个包）后，`stitcher-test-utils` 的依赖声明最为滞后。它在代码中直接引用了 `stitcher.common`、`stitcher.spec` 和 `stitcher.index` 的内容，但在 `pyproject.toml` 中缺少相应的显式依赖或 UV 源码映射。

以下是更新依赖关系的计划：

## [WIP] refactor: 更新 stitcher-test-utils 的依赖关系以匹配实际引用

### 用户需求
由于文件已移动并拆分为多个 monorepo 包，需要更新各包的 `pyproject.toml` 配置文件，确保内部依赖关系（Internal Dependencies）和 UV 源码映射（Workspace Sources）正确无误。

### 评论
在 UV 驱动的 Monorepo 架构中，显式声明每个包的直接依赖是保证构建可靠性和开发体验（如 IDE 跳转）的关键。当前 `stitcher-test-utils` 遗漏了几个核心包的关联。

### 目标
1.  修正 `packages/stitcher-test-utils/pyproject.toml` 中的依赖项。
2.  补齐 `stitcher-test-utils` 中缺失的 `[tool.uv.sources]` 映射。
3.  确保 `stitcher-application` 等其他包的依赖链条完整。

### 基本原理
我们将对 `stitcher-test-utils` 进行补丁：
*   添加 `stitcher-common`：因为它在 `bus.py` 中被引用。
*   添加 `stitcher-spec`：因为它在 `helpers.py` 中被引用（如 `InteractionHandler`）。
*   添加 `stitcher-index` 的源码映射：它已在 `dependencies` 中但漏掉了 `sources` 定义。

### 标签
#intent/refine #flow/ready #comp/test #comp/build #concept/config #scope/dx #ai/instruct #task/domain/build #task/object/pyproject-dependencies #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 更新 `stitcher-test-utils` 的依赖配置

我们将补全 `stitcher-test-utils` 的 `pyproject.toml`，使其包含所有实际引用的内部包。

~~~~~act
patch_file
packages/stitcher-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyneedle",
    "PyYAML",
    "tomli-w",
    "stitcher-application",
    "stitcher-python-adapter",
    "stitcher-index",
    "stitcher-workspace",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
pyneedle = { workspace = true }
stitcher-application = { workspace = true }
stitcher-python-adapter = { workspace = true }
stitcher-workspace = { workspace = true }
~~~~~
~~~~~toml.new
dependencies = [
    "pyneedle",
    "PyYAML",
    "tomli-w",
    "stitcher-application",
    "stitcher-python-adapter",
    "stitcher-index",
    "stitcher-workspace",
    "stitcher-common",
    "stitcher-spec",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
pyneedle = { workspace = true }
stitcher-application = { workspace = true }
stitcher-python-adapter = { workspace = true }
stitcher-workspace = { workspace = true }
stitcher-index = { workspace = true }
stitcher-common = { workspace = true }
stitcher-spec = { workspace = true }
~~~~~

### 下一步建议

- **同步环境**: 执行 `uv sync` 以应用新的依赖关系，并确保虚拟环境中的链接已更新。
- **验证测试**: 运行 `pytest` 确保 `test-utils` 能够正确加载所有依赖包。
- **缺失包检查**: 我注意到 `stitcher-application` 依赖 `stitcher-python-adapter` 和 `stitcher-stubgen`，但这些目录目前未出现在我的文件列表快照中。如果您已经移动了它们，请确保它们也包含了类似的 `pyproject.toml` 结构。
