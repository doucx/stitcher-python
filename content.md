分析完全正确。测试的失败和类型错误是意料之中的，它们精确地暴露了旧架构与新架构之间的契约冲突。这正是测试驱动开发（TDD）和强类型检查的价值所在：它们是确保我们重构正确的“护栏”。

我将生成一个计划来修复这些问题，使测试和类型系统与我们新的“解耦”数据模型保持一致。

## [WIP] fix: 修复因数据模型解耦导致的测试与类型错误

### 错误分析

**1. `test_store.py` 失败 (`TypeError`)**:
*   **原因**: 我们修改了 `ReferenceRecord` 的构造函数，使其 `target_fqn` 成为必需参数。单元测试 `test_analysis_update` 在创建 `ReferenceRecord` 实例时，没有提供这个新参数，导致 `TypeError`。
*   **解决方案**: 更新测试用例，为 `ReferenceRecord` 的实例化提供一个有效的 `target_fqn`。

**2. `test_index_adapter_references.py` 失败 (`TypeError: 'NoneType' is not iterable`)**:
*   **原因**: 测试中的辅助函数 `find_refs` 试图检查 `r.target_id` (`if target_fragment in r.target_id`)。根据我们的新设计，在扫描阶段 `target_id` **故意**被设置为 `None`，等待 Linker 填充。因此，代码尝试在 `None` 上进行 `in` 操作，引发了 `TypeError`。
*   **解决方案**: 修改 `find_refs` 辅助函数，使其检查 `r.target_fqn` 字段。这不仅能修复错误，还能使测试的意图更加明确：验证扫描器是否正确识别了引用的*逻辑目标*，而非物理链接。

**3. `griffe_parser.py` Pyright 错误**:
*   **原因**: 类型检查器是正确的。`griffe.Alias` 类型并不继承自 `griffe.Object`。我们的 `_extract_location` 函数签名 `(self, obj: griffe.Object)` 过于严格，当代码尝试传入一个 `Alias` 对象时，就构成了类型违规。
*   **解决方案**: 放宽 `_extract_location` 的类型约束，接受 `Union[griffe.Object, griffe.Alias]`。这准确地反映了该函数的实际用途，即处理任何具有 `.lineno` 属性的 Griffe 节点。

### 用户需求

修复因上一轮数据模型解耦重构而导致的所有测试失败和 Pyright 类型错误。

### 评论

这些失败是重构过程中的健康信号。它们迫使我们更新测试套件，以验证新的架构假设（例如 `target_id` 在扫描后为空）。通过修复这些问题，我们不仅使构建恢复绿色，还强化了测试用例，使其能够更精确地反映我们新架构的意图。

### 目标

1.  在 `test_store.py` 中，更新 `ReferenceRecord` 的创建，为其提供 `target_fqn`。
2.  在 `test_index_adapter_references.py` 中，修改测试逻辑以断言 `target_fqn` 而非 `target_id`。
3.  在 `griffe_parser.py` 中，修正 `_extract_location` 的类型注解，使其接受 `Alias` 对象。

### 基本原理

我们的核心原则是“验证意图而非实现”。在扫描阶段，`PythonAdapter` 的“意图”是记录一个指向逻辑 FQN 的引用。测试也应该验证这一点。旧的测试错误地耦合了扫描与链接两个阶段的产物。通过将断言目标从 `target_id` (链接产物) 切换到 `target_fqn` (扫描产物)，我们使测试与被测单元的职责保持了高度一致。

### 标签

#intent/fix #flow/ready #priority/critical #comp/tests #comp/index #comp/python-adapter #scope/dx #ai/instruct #task/domain/architecture #task/object/schema-decoupling #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `test_store.py`

我们将为 `ReferenceRecord` 的实例化提供缺失的 `target_fqn` 参数。

~~~~~act
patch_file
packages/stitcher-index/tests/unit/test_store.py
~~~~~
~~~~~python.old
    references = [
        ReferenceRecord(
            target_id="py://src/other.py#func",
            kind="import",
            lineno=6,
            col_offset=0,
            end_lineno=6,
            end_col_offset=15,
        )
    ]
