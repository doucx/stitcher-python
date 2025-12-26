You are absolutely right. The test has correctly caught a flaw in my previous implementation. My apologies.

The test failure `assert 'from typing import Any' in []` proves that my logic in `_enrich_typing_imports` was not correctly triggered or was flawed in its execution. The proactive check I added for `Any` did not result in the import being added.

Let's fix this properly with a cleaner, more robust implementation. The issue is that the logic became fragmented. A better approach is to first gather **all** required symbols (both proactively for `Any` and reactively from annotations), and then add the necessary imports in a single, final step.

## [WIP] fix: Refactor import enrichment to correctly add `Any`

### 错误分析
测试用例暴露了 `_enrich_typing_imports` 函数中的一个逻辑缺陷。尽管我的意图是为无注解的属性主动添加 `from typing import Any`，但实现方式未能确保在所有情况下都正确执行。`missing_symbols` 集合的填充和最终的 `append` 循环之间存在问题，导致在只存在无注解属性而无任何显式类型注解的情况下，该逻辑链条中断。

### 用户需求
修复 `parser` 模块，使其在遇到无类型注解的属性时，能可靠、正确地将 `from typing import Any` 添加到模块的导入列表中。

### 评论
这个 bug 的修复是生成有效 `.pyi` 文件的基本前提。这次重构将使导入注入逻辑更加清晰和确定，避免未来出现类似的逻辑碎片化问题。

### 目标
1.  重构 `_enrich_typing_imports` 函数，统一处理所有需要从 `typing` 模块导入的符号。
2.  确保 `_has_unannotated_attributes` 的检测能正确触发 `Any` 的导入。
3.  确保测试用例 `test_auto_inject_any_for_unannotated_attribute` 通过。

### 基本原理
我们将简化 `_enrich_typing_imports` 的逻辑：
1.  创建一个 `required_symbols` 集合。
2.  **第一步**: 如果模块中存在无注解的属性，直接将 `'Any'` 添加到 `required_symbols`。
3.  **第二步**: 遍历代码中所有显式的类型注解，将其中包含的 `typing` 符号（如 `'List'`, `'Optional'`）也添加到 `required_symbols`。
4.  **最后**: 遍历最终的 `required_symbols` 集合，为那些尚未被导入的符号生成并添加 `import` 语句。

---

### Script

#### Acts 1: 重构并修复 `_enrich_typing_imports`

我们用更清晰、更正确的逻辑完全替换 `packages/stitcher-scanner/src/stitcher/scanner/parser.py` 中的 `_enrich_typing_imports` 函数。

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~old
def _enrich_typing_imports(module: ModuleDef):
    """
    Scans used annotations and injects missing 'typing' imports.
    """
    # Common symbols from 'typing' that are often used without quotes
    # We deliberately exclude generic 'List'/'Dict' if the user imports
    # standard collections, but for safety in .pyi (which often supports older Pythons),
    # adding them from typing is usually safe if missing.
    TYPING_SYMBOLS = {
        "List",
        "Dict",
        "Tuple",
        "Set",
        "Optional",
        "Union",
        "Any",
        "Callable",
        "Sequence",
        "Iterable",
        "Type",
        "Final",
        "ClassVar",
        "Mapping",
    }

    annotations = _collect_annotations(module)
    if not annotations:
        return

    # A simple combined string of all current imports for quick check
    existing_imports_text = "\n".join(module.imports)

    missing_symbols = set()

    # Proactively add 'Any' if we have unannotated attributes,
    # as the generator will default to using it.
    if _has_unannotated_attributes(module):
        if not re.search(r"\bAny\b", existing_imports_text):
            missing_symbols.add("Any")

    for ann in annotations:
        # Check for each symbol
        for symbol in TYPING_SYMBOLS:
            # We use regex word boundary to avoid partial matches (e.g. matching 'List' in 'MyList')
            if re.search(rf"\b{symbol}\b", ann):
                # Check if it's already imported
                # This is a heuristic: if "List" appears in imports text, assume it's covered.
                # It handles "from typing import List" and "import typing" (if user wrote typing.List)
                # But wait, if user wrote "typing.List", then 'List' matches \bList\b.
                # If existing imports has "import typing", we shouldn't add "from typing import List"?
                # Actually, if they wrote "typing.List", the annotation string is "typing.List".
                # If we just add "from typing import List", it doesn't hurt.
                # But if they wrote "List" and have NO import, we MUST add it.

                if not re.search(rf"\b{symbol}\b", existing_imports_text):
                    missing_symbols.add(symbol)

    for symbol in sorted(missing_symbols):
        module.imports.append(f"from typing import {symbol}")
~~~~~
~~~~~new
def _enrich_typing_imports(module: ModuleDef):
    """
    Scans used annotations and module structure, then injects necessary
    'typing' imports.
    """
    TYPING_SYMBOLS = {
        "List", "Dict", "Tuple", "Set", "Optional", "Union", "Any",
        "Callable", "Sequence", "Iterable", "Type", "Final", "ClassVar", "Mapping",
    }

    required_symbols = set()

    # 1. Proactively add 'Any' if generator will need it for unannotated attributes.
    if _has_unannotated_attributes(module):
        required_symbols.add("Any")

    # 2. Reactively find symbols used in explicit annotations.
    annotations = _collect_annotations(module)
    for ann in annotations:
        for symbol in TYPING_SYMBOLS:
            if re.search(rf"\b{symbol}\b", ann):
                required_symbols.add(symbol)
    
    if not required_symbols:
        return

    # 3. Add imports for required symbols that are not already imported.
    existing_imports_text = "\n".join(module.imports)
    
    for symbol in sorted(list(required_symbols)):
        # Heuristic: if the symbol appears as a word in the imports, assume it's covered.
        if not re.search(rf"\b{symbol}\b", existing_imports_text):
            module.imports.append(f"from typing import {symbol}")
~~~~~

### 下一步建议
这次的实现更加直接和清晰。
1.  **运行测试**: 再次运行 `pytest packages/stitcher-scanner/tests/test_parser_imports.py`。这一次，`test_auto_inject_any_for_unannotated_attribute` 应该会通过。
2.  **全量回归**: 运行完整的测试套件 `pytest` 确保没有引入回归问题。
3.  **最终生成**: 确认无误后，再次运行 `stitcher generate`。生成的 `__init__.pyi` 文件现在应该是完全合法的了。
