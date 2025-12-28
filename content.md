由于我们引入了严格的 `Fingerprint` 模型，旧的单元测试中直接使用字典（Dict）作为参数的代码现在会触发 `AttributeError`。我们需要更新这些测试用例，使其符合新的接口契约。

---
## [WIP] test: 更新 SignatureManager 单元测试以适配 Fingerprint 模型

### 错误分析
在重构 `SignatureManager` 后，其 `save_composite_hashes` 方法现在期望接收 `Dict[str, Fingerprint]`。然而，`test_signature_manager.py` 中的旧测试用例仍在传递原始字典，导致在尝试调用 `fp.to_dict()` 时抛出 `AttributeError: 'dict' object has no attribute 'to_dict'`。

### 用户需求
修复受影响的单元测试，确保测试数据使用 `Fingerprint` 对象。

### 评论
这是重构后的必然步骤。单元测试必须与它们所测试的组件的最新接口保持同步。

### 目标
1.  更新 `packages/stitcher-application/tests/test_signature_manager.py`。
2.  将测试数据中的字典包装为 `Fingerprint` 对象。

### 标签
#intent/tooling #flow/ready #priority/medium #comp/tests #concept/state #ai/instruct #task/domain/testing #task/object/signature-manager-test #task/action/fix #task/state/end

---

### Script

#### Acts 1: 更新 SignatureManager 单元测试

我们将修改测试用例，使用 `Fingerprint.from_dict` 来转换测试数据。

~~~~~act
patch_file
packages/stitcher-application/tests/test_signature_manager.py
~~~~~
~~~~~python
import json
from pathlib import Path
from stitcher.spec import ModuleDef, FunctionDef, Argument, ArgumentKind
from stitcher.app.services import SignatureManager


def create_func(name="func", args=None, ret=None):
~~~~~
~~~~~python
import json
from pathlib import Path
from stitcher.spec import ModuleDef, FunctionDef, Argument, ArgumentKind, Fingerprint
from stitcher.app.services import SignatureManager


def create_func(name="func", args=None, ret=None):
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/test_signature_manager.py
~~~~~
~~~~~python
def test_manager_save_and_load_composite_hashes(tmp_path: Path):
    # Arrange
    manager = SignatureManager(root_path=tmp_path)
    module = ModuleDef(file_path="src/main.py", functions=[create_func(name="foo")])

    hashes_to_save = {
        "foo": {
            "baseline_code_structure_hash": "abc",
            "baseline_yaml_content_hash": "def",
        },
        "bar": {
            "baseline_code_structure_hash": "123",
            "baseline_yaml_content_hash": None,
        },
    }

    # Act: Save
    manager.save_composite_hashes(module, hashes_to_save)
~~~~~
~~~~~python
def test_manager_save_and_load_composite_hashes(tmp_path: Path):
    # Arrange
    manager = SignatureManager(root_path=tmp_path)
    module = ModuleDef(file_path="src/main.py", functions=[create_func(name="foo")])

    # Data is now composed of Fingerprint objects
    hashes_to_save = {
        "foo": Fingerprint.from_dict({
            "baseline_code_structure_hash": "abc",
            "baseline_yaml_content_hash": "def",
        }),
        "bar": Fingerprint.from_dict({
            "baseline_code_structure_hash": "123",
            "baseline_yaml_content_hash": None,
        }),
    }

    # Act: Save
    manager.save_composite_hashes(module, hashes_to_save)
~~~~~