~~~~~
~~~~~python.new
    references = [
        ReferenceRecord(
            target_fqn="src.other.func",
            target_id="py://src/other.py#func",
            kind="import",
            lineno=6,
            col_offset=0,
            end_lineno=6,
            end_col_offset=15,
        )
    ]
~~~~~

#### Acts 2: 修复 `test_index_adapter_references.py`

我们将修改测试的断言逻辑，使其检查新引入的 `target_fqn` 字段。

~~~~~act
patch_file
packages/stitcher-python-adapter/tests/integration/test_index_adapter_references.py
~~~~~
~~~~~python.old
    # 辅助断言函数
    def find_refs(target_fragment):
        return [r for r in references if target_fragment in r.target_id]

    # 1. 验证导入引用 (Imports)
    # import os -> target should assume os
    # 注意：SURI 生成目前是推测性的，我们主要验证它捕获了 'os' 这个意图
    os_refs = find_refs("os")
    assert len(os_refs) >= 1
    assert os_refs[0].kind == "import_path"

    # from mypkg import utils
    # 修正：SURI 可能是 py://mypkg.py#utils，不包含 "mypkg.utils" 连续字符串
    # 我们放宽断言，检查 target_id 中是否包含关键部分
    utils_refs = [
        r for r in references if "mypkg" in r.target_id and "utils" in r.target_id
    ]
    assert len(utils_refs) >= 1

    # 2. 验证调用引用 (Usages)
    # utils.do_work()
    # 应该引用 mypkg.utils.do_work (基于 import utils)
    do_work_refs = find_refs("do_work")
    assert len(do_work_refs) > 0
    assert do_work_refs[0].kind == "symbol"
~~~~~
~~~~~python.new
    # 辅助断言函数
    def find_refs(target_fqn_fragment):
        # After decoupling, we assert against the logical target_fqn, not the physical target_id
        return [r for r in references if target_fqn_fragment in r.target_fqn]

    # 1. 验证导入引用 (Imports)
    # import os
    os_refs = find_refs("os")
    assert len(os_refs) >= 1
    assert os_refs[0].kind == "import_path"
    assert os_refs[0].target_fqn == "os"

    # from mypkg import utils
    utils_refs = find_refs("mypkg.utils")
    assert len(utils_refs) >= 1
    assert utils_refs[0].target_fqn == "mypkg.utils"

    # 2. 验证调用引用 (Usages)
    # utils.do_work() -> should resolve to a reference to 'mypkg.utils.do_work'
    do_work_refs = find_refs("mypkg.utils.do_work")
    assert len(do_work_refs) > 0
    assert do_work_refs[0].kind == "symbol"
~~~~~

#### Acts 3: 修复 Pyright 类型错误

最后，我们放宽 `_extract_location` 的类型注解，并添加必要的 `Union` 导入。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py
~~~~~
~~~~~python.old
from pathlib import Path
from typing import List, cast, Any, Optional
import logging
~~~~~
~~~~~python.new
from pathlib import Path
from typing import List, cast, Any, Optional, Union
import logging
~~~~~
~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py
~~~~~
~~~~~python.old
    def _extract_location(self, obj: griffe.Object) -> Optional[SourceLocation]:
        try:
            # Accessing lineno on an Alias triggers target resolution.
~~~~~
~~~~~python.new
    def _extract_location(
        self, obj: Union[griffe.Object, griffe.Alias]
    ) -> Optional[SourceLocation]:
        try:
            # Accessing lineno on an Alias triggers target resolution.
~~~~~

### 下一步建议

测试和类型系统现已与我们解耦后的数据模型完全对齐。所有障碍都已清除。

现在是时候构建连接这一切的核心组件了。我建议立即开始实施 **Phase 3: 实现链接器 (The Stitcher Linker)**。这将是一个全新的组件，负责读取扫描阶段产生的数据，解析 FQN 引用，并用确定的 SURI 更新数据库，最终完成从“逻辑意图”到“物理链接”的转换。
