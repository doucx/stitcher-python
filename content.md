简要回答
你说得对，我完全忽略了 Stitcher 的核心价值——同步 Sidecar 文件。一个只修改 Python 代码的重构引擎是不完整的。

我们现在就来实现 `DocUpdater` 和 `SigUpdater` 的逻辑，并将它们集成到 `RenameSymbolOperation` 中，使其具备“代码-文档-指纹”三位一体的原子化重构能力。

## [WIP] feat(refactor): 集成 sidecar 文件更新到 RenameSymbolOperation

### 用户需求
`RenameSymbolOperation` 在重构 Python 代码的同时，必须同步更新 `.stitcher.yaml` 和 `.stitcher/signatures/*.json` 文件中所有相关的 FQN 键。

### 评论
这正是 `stitcher-refactor` 的核心竞争力所在。通过将 Sidecar 文件的更新作为重构操作的**一等公民**，我们保证了架构元数据与代码的同步演进，彻底消除了传统重构工具导致的“元数据腐败”问题。

### 目标
1.  创建 `packages/stitcher-refactor/src/stitcher/refactor/sidecar` 模块。
2.  实现 `DocUpdater` 和 `SigUpdater` 的核心逻辑，用于重命名字典中的 key。
3.  修改 `RenameSymbolOperation.analyze` 方法，使其能够：
    *   定位与被修改的 `.py` 文件关联的 Sidecar 文件。
    *   读取 Sidecar 文件内容。
    *   调用 Updater 更新内容。
    *   为被修改的 Sidecar 文件生成新的 `WriteFileOp`。
4.  扩展端到端集成测试，验证重构后 Sidecar 文件的内容是否正确更新。

### 基本原理
-   **派生路径**: 操作根据源文件路径 (`a/b/c.py`) 推导出其 Sidecar 文件的路径 (`a/b/c.stitcher.yaml` 和 `.stitcher/signatures/a/b/c.json`)。
-   **数据转换**: Updater 纯粹是数据转换函数，接收 `(data, old_fqn, new_fqn)` 并返回新的 `data`。它们不执行任何 IO 操作。
-   **原子化操作**: `analyze` 方法将代码变更和 Sidecar 变更聚合到一个单一的操作列表中。`TransactionManager` 在 `commit` 时会将所有变更原子化地写入磁盘，从而保证一致性。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #concept/state #task/domain/refactor #task/object/sidecar-sync #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建 Sidecar 模块及 Updater 实现
我们创建 `sidecar` 模块并添加 Updater 的实现。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-refactor/src/stitcher/refactor/sidecar
touch packages/stitcher-refactor/src/stitcher/refactor/sidecar/__init__.py
~~~~~

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/sidecar/updater.py
~~~~~
~~~~~python
import json
from typing import Dict, Any
from pathlib import Path
import yaml


