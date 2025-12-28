由于 `Fingerprint` 容器在加载数据时会过滤掉 `None` 值，因此在序列化为 JSON 后，这些键将完全不存在，而不是存储为 `null`。我们需要修正测试中的断言逻辑，改为检查键的缺失。

---
## [WIP] test: 修正 SignatureManager 测试中的空值断言

### 错误分析
在 `Fingerprint.from_dict` 的实现中，如果输入字典的值为 `None`，该键将不会被添加到内部存储中。因此，在 `SignatureManager.save_composite_hashes` 序列化数据时，这些键不会出现在生成的 JSON 中。旧的测试用例尝试访问 `data["bar"]["baseline_yaml_content_hash"]` 并预期得到 `None`，但这在 Python 字典中会触发 `KeyError`。

### 用户需求
修正测试断言，准确反映 `Fingerprint` 容器对空值的处理行为（即不存储、不序列化）。

### 评论
这是对“稀疏存储”特性的正确验证。不存储空键可以减小指纹文件的大小，并使状态表示更加清晰。

### 标签
#intent/tune #flow/ready #priority/low #comp/tests #ai/instruct #task/domain/testing #task/object/signature-manager-test #task/action/fix #task/state/end

---

### Script

#### Acts 1: 修正断言逻辑

我们将修改 `test_signature_manager.py`，使用 `not in` 来验证空键的缺失。

~~~~~act
patch_file
packages/stitcher-application/tests/test_signature_manager.py
~~~~~
~~~~~python
    with sig_path.open("r") as f:
        data = json.load(f)
        assert data["foo"]["baseline_code_structure_hash"] == "abc"
        assert data["foo"]["baseline_yaml_content_hash"] == "def"
        assert data["bar"]["baseline_code_structure_hash"] == "123"
        assert data["bar"]["baseline_yaml_content_hash"] is None

    # Act: Load
~~~~~
~~~~~python
    with sig_path.open("r") as f:
        data = json.load(f)
        assert data["foo"]["baseline_code_structure_hash"] == "abc"
        assert data["foo"]["baseline_yaml_content_hash"] == "def"
        assert data["bar"]["baseline_code_structure_hash"] == "123"
        # Since it was None, the key should be absent in the serialized JSON
        assert "baseline_yaml_content_hash" not in data["bar"]

    # Act: Load
~~~~~
