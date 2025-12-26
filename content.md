简要回答：
测试失败的原因有两个细节：
1.  **Chomping 符号**: PyYAML 默认生成的块样式符号是 `|-`（表示剔除末尾多余换行符），而不是简单的 `|`。
2.  **Key 的引用**: 因为我们的 Key 可能包含点号（如 `MyClass.method`），PyYAML 为了安全起见对 Key 进行了双引号包裹（如 `"MyClass":`）。
3.  **结构差异**: 现在的输出不再是单行，因此 `key: value` 这种子字符串匹配在物理层面上失效了。

我们将更新测试用例中的断言，使其适应新的、一致的块格式。

## [WIP] test: 更新测试以匹配统一的 YAML 块格式

### 错误分析
由于我们强制将所有字符串输出为 YAML 的 Literal Block Style (`|-`)，原本基于单行输出假设的测试断言失效了。例如，原本期望 `my_func: doc`，现在实际输出为：
```yaml
"my_func": |-
  doc
```
此外，PyYAML 在这种模式下对 Key 进行了引用。

### 用户需求
修复受 YAML 样式变更影响的集成测试和单元测试，确保测试能正确验证新的块状存储格式。

### 评论
测试必须紧跟实现。这次样式的变更虽然是视觉上的，但由于涉及到物理存储格式的改变，必须同步更新那些直接对文件内容进行字符串匹配的测试。

### 目标
1.  修改 `tests/integration/test_init_command.py`，更新对 `init` 生成内容的匹配逻辑。
2.  修改 `packages/stitcher-io/tests/test_document_io.py`，处理双引号 Key 和 `|-` 指示符。

### 标签
#intent/test #flow/ready #priority/medium #comp/tests #ai/instruct
#task/domain/testing #task/object/yaml-assertions #task/action/update
#task/state/continue

---

### Script

#### Acts 1: 更新集成测试断言

修改 `tests/integration/test_init_command.py`。

~~~~~act
patch_file
tests/integration/test_init_command.py
~~~~~
~~~~~old
    # 3. Assert
    expected_yaml = project_root / "src/main.stitcher.yaml"
    assert expected_yaml in created_files
    assert "my_func: This is a docstring." in expected_yaml.read_text()

    spy_bus.assert_id_called(L.init.file.created, level="success")
~~~~~
~~~~~new
    # 3. Assert
    expected_yaml = project_root / "src/main.stitcher.yaml"
    assert expected_yaml in created_files
    
    content = expected_yaml.read_text()
    # Check for block style with quoted key
    assert '"my_func": |-' in content
    assert "  This is a docstring." in content

    spy_bus.assert_id_called(L.init.file.created, level="success")
~~~~~

#### Acts 2: 更新 YamlAdapter 单元测试断言

修改 `packages/stitcher-io/tests/test_document_io.py`。

~~~~~act
patch_file
packages/stitcher-io/tests/test_document_io.py
~~~~~
~~~~~old
    # Verify file content is deterministic (sorted)
    content = file_path.read_text(encoding="utf-8")
    # "MyClass" comes before "MyClass.method" (lexicographical)
    # But "func" comes last.
    # Let's just check raw content contains keys
    assert "MyClass:" in content
    assert "中文测试" in content
~~~~~
~~~~~new
    # Verify file content is deterministic (sorted)
    content = file_path.read_text(encoding="utf-8")
    # "MyClass" comes before "MyClass.method" (lexicographical)
    # But "func" comes last.
    # Let's just check raw content contains keys (which are now quoted)
    assert '"MyClass": |-' in content
    assert "  中文测试" in content
~~~~~

~~~~~act
patch_file
packages/stitcher-io/tests/test_document_io.py
~~~~~
~~~~~old
def test_yaml_adapter_block_format_consistency(tmp_path: Path):
    """
    Verify that all strings (multiline or single-line) are saved
    using Literal Block Style (|) for consistency.
    """
    adapter = YamlAdapter()
    file_path = tmp_path / "docs.yaml"
    data = {
        "multi": "Line 1\nLine 2",
        "single": "Just one line"
    }

    adapter.save(file_path, data)

    content = file_path.read_text(encoding="utf-8")
    
    # Both should use block style
    assert "multi: |" in content
    assert "single: |" in content
    
    # Check indentation
    assert "  Line 1" in content
    assert "  Just one line" in content
~~~~~
~~~~~new
def test_yaml_adapter_block_format_consistency(tmp_path: Path):
    """
    Verify that all strings (multiline or single-line) are saved
    using Literal Block Style (|-) for consistency.
    """
    adapter = YamlAdapter()
    file_path = tmp_path / "docs.yaml"
    data = {
        "multi": "Line 1\nLine 2",
        "single": "Just one line"
    }

    adapter.save(file_path, data)

    content = file_path.read_text(encoding="utf-8")
    
    # Both should use block style with strip chomping (|-) and quoted keys
    assert '"multi": |-' in content
    assert '"single": |-' in content
    
    # Check indentation
    assert "  Line 1" in content
    assert "  Just one line" in content
~~~~~

### 下一步建议
1.  **运行全量测试**: 执行 `pytest`。
2.  **重运行 Dogfooding**: 再次执行 `stitcher init` 刷新你的本地资产。
3.  **检查产出**: 确保 `.stitcher.yaml` 文件现在的外观符合你的审美要求（统一的 `|-` 块样式）。