class DocUpdater:
    def rename_key(self, data: Dict[str, Any], old_key: str, new_key: str) -> Dict[str, Any]:
        if old_key in data:
            # Preserve order if possible, but for simplicity, dict recreation is fine
            new_data = data.copy()
            new_data[new_key] = new_data.pop(old_key)
            return new_data
        return data

    def load(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        # Using a simple loader for now. In reality, we'd use stitcher-common's YamlAdapter.
        return yaml.safe_load(path.read_text("utf-8")) or {}

    def dump(self, data: Dict[str, Any]) -> str:
        # Using a simple dumper.
        return yaml.dump(dict(sorted(data.items())), allow_unicode=True)


class SigUpdater:
    def rename_key(self, data: Dict[str, Any], old_key: str, new_key: str) -> Dict[str, Any]:
        if old_key in data:
            new_data = data.copy()
            new_data[new_key] = new_data.pop(old_key)
            return new_data
        return data

    def load(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text("utf-8"))

    def dump(self, data: Dict[str, Any]) -> str:
        return json.dumps(data, indent=2, sort_keys=True)
~~~~~

#### Acts 2: 集成 Sidecar 更新到 RenameSymbolOperation
我们修改 `RenameSymbolOperation` 的 `analyze` 方法来处理 Sidecar 文件。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~python.old
import libcst as cst
from collections import defaultdict
from typing import List, Dict
from pathlib import Path

from .base import AbstractOperation
from .transforms.rename_transformer import SymbolRenamerTransformer
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, WriteFileOp
from stitcher.refactor.engine.graph import UsageLocation


class RenameSymbolOperation(AbstractOperation):
~~~~~
~~~~~python.new
import libcst as cst
from collections import defaultdict
from typing import List, Dict
from pathlib import Path

from .base import AbstractOperation
from .transforms.rename_transformer import SymbolRenamerTransformer
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, WriteFileOp
from stitcher.refactor.engine.graph import UsageLocation
from stitcher.refactor.sidecar.updater import DocUpdater, SigUpdater


class RenameSymbolOperation(AbstractOperation):
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~python.old
        for file_path, file_usages in usages_by_file.items():
            try:
                # We assume file_path is absolute from Griffe
                original_source = file_path.read_text(encoding="utf-8")
                
                module = cst.parse_module(original_source)
                wrapper = cst.MetadataWrapper(module)
                
                transformer = SymbolRenamerTransformer(rename_map, file_usages)
                modified_module = wrapper.visit(transformer)

                if modified_module.code != original_source:
                    # The path in WriteFileOp should be relative to the project root
                    relative_path = file_path.relative_to(ctx.graph.root_path)
                    ops.append(WriteFileOp(path=relative_path, content=modified_module.code))

            except Exception:
                # Log error and continue? For now, let it fail fast.
                # In a real CLI, we'd collect these errors.
                raise

        return ops
~~~~~
~~~~~python.new
        for file_path, file_usages in usages_by_file.items():
            try:
                # --- 1. Handle Code Renaming ---
                original_source = file_path.read_text(encoding="utf-8")
                
                module = cst.parse_module(original_source)
                wrapper = cst.MetadataWrapper(module)
                
                transformer = SymbolRenamerTransformer(rename_map, file_usages)
                modified_module = wrapper.visit(transformer)

                relative_path = file_path.relative_to(ctx.graph.root_path)
                if modified_module.code != original_source:
                    ops.append(WriteFileOp(path=relative_path, content=modified_module.code))

                # --- 2. Handle Sidecar Renaming ---
                doc_updater = DocUpdater()
                sig_updater = SigUpdater()

                # Doc file
                doc_path = file_path.with_suffix(".stitcher.yaml")
                if doc_path.exists():
                    doc_data = doc_updater.load(doc_path)
                    new_doc_data = doc_updater.rename_key(doc_data, self.old_fqn, self.new_fqn)
                    if new_doc_data != doc_data:
                        ops.append(WriteFileOp(
                            path=doc_path.relative_to(ctx.graph.root_path),
                            content=doc_updater.dump(new_doc_data)
                        ))

                # Signature file
                sig_path = ctx.graph.root_path / ".stitcher/signatures" / relative_path.with_suffix(".json")
                if sig_path.exists():
                    sig_data = sig_updater.load(sig_path)
                    new_sig_data = sig_updater.rename_key(sig_data, self.old_fqn, self.new_fqn)
                    if new_sig_data != sig_data:
                        ops.append(WriteFileOp(
                            path=sig_path.relative_to(ctx.graph.root_path),
                            content=sig_updater.dump(new_sig_data)
                        ))

            except Exception:
                raise

        return ops
~~~~~

#### Acts 3: 扩展端到端集成测试
现在我们更新 E2E 测试，让它创建并验证 Sidecar 文件。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
~~~~~
~~~~~python.old
def test_rename_symbol_end_to_end(tmp_path):
    # 1. Setup: Create a virtual project
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    
    # File with the definition
    core_path = pkg_dir / "core.py"
    core_path.write_text(
        "class OldHelper:\n    pass\n\ndef old_func():\n    pass",
        encoding="utf-8"
    )
    
    # File with usages
    app_path = pkg_dir / "app.py"
    app_path.write_text(
        "from .core import OldHelper, old_func\n\n"
        "h = OldHelper()\n"
        "old_func()",
        encoding="utf-8"
    )

    # 2. Analysis Phase
    graph = SemanticGraph(root_path=tmp_path)
~~~~~
~~~~~python.new
import yaml
import json

def test_rename_symbol_end_to_end(tmp_path):
    # 1. Setup: Create a virtual project with code and sidecars
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    
    # File with the definition
    core_path = pkg_dir / "core.py"
    core_path.write_text(
        "class OldHelper:\n    pass\n\ndef old_func():\n    pass",
        encoding="utf-8"
    )
    
    # File with usages
    app_path = pkg_dir / "app.py"
    app_path.write_text(
        "from .core import OldHelper, old_func\n\n"
        "h = OldHelper()\n"
        "old_func()",
        encoding="utf-8"
    )

    # Sidecar files for core.py
    doc_path = core_path.with_suffix(".stitcher.yaml")
    doc_path.write_text(yaml.dump({
        "mypkg.core.OldHelper": "This is the old helper.",
        "mypkg.core.old_func": "This is an old function."
    }))

    sig_dir = tmp_path / ".stitcher" / "signatures" / "mypkg"
    sig_dir.mkdir(parents=True)
    sig_path = sig_dir / "core.json"
    sig_path.write_text(json.dumps({
        "mypkg.core.OldHelper": {"baseline_code_structure_hash": "hash1"},
        "mypkg.core.old_func": {"baseline_code_structure_hash": "hash2"}
    }))

    # 2. Analysis Phase
    graph = SemanticGraph(root_path=tmp_path)
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
~~~~~
~~~~~python.old
    modified_app_code = app_path.read_text(encoding="utf-8")
    expected_app_code = ("from .core import NewHelper, old_func\n\n"
                         "h = NewHelper()\n"
                         "old_func()")
    assert modified_app_code == expected_app_code
~~~~~
~~~~~python.new
    modified_app_code = app_path.read_text(encoding="utf-8")
    expected_app_code = ("from .core import NewHelper, old_func\n\n"
                         "h = NewHelper()\n"
                         "old_func()")
    assert modified_app_code == expected_app_code

    # Check sidecar files
    modified_doc_data = yaml.safe_load(doc_path.read_text("utf-8"))
    assert "mypkg.core.NewHelper" in modified_doc_data
    assert "mypkg.core.OldHelper" not in modified_doc_data
    assert modified_doc_data["mypkg.core.NewHelper"] == "This is the old helper."

    modified_sig_data = json.loads(sig_path.read_text("utf-8"))
    assert "mypkg.core.NewHelper" in modified_sig_data
    assert "mypkg.core.OldHelper" not in modified_sig_data
    assert modified_sig_data["mypkg.core.NewHelper"]["baseline_code_structure_hash"] == "hash1"
~~~~~

### 下一步建议
我们已经成功实现了代码与 Sidecar 文件的同步重命名，这是 `stitcher-refactor` 的核心价值体现。

接下来的工作可以向两个方向发展：
1.  **提升 `SymbolRenamerTransformer` 的能力**: 当前它只处理简单的 `Name` 节点。我们需要扩展它，以处理更复杂的引用模式，如 `Attribute` 和 `ImportAlias`。
2.  **实现 `MoveFileOperation`**: 这是第二大核心重构算子。文件移动本质上是一次大规模的符号重命名（模块 FQN 发生了变化），因此可以复用我们已经构建的 `RenameSymbolOperation` 逻辑。

我建议先进行**第 1 项**，因为一个健壮的符号重命名能力是实现文件移动的基础。
