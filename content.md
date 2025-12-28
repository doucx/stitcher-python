## [WIP] fix: 修复状态机浅拷贝与 ID 不匹配问题

### 错误分析

根据测试失败日志，我们在重构过程中引入了三个关键错误：

1.  **浅拷贝导致的状态持久化失败 (`AssertionError`)**:
    *   在 `_analyze_file` 中，`new_hashes_map = stored_hashes_map.copy()` 仅创建了字典的浅拷贝。
    *   当我们修改嵌套字典（如 `new_hashes_map[fqn]["baseline_code_structure_hash"] = ...`）时，原字典 `stored_hashes_map` 也被同步修改。
    *   导致最后的检查 `if new_hashes_map != stored_hashes_map:` 永远为 `False`，因此更新从未被保存到磁盘。
    *   这导致了 `test_state_signature_drift_force_relink` 和 `test_check_with_force_relink_reconciles_changes` 的失败。

2.  **消息 ID 不匹配 (`AssertionError: Message ... was not sent`)**:
    *   `run_check` 代码中使用的是 `L.check.state.extra_doc`。
    *   但测试 `test_check_command.py` 期望的是 `L.check.issue.extra`。
    *   我们需要统一使用 `L.check.issue.extra` 以保持一致性。

3.  **Clean 状态下的消息吞没 (`AssertionError: Message ... was not sent`)**:
    *   当发生“文档改进”（Doc Improvement）时，`FileCheckResult.is_clean` 仍为 `True`。
    *   `run_check` 中的逻辑在 `if res.is_clean:` 块中执行了 `continue`，跳过了后续详细消息（如 `L.check.state.doc_updated`）的打印逻辑。
    *   这导致 `test_state_doc_improvement_auto_reconciled` 失败。

### 用户需求
修复上述 Bug，确保重构后的代码能够正确通过所有测试。

### 评论
这些错误非常典型，特别是浅拷贝问题在处理嵌套字典时极易被忽视。修复它们对于确保状态机的正确性至关重要。

### 目标
1.  在 `core.py` 中引入 `copy.deepcopy` 解决浅拷贝问题。
2.  修正 `run_check` 中的消息 ID 和控制流逻辑。

### 基本原理
我们将修改 `stitcher/app/core.py`。这是唯一的修改点，但涉及导入、`_analyze_file` 和 `run_check` 三个位置。

### 标签
#intent/fix #flow/ready #priority/high #comp/engine #scope/core #ai/instruct #task/domain/refactoring #task/object/state-machine #task/action/fix-bugs #task/state/continue

---
### Script

#### Acts 1: 修复 core.py 中的 Bug

我们将一次性应用所有修复：
1.  导入 `copy` 模块。
2.  在 `_analyze_file` 中使用 `copy.deepcopy`。
3.  在 `run_check` 中将 `L.check.state.extra_doc` 替换为 `L.check.issue.extra`。
4.  在 `run_check` 中调整逻辑，确保在 `continue` 之前打印 `doc_updated` 消息。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field
~~~~~
~~~~~python.new
import copy
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        current_code_structure_map = self.sig_manager.compute_code_structure_hashes(module)
        current_yaml_content_map = self.doc_manager.compute_yaml_content_hashes(module)
        stored_hashes_map = self.sig_manager.load_composite_hashes(module)
        new_hashes_map = stored_hashes_map.copy()

        all_fqns = set(current_code_structure_map.keys()) | set(stored_hashes_map.keys())
~~~~~
~~~~~python.new
        current_code_structure_map = self.sig_manager.compute_code_structure_hashes(module)
        current_yaml_content_map = self.doc_manager.compute_yaml_content_hashes(module)
        stored_hashes_map = self.sig_manager.load_composite_hashes(module)
        new_hashes_map = copy.deepcopy(stored_hashes_map)

        all_fqns = set(current_code_structure_map.keys()) | set(stored_hashes_map.keys())
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
                res = self._analyze_file(module, force_relink, reconcile)
                if res.is_clean:
                    if res.auto_reconciled_count > 0:
                        bus.info(
                            L.check.state.auto_reconciled,
                            count=res.auto_reconciled_count,
                            path=res.path
                        )
                    continue

                if res.reconciled_count > 0:
~~~~~
~~~~~python.new
                res = self._analyze_file(module, force_relink, reconcile)
                if res.is_clean:
                    if res.auto_reconciled_count > 0:
                        bus.info(
                            L.check.state.auto_reconciled,
                            count=res.auto_reconciled_count,
                            path=res.path
                        )
                    # Even if clean, we might want to report info-level updates like doc improvements
                    for key in sorted(res.infos["doc_improvement"]):
                        bus.info(L.check.state.doc_updated, key=key)
                    continue

                if res.reconciled_count > 0:
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
                # Report Specific Issues
                for key in sorted(res.errors["extra"]):
                    bus.error(L.check.state.extra_doc, key=key)
                for key in sorted(res.errors["signature_drift"]):
                    bus.error(L.check.state.signature_drift, key=key)
~~~~~
~~~~~python.new
                # Report Specific Issues
                for key in sorted(res.errors["extra"]):
                    bus.error(L.check.issue.extra, key=key)
                for key in sorted(res.errors["signature_drift"]):
                    bus.error(L.check.state.signature_drift, key=key)
~~~~~

### 下一步建议
执行此计划后，所有核心状态机测试应当通过。之后，我们可以继续提交 `[COMMIT]` 计划。
