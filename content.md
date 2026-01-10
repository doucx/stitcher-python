根据 ADAP 和 HFEA 协议，我必须立即采取行动消除系统中的模糊性。当前的 `test_refactor_apply_e2e` 和 `test_refactor_apply_dry_run` 测试失败，且表现为 `AssertionError`，结合代码分析，最可能的原因是重构引擎未能生成任何操作（`no_ops`），导致预期的成功消息或预览头未出现。而造成这一现象的根本原因极有可能是 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py` 中的 `try-except: pass` 块掩盖了底层的解析错误（如文件读取失败、LibCST 解析错误或 Griffe 别名解析错误）。

为了修复此问题并确保系统的确定性，我将制定一个计划，首先移除这些异常吞噬块，并添加必要的日志记录。

[简要回答]
分析显示 `RefactorRunner` 未生成任何 Ops，导致集成测试因断言失败而挂起。根源在于 `SemanticGraph` 的异常吞噬逻辑掩盖了 `_scan_module_usages` 的失败。本计划将移除这些 `try-except` 块以暴露根因，并增强日志可见性。

## [WIP] fix(refactor): 移除 SemanticGraph 中的异常吞噬以修复静默失败

### 错误分析
集成测试 `test_refactor_apply_e2e` 和 `test_refactor_apply_dry_run` 失败，现象为 `AssertionError`。分析 `RefactorRunner` 逻辑可知，当 `Planner` 未生成任何操作时，Runner 会输出 `no_ops` 并返回，而测试用例期望的是 `success` 或 `preview_header` 消息。

Ops 列表为空的直接原因是 `UsageRegistry` 为空。深入分析 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py` 发现，`_scan_module_usages` 方法被包裹在一个宽泛的 `try: ... except Exception: pass` 块中。这违反了 ADAP 协议，掩盖了文件读取、CST 解析或 Visitor 执行过程中的任何错误，导致系统在遇到问题时静默失败，而非显式报错。

### 用户需求
修复集成测试失败，并提升 Refactor 引擎的健壮性和可观测性。

### 评论
这不仅是一个 Bug 修复，更是一次必要的架构清洗。根据 HFEA 原则，"吞噬异常"是严重的架构异味。通过移除它，我们不仅能修复当前的测试，还能防止未来出现类似的幽灵 Bug。

### 目标
1.  修改 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py`，移除 `_scan_module_usages` 和 `_build_registry` 中的 `try-except: pass` 块。
2.  引入 `logging`，在捕获到非致命错误（如果存在业务上允许忽略的错误）时记录警告，而不是静默忽略。对于致命错误（如源码解析失败），应允许异常冒泡或记录 Error。鉴于这是重构引擎，源码解析失败理应是致命的或至少是高优先级的 Error。

### 基本原理
为了符合 **ADAP v1.0** 和 **HFEA v1.0**，系统必须是确定性的。`try-except: pass` 创造了不确定性。移除它将迫使任何潜在的解析错误暴露出来，从而允许我们（或测试框架）捕获并修复真正的根因。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #concept/history #scope/core #ai/instruct #task/domain/refactoring #task/object/semantic-graph #task/action/debug

---

### Script

#### Acts 1: 移除 `graph.py` 中的异常吞噬

我们将修改 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py`，引入 `logging` 模块，并在 `_scan_module_usages` 和 `_build_registry` 中移除或改进异常处理逻辑。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
import libcst as cst
from libcst import helpers
from libcst.metadata import PositionProvider, CodeRange
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, DefaultDict, Set, cast
from collections import defaultdict
import griffe
from stitcher.refactor.workspace import Workspace
from libcst.helpers import (
    get_absolute_module_from_package_for_import,
    get_full_name_for_node,
)
~~~~~
~~~~~python.new
import libcst as cst
from libcst import helpers
from libcst.metadata import PositionProvider, CodeRange
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, DefaultDict, Set, cast
from collections import defaultdict
import logging
import griffe
from stitcher.refactor.workspace import Workspace
from libcst.helpers import (
    get_absolute_module_from_package_for_import,
    get_full_name_for_node,
)

log = logging.getLogger(__name__)
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
    def _scan_module_usages(self, module: griffe.Module):
        # We assume module.filepath is a Path here, checked by caller
        if not isinstance(module.filepath, Path):
            return

        local_symbols: Dict[str, str] = {}
        for name, member in module.members.items():
            try:
                if isinstance(member, griffe.Alias):
                    target_fqn = member.target_path
                else:
                    target_fqn = member.path
                local_symbols[name] = target_fqn
            except Exception:
                pass

        try:
            source = module.filepath.read_text(encoding="utf-8")
            wrapper = cst.MetadataWrapper(cst.parse_module(source))
            is_init = module.filepath.name == "__init__.py"
            visitor = _UsageVisitor(
                module.filepath,
                local_symbols,
                self.registry,
                current_module_fqn=module.path,
                is_init_file=is_init,
            )
            wrapper.visit(visitor)
        except Exception:
            pass
~~~~~
~~~~~python.new
    def _scan_module_usages(self, module: griffe.Module):
        # We assume module.filepath is a Path here, checked by caller
        if not isinstance(module.filepath, Path):
            return

        local_symbols: Dict[str, str] = {}
        for name, member in module.members.items():
            try:
                if isinstance(member, griffe.Alias):
                    target_fqn = member.target_path
                else:
                    target_fqn = member.path
                local_symbols[name] = target_fqn
            except Exception as e:
                log.warning(
                    f"Failed to resolve symbol '{name}' in {module.path}: {e}"
                )

        try:
            source = module.filepath.read_text(encoding="utf-8")
            wrapper = cst.MetadataWrapper(cst.parse_module(source))
            is_init = module.filepath.name == "__init__.py"
            visitor = _UsageVisitor(
                module.filepath,
                local_symbols,
                self.registry,
                current_module_fqn=module.path,
                is_init_file=is_init,
            )
            wrapper.visit(visitor)
        except Exception as e:
            log.error(f"Failed to scan usages in {module.filepath}: {e}")
            raise  # Re-raise to ensure tests fail if scanning fails
~~~~~

### 下一步建议

执行此计划后，如果原来的 `no_ops` 是由异常引起的，测试将会以具体的 Traceback 失败，从而直接指向问题根源。如果测试通过了，说明之前的 `pass` 掩盖了某种非致命但阻断流程的状态，或者仅仅是环境问题。无论结果如何，我们都将获得明确的下一步调试线索。建议运行 pytest 并观察输出。
