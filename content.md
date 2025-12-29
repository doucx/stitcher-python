简要回答：
问题的根源在于 Python 命名空间包 (Namespace Packages) 的实现策略不一致。`pyneedle` 和 `pyneedle-runtime` 使用了 `pkgutil` 风格的显式命名空间（包含 `__init__.py`），而 `pyneedle-pointer` 和 `pyneedle-spec` 却使用了 PEP 420 风格的隐式命名空间（缺失 `__init__.py`）。这种混合状态导致静态分析工具（如 Pyright 和 Pyrefly）在解析 `needle` 这一顶层包时产生歧义，优先锁定了那些包含 `__init__.py` 的路径，从而无法发现其他路径下的子模块。

## [WIP] fix(build): 统一命名空间包策略以修复静态分析解析错误

### 错误分析
静态分析工具（Pyright, Pyrefly）在处理分散在多个目录下的同一个顶层包（这里是 `needle`）时，需要一致的信号来识别它们属于同一个命名空间。

当前项目存在混合策略：
1.  **显式策略 (pkgutil)**: `packages/pyneedle/src/needle/__init__.py` 和 `packages/pyneedle-runtime/src/needle/__init__.py` 存在，且包含 `extend_path` 逻辑。
2.  **隐式策略 (PEP 420)**: `packages/pyneedle-pointer/src/needle/` 和 `packages/pyneedle-spec/src/needle/` 目录下**没有** `__init__.py`。

当 Pyright 解析 `from needle.pointer import ...` 时，它扫描了配置中的 `extraPaths`。一旦它在 `pyneedle` 或 `pyneedle-runtime` 中发现了一个确切的 `needle/__init__.py`，它往往会认为这就定义了该包的“全部”，而不会继续将那些**没有** `__init__.py` 的目录合并进来（因为它们看起来像是隐式命名空间，而工具此时已认定 `needle` 是一个显式包）。

修复方法是在所有参与 `needle` 命名空间的子包根目录中添加相同的 `pkgutil` 风格 `__init__.py`。

### 用户需求
修复 `pyrefly check` 和 `pyright` 无法解析 `needle.pointer` 和 `needle.spec` 等跨包导入的问题，确保静态分析管道畅通。

### 评论
这是一个在 Python Monorepo 开发中非常典型的陷阱。虽然 Python 运行时（尤其是在正确配置的虚拟环境中）通常能容忍这种混合，但静态分析工具要求更严格的一致性。

### 目标
1.  在 `packages/pyneedle-pointer/src/needle/` 创建缺失的 `__init__.py`。
2.  在 `packages/pyneedle-spec/src/needle/` 创建缺失的 `__init__.py`。
3.  确保所有 `needle` 命名空间入口都包含标准的 `pkgutil` 扩展代码。

### 基本原理
通过统一所有 `needle` 包目录下的 `__init__.py` 文件，我们明确告知所有工具：无论该目录位于文件系统的何处，它都是 `needle` 命名空间的一部分，需要被动态合并。这消除了静态分析工具在“常规包”与“命名空间包”之间判定逻辑的冲突。

### 标签
#intent/fix #flow/ready #priority/medium #comp/build #concept/config #scope/dx #ai/instruct #task/domain/build #task/object/namespace-packages #task/action/unification #task/state/begin

---

### Script

#### Acts 1: 补全缺失的命名空间声明文件

我们在 `pyneedle-pointer` 和 `pyneedle-spec` 的根命名空间目录下添加 `__init__.py`，内容与项目中其他 `needle` 包保持一致。

~~~~~act
write_file
packages/pyneedle-pointer/src/needle/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/pyneedle-spec/src/needle/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~
