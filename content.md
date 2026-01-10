在执行修复之前，我必须先解决 `test_parse_imports` 失败的根本原因（`Any` 被错误注入）以及改进异常处理的策略。

1.  **防止 `Any` 污染**：新的 Alias 机制将 `import` 语句映射为了 `Attribute`。由于这些 Attribute 没有 `annotation`，`_enrich_typing_imports` 误判模块包含未注解属性，从而自动注入了 `from typing import Any`。必须修改检查逻辑，忽略 `alias_target` 存在的属性。
2.  **精细化异常捕获**：不能捕获所有 `Exception`。必须显式导入并捕获 `griffe` 的 `AliasResolutionError` 和 `KeyError`。
3.  **测试调整**：`test_parser_fails_on_local_typing_import` 原本是用来证明 Griffe 会崩溃的。现在我们通过 `try...except` 修复了崩溃，测试应当更新为断言“不再崩溃”。

## [WIP] fix: 优化 Alias 处理逻辑并修复副作用

### 用户需求
1.  修复因 Alias Attribute 被误判为未注解属性而导致的 `from typing import Any` 错误注入。
2.  改进 Griffe Parser 中获取位置信息的异常处理，避免宽泛的 `except Exception`。
3.  更新测试以反映修复后的行为（不再崩溃）。

### 评论
Alias 解析的引入揭示了系统中隐含的假设（即“所有 Attribute 都是变量定义”）。我们需要更新这些假设。同时，将 Crash 修复为 Graceful Degradation（降级为无位置信息）是正确的方向，但实现必须严谨。

### 目标
1.  修改 `stitcher-python-analysis` 中的 `_has_unannotated_attributes`，跳过 `alias_target` 不为空的属性。
2.  在 `GriffePythonParser` 中显式捕获 `AliasResolutionError`。
3.  更新 `test_griffe_parsing_bugs.py`，断言解析现在应该成功。

### 标签
#intent/fix #flow/ready #priority/high
#comp/analysis #scope/core #ai/instruct
#task/domain/analysis #task/object/alias-resolution #task/action/fix
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 修复 `Any` 注入判定逻辑

修改 `visitors.py`，在检查未注解属性时，忽略 Alias。

~~~~~act
patch_file
packages/stitcher-python-analysis/src/stitcher/python/analysis/cst/visitors.py
~~~~~
~~~~~python.old
def _has_unannotated_attributes(module: ModuleDef) -> bool:
    if any(attr.annotation is None for attr in module.attributes):
        return True
    for cls in module.classes:
        if any(attr.annotation is None for attr in cls.attributes):
            return True
    return False
~~~~~
~~~~~python.new
def _has_unannotated_attributes(module: ModuleDef) -> bool:
    # Ignore attributes that are aliases (alias_target is set)
    if any(
        attr.annotation is None and attr.alias_target is None
        for attr in module.attributes
    ):
        return True
    for cls in module.classes:
        if any(
            attr.annotation is None and attr.alias_target is None
            for attr in cls.attributes
        ):
            return True
    return False
~~~~~

#### Acts 2: 优化 `_extract_location` 异常处理

显式导入异常并捕获。

~~~~~act
patch_file
packages/stitcher-python-analysis/src/stitcher/python/analysis/griffe/parser.py
~~~~~
~~~~~python.old
import ast
from pathlib import Path
from typing import List, cast, Any, Optional

import griffe
from stitcher.spec import (
~~~~~
~~~~~python.new
import ast
from pathlib import Path
from typing import List, cast, Any, Optional
import logging

import griffe
from griffe import AliasResolutionError
from stitcher.spec import (
~~~~~

~~~~~act
patch_file
packages/stitcher-python-analysis/src/stitcher/python/analysis/griffe/parser.py
~~~~~
~~~~~python.old
    def _extract_location(self, obj: griffe.Object) -> Optional[SourceLocation]:
        try:
            # Accessing lineno on an Alias triggers target resolution.
            # If the target is external/unresolvable, this raises AliasResolutionError (or KeyError).
            # We catch generic Exception here to be safe against Griffe internals,
            # accepting that unresolvable aliases will have no location for now.
            if obj.lineno:
                # Safely access end_lineno as it might not be present on base Object type
                end_lineno = getattr(obj, "end_lineno", None) or obj.lineno
                return SourceLocation(
                    lineno=obj.lineno,
                    col_offset=0,  # Griffe doesn't provide column
                    end_lineno=end_lineno,
                    end_col_offset=0,
                )
        except Exception:
            pass
        return None
~~~~~
~~~~~python.new
    def _extract_location(self, obj: griffe.Object) -> Optional[SourceLocation]:
        try:
            # Accessing lineno on an Alias triggers target resolution.
            # If the target is external/unresolvable, this raises AliasResolutionError (or KeyError).
            # We catch specific exceptions to safely degrade to "no location" for unresolvable aliases.
            if obj.lineno:
                # Safely access end_lineno as it might not be present on base Object type
                end_lineno = getattr(obj, "end_lineno", None) or obj.lineno
                return SourceLocation(
                    lineno=obj.lineno,
                    col_offset=0,  # Griffe doesn't provide column
                    end_lineno=end_lineno,
                    end_col_offset=0,
                )
        except (AliasResolutionError, KeyError):
            # This is expected for external imports in single-file mode.
            # We swallow the error and return None for location.
            pass
        except Exception as e:
            # Log unexpected errors but don't crash the scanner
            logging.getLogger(__name__).warning(
                f"Unexpected error extracting location for {obj.name}: {e}"
            )
        return None
~~~~~

#### Acts 3: 更新 Bug 追踪测试

由于我们修复了 crash，现在这个测试应该断言解析成功。

~~~~~act
patch_file
packages/stitcher-python-adapter/tests/integration/test_griffe_parsing_bugs.py
~~~~~
~~~~~python.old
    # 2. Verification
    # This should raise AliasResolutionError until the bug in Griffe is fixed.
    # This test serves to document this dependency limitation.
    with pytest.raises(AliasResolutionError):
        parser.parse(source_code, "buggy_module.py")
~~~~~
~~~~~python.new
    # 2. Verification
    # Previously this raised AliasResolutionError.
    # Now we handle it gracefully by returning an Attribute with no location.
    module = parser.parse(source_code, "buggy_module.py")
    
    # Verify that the parser survived and produced the alias
    # "from typing import Optional" -> Attribute named "Optional"
    opt = next((a for a in module.attributes if a.name == "Optional"), None)
    assert opt is not None
    assert opt.alias_target == "typing.Optional"
    # Location should be None because resolution failed
    assert opt.location is None
~~~~~

### 下一步建议
执行测试，确保所有红色均已变绿。之后继续推进 **Atomic Task 3**（Adapter 层 SURI 转换）。
