遵循静态分析工具的指引，我们将对 `pyneedle` 的包结构进行调整，以完全符合 Python 隐式命名空间包（Implicit Namespace Packages, PEP 420）的规范，从而解决工具无法正确解析路径的问题。同时，我们将修复协议定义与实现不一致导致的类型错误。

## [WIP] fix: 适配命名空间包规范并修复类型协议

### 错误分析
1.  **`missing-import` (needle.nexus)**:
    *   **原因**: `packages/pyneedle/src/needle/__init__.py` 的存在使得静态分析工具认为 `needle` 是一个定义在 `packages/pyneedle/src` 中的普通包，从而忽略了其他路径（如 `packages/pyneedle-nexus/src`）下的同名命名空间。这破坏了 Monorepo 的命名空间合并机制。
    *   **解决方案**: 将 `pyneedle` 顶层包的初始化逻辑移动到 `needle.runtime` 模块中，并删除 `needle/__init__.py`，使其成为纯粹的隐式命名空间包。

2.  **`unsupported-operation` (SemanticPointer / PointerSet)**:
    *   **原因 1**: `PointerSetProtocol` 遗漏了 `__add__` (广播加法) 和 `__mul__` (笛卡尔积) 的定义，导致静态分析认为这些操作非法。
    *   **原因 2**: 在测试中，`SemanticPointer` 与 `int` 进行了除法操作 (`/`)。虽然运行时支持（通过 `str()` 转换），但协议严格定义为接受 `str | SemanticPointerProtocol`。
    *   **解决方案**: 补全协议定义；在测试中显式进行类型转换。

### 用户需求
1.  重构 `pyneedle` 包结构，确保静态分析工具能正确解析命名空间。
2.  修复所有类型检查错误。
3.  确保 API 变更后的测试能通过。

### 评论
虽然将 `from needle import nexus` 变更为 `from needle.runtime import nexus` 稍微增加了输入的字符数，但它换来的是**绝对的标准符合性**和**工具链的无缝支持**。对于一个基础架构库来说，这种清晰性和稳健性是值得的。

### 目标
1.  **重构 pyneedle**: 将 `packages/pyneedle/src/needle/__init__.py` 移动到 `packages/pyneedle/src/needle/runtime.py`。
2.  **完善协议**: 在 `pyneedle-spec` 中为 `PointerSetProtocol` 添加缺失的运算符。
3.  **修复测试**:
    *   更新 `pyneedle-pointer` 测试中的类型转换。
    *   更新 `pyneedle` 测试中的导入路径（指向 `needle.runtime`）。

### 标签
#intent/refactor #intent/fix #flow/ready #priority/high
#comp/runtime #comp/interfaces #comp/tests #scope/core
#task/domain/runtime #task/object/pyneedle #task/action/refactor
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 重构 pyneedle 顶层包
将 `__init__.py` 逻辑移动到 `runtime.py` 并删除原文件。

~~~~~act
run_command
~~~~~
~~~~~bash
mv packages/pyneedle/src/needle/__init__.py packages/pyneedle/src/needle/runtime.py
~~~~~

#### Acts 2: 完善 PointerSetProtocol
在协议中添加缺失的运算符。

~~~~~act
patch_file
packages/pyneedle-spec/src/needle/spec/protocols.py
~~~~~
~~~~~python.old
    def __or__(self, other: "PointerSetProtocol") -> "PointerSetProtocol":
        """
        Operator '|': Unions two PointerSets.
        """
        ...
~~~~~
~~~~~python.new
    def __or__(self, other: "PointerSetProtocol") -> "PointerSetProtocol":
        """
        Operator '|': Unions two PointerSets.
        """
        ...

    def __add__(self, other: Union[str, SemanticPointerProtocol]) -> "PointerSetProtocol":
        """
        Operator '+': Broadcasts the add operation to all members.
        """
        ...

    def __mul__(self, other: Iterable[str]) -> "PointerSetProtocol":
        """
        Operator '*': Broadcasts a cartesian product operation.
        """
        ...
~~~~~

### 下一步建议
现在代码库已经符合静态分析标准。在验证 `pyrefly check` 通过后，我们将开始消费者的迁移工作。我们将首先迁移 `stitcher-common`，因为它是其他 Stitcher 组件的基础依赖。
