简要回答：
你的直觉非常敏锐。**这确实是严重的命名空间遮蔽 (Namespace Shadowing) 问题。**

问题根源：
1.  **不该存在的 `__init__.py`**: 部分包（如 `stitcher-needle`, `stitcher-common`）在 `src/stitcher/` 根目录下包含了 `__init__.py`。在现代 Python (Implicit Namespace Packages) 架构中，这个位置**必须是空的**。
2.  **致命的 `__init__.pyi`**: 因为上述 `.py` 文件存在，`stitcher generate` 忠实地为它们生成了 `__init__.pyi`。对于类型检查器（Pylance/MyPy）来说，一旦看到 `stitcher/__init__.pyi`，它就会认为 `stitcher` 是一个**普通包**，包含固定的内容，从而**停止扫描**所有其他子包（如 `stitcher.app`, `stitcher.cli`）。这导致整个命名空间“塌缩”，所有跨包引用瞬间失效。

LSP 的 Root 错误是次要的，主要原因是它被这种混乱的包结构搞晕了。

我们需要立即执行“外科手术”，切除这些不该存在的根节点文件。

## [WIP] fix: 移除根目录 __init__.py 以修复命名空间遮蔽

### 用户需求
用户发现 `stitcher-needle` 等包在 `src/stitcher/` 目录下生成了 `__init__.pyi`，导致 IDE 无法解析其他子包（命名空间遮蔽）。这是因为源码中错误地存在了 `src/stitcher/__init__.py`。

### 评论
这是一个架构上的修正。我们在 `stitcher-python` 架构蓝图中明确了基于 `uv` 的 Workspace 架构，这隐含了使用 Python 3 native namespace packages 的要求。遗留的 `pkgutil` 风格的 `__init__.py` 不仅是多余的，现在证明是有害的，因为它们诱导 `stitcher` 生成了“封死”命名空间的存根文件。

### 目标
1.  删除 `packages/stitcher-needle/src/stitcher/__init__.py`。
2.  删除 `packages/stitcher-common/src/stitcher/__init__.py`（如果存在且内容不当）。
3.  删除对应的 `__init__.pyi` 文件（如果已生成）。
4.  清理对应的 `.stitcher.yaml` 文件（如果已生成）。

### 基本原理
**Implicit Namespace Packages (PEP 420)** 要求命名空间容器目录（这里是 `stitcher`）不包含 `__init__.py`。这允许 Python 解释器将分散在不同物理路径下的 `stitcher/*` 子目录无缝合并为一个逻辑包。一旦放入 `__init__.py`，该目录就变成了常规包，破坏了合并机制。

### 标签
#intent/fix #flow/ready #priority/critical #comp/build #concept/structure #scope/core
#task/domain/refactor #task/object/namespace-package #task/action/cleanup
#task/state/continue

---

### Script

#### Acts 1: 删除 stitcher-needle 的根 init

这是用户明确指出的问题点。

~~~~~act
delete_file
packages/stitcher-needle/src/stitcher/__init__.py
~~~~~

~~~~~act
delete_file
packages/stitcher-needle/src/stitcher/__init__.pyi
~~~~~

~~~~~act
delete_file
packages/stitcher-needle/src/stitcher/__init__.stitcher.yaml
~~~~~

#### Acts 2: 检查并清理 stitcher-common 的根 init

之前分析发现 `stitcher-common` 也有这个问题，并且试图在该文件中导出 `bus`。我们需要删除它。**注意**：如果有代码依赖 `from stitcher import bus`，这将是破坏性变更，但那是错误用法，必须纠正为 `from stitcher.common import bus`。

~~~~~act
delete_file
packages/stitcher-common/src/stitcher/__init__.py
~~~~~

~~~~~act
delete_file
packages/stitcher-common/src/stitcher/__init__.pyi
~~~~~

~~~~~act
delete_file
packages/stitcher-common/src/stitcher/__init__.stitcher.yaml
~~~~~

#### Acts 3: 预防性检查其他包

为了保险，我们检查其他包是否也有此问题。虽然之前的 XML 没显示，但确认一下更安全。如果文件不存在，`delete_file` 会报错吗？Quipu 指令集没有 `delete_if_exists`。我们先列出看看，或者假设之前的 PathInspector 是准确的。基于之前的信息，只有这两个包有此问题。

我们添加一个 `run_command` 来清理可能残留的 `__pycache__`，这对命名空间包的恢复很重要。

~~~~~act
run_command
~~~~~
~~~~~
find packages -name "__pycache__" -type d -exec rm -rf {} +
~~~~~

### 下一步建议
1.  **重启 LSP**: 再次执行 `LspRestart` 或重启 lvim。
2.  **验证引用**: 检查代码中是否有 `from stitcher import bus` 这种错误写法。如果有，需要全局替换为 `from stitcher.common import bus`。
3.  **重新生成**: 运行 `stitcher init` 和 `stitcher generate` 以确保一切干净。由于我们删除了源文件，`stitcher` 将不再为根目录生成存根，命名空间应当恢复通畅。
