好的，我们将针对星号解包（Starred Unpacking）增加专门的测试用例，以验证 `IRBuildingVisitor` 对复杂赋值语法的支持深度。

## [WIP] test(lang-python): 增加星号解包赋值的 IR 解析测试

### 用户需求
验证解析器是否能正确识别 `x, *y = ...` 这种包含星号解包的赋值语句中的所有符号。

### 评论
星号解包在处理可变长度序列或忽略剩余项时非常常见（如 `head, *tail = items`）。确保 `y` 也能被识别为属性，是保证索引完备性的要求。

### 目标
在 `test_visitors.py` 中增加 `test_parse_starred_unpacking` 测试用例。

### 标签
#intent/tooling #flow/ready #priority/medium #comp/lang-python #concept/parser #scope/tests #task/domain/testing #task/object/ir-parser #task/action/test-enhancement #task/state/continue

---

### Script

#### Acts 1: 增加星号解包测试用例

我们在 `packages/stitcher-lang-python/tests/analysis/unit/cst/test_visitors.py` 的 `TestParser` 类中增加该用例。

~~~~~act
patch_file
packages/stitcher-lang-python/tests/analysis/unit/cst/test_visitors.py
~~~~~
~~~~~python.old
        method_names = {m.name for m in outer.methods}
        assert "outer_method" in method_names
        assert "inner_method" not in method_names
~~~~~
~~~~~python.new
        method_names = {m.name for m in outer.methods}
        assert "outer_method" in method_names
        assert "inner_method" not in method_names

    def test_parse_starred_unpacking(self):
        code = "x, *y = 1, 2, 3"
        module = parse_source_code(code)
        
        attr_names = {a.name for a in module.attributes}
        assert "x" in attr_names
        assert "y" in attr_names
~~~~~

### 下一步建议

1.  **运行完整测试套件**: 执行 `pytest packages/stitcher-lang-python/tests/analysis/unit/cst/test_visitors.py` 确保所有 7 个测试（包含新加的 3 个：解包赋值、嵌套类鲁棒性、星号解包）全部通过。
2.  **验证 FQN 生成**: 如果赋值位于类内部，需确保解包出的属性能够正确生成类前缀的 FQN（例如 `MyClass.x`），这可以通过在 `TestParser` 中增加一个类内部解包赋值的用例来验证。
