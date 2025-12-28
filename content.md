这是一个经典的字符串匹配陷阱。由于 `"code_structure_hash"` 是 `"baseline_code_structure_hash"` 的子字符串，直接使用 `not in` 对 JSON 字符串进行断言会产生误报。

我们需要解析 JSON 并在字典对象层面进行精确的键值检查。

---
## [WIP] test: 修正回归测试中的断言逻辑

### 错误分析
在 `test_hydrate_regression.py` 中，断言 `assert "code_structure_hash" not in content_after` 失败了。这是因为新的键名 `"baseline_code_structure_hash"` 包含了被测试的子字符串。即使旧的键确实被移除了，字符串匹配依然会找到它。

### 用户需求
修正测试脚本，通过解析 JSON 来验证键的精确存在性，而不是依赖模糊的字符串搜索。

### 评论
在处理 JSON 或代码生成时，对原始字符串进行 `in` 断言通常是不够健壮的。解析为结构化数据后再进行断言是最佳实践。

### 标签
#intent/tune #flow/ready #priority/low #comp/tests #ai/instruct #task/domain/testing #task/object/hydrate-regression-test #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修正测试断言

我们将修改测试文件，解析 JSON 并检查字典中的键。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_hydrate_regression.py
~~~~~
~~~~~python
    # 4. Assert
    content_after = sig_file_path.read_text()

    assert success is True
    # The file content MUST change, because we are migrating from legacy to new schema.
    assert content_after != content_before, (
        "Hydrate command failed to migrate legacy signature file."
    )
    
    # Verify the new schema is present
    assert "baseline_code_structure_hash" in content_after
    assert "code_structure_hash" not in content_after

    # Even though we migrated signatures, no docs were hydrated, so user sees "no changes"
~~~~~
~~~~~python
    # 4. Assert
    data_after = json.loads(sig_file_path.read_text())

    assert success is True
    
    # Verify the new schema is present for the function
    fp_func = data_after.get("func", {})
    assert "baseline_code_structure_hash" in fp_func, (
        "New schema key 'baseline_code_structure_hash' missing."
    )
    assert "code_structure_hash" not in fp_func, (
        "Legacy schema key 'code_structure_hash' was not removed."
    )

    # Even though we migrated signatures, no docs were hydrated, so user sees "no changes"
~~~~~
