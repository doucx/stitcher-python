你的观察力非常敏锐，一针见血。你说得完全正确，**`Any` 没有被导入，这是一个由 `stitcher` 自身逻辑缺陷导致的 bug。**

错误分析

1.  **问题根源**: `StubGenerator` 在生成 `.pyi` 时，如果遇到一个没有类型注解的属性（比如从 `__path__ = ...` 解析出的 `Attribute` 对象），它会**默认**使用 `"Any"`作为其类型提示，生成 `__path__: Any`。
2.  **逻辑断层**: 然而，负责添加 `import` 语句的 `parser` 模块，并不知道 `StubGenerator` 会做出这个“默认使用 `Any`”的决定。`parser` 的导入分析逻辑只检查代码中**显式**写出的类型注解。因为它在源码中没有看到 `Any`，所以它就没有添加 `from typing import Any`。
3.  **最终结果**: 我们生成了一个语法不完整的 `.pyi` 文件，导致类型检查器报错。

解决方案

我们将在 `parser` 中修复这个逻辑断层。我们将赋予它“预知”能力：在解析完一个模块后，如果它发现存在任何没有类型注解的属性，它就会**主动**添加 `from typing import Any`，以确保 `StubGenerator` 后续生成的代码是合法的。

## [WIP] fix: 为无注解属性自动导入 Any 类型

### 用户需求
用户发现 `stitcher` 为 `__path__` 等无类型注解的变量生成了 `__path__: Any`，但没有自动导入 `Any`，导致生成的 `.pyi` 文件无效。

### 评论
这是一个典型的“左右手互搏”的 bug。修复它的关键是确保解析器（`parser`）和生成器（`generator`）对隐式规则（如默认类型）有共同的认知。这次修复将显著提升生成存根的健壮性。

### 目标
1.  修改 `parser.py` 中的 `_enrich_typing_imports` 函数，使其能够检测到模块中存在无注解的属性。
2.  如果检测到，则自动添加 `from typing import Any`。
3.  添加一个新的单元测试，专门验证此行为。

### 基本原理
通过在 `parser.py` 的主函数 `parse_source_code` 中，调用 `_enrich_typing_imports` 之前，检查 `ModuleDef` 中是否存在 `attr.annotation is None` 的情况，来决定是否需要注入 `Any` 的导入。

### 标签
#intent/fix #flow/ready #priority/high #comp/scanner #comp/io #scope/core
#task/domain/parser #task/object/type-import #task/action/implement
#task/state/continue

---

### Script

#### Acts 1: 增强 Parser 的导入逻辑

我们修改 `parser.py`，让它能预判到 `Any` 的使用。

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~old
def _enrich_typing_imports(module: ModuleDef):
    """
    Scans used annotations and injects missing 'typing' imports.
    """
~~~~~
~~~~~new
def _has_unannotated_attributes(module: ModuleDef) -> bool:
    """Check if any attribute in the module IR lacks an annotation."""
    if any(attr.annotation is None for attr in module.attributes):
        return True
    for cls in module.classes:
        if any(attr.annotation is None for attr in cls.attributes):
            return True
    return False


def _enrich_typing_imports(module: ModuleDef):
    """
    Scans used annotations and injects missing 'typing' imports.
    """
~~~~~

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~old
    # A simple combined string of all current imports for quick check
    existing_imports_text = "\n".join(module.imports)

    missing_symbols = set()
~~~~~
~~~~~new
    # A simple combined string of all current imports for quick check
    existing_imports_text = "\n".join(module.imports)

    missing_symbols = set()

    # Proactively add 'Any' if we have unannotated attributes,
    # as the generator will default to using it.
    if _has_unannotated_attributes(module):
        if not re.search(r"\bAny\b", existing_imports_text):
            missing_symbols.add("Any")
~~~~~

#### Acts 2: 添加相应的测试用例

在 `packages/stitcher-scanner/tests/test_parser_imports.py` 中添加一个测试，确保这个新逻辑被覆盖。

~~~~~act
patch_file
packages/stitcher-scanner/tests/test_parser_imports.py
~~~~~
~~~~~old
    assert "from typing import Dict" in combined
    assert "from typing import Any" in combined
    assert "from typing import Union" in combined
~~~~~
~~~~~new
    assert "from typing import Dict" in combined
    assert "from typing import Any" in combined
    assert "from typing import Union" in combined


def test_auto_inject_any_for_unannotated_attribute():
    """If an attribute has no type, generator defaults to 'Any', so we need the import."""
    source = dedent("""
    MY_CONSTANT = 123
    """)
    module = parse_source_code(source)
    
    assert "from typing import Any" in module.imports
~~~~~

### 下一步建议
1.  **运行测试**: 确保新测试和所有现有测试都通过。
2.  **重新生成**: 再次运行 `stitcher generate`。
3.  **验证最终产出**: 检查 `packages/stitcher-application/src/stitcher/app/__init__.pyi`，它现在应该包含 `from typing import Any`。同时，IDE 中的所有报错应该都已消失。

Dogfooding 计划终于要大功告成了！
