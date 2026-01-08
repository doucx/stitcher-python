[简要回答]
我们将通过在 `stitcher-common` 中引入一个新的 `AssetPathResolver` 服务来统一 `stitcher-application` 和 `stitcher-refactor` 中的路径解析逻辑，从而消除重复代码并确保 Sidecar 文件定位的一致性。

## [WIP] refactor: 统一资产路径解析逻辑至 AssetPathResolver

### 用户需求
用户希望将“源码 -> Sidecar (.stitcher.yaml/.json)”的映射规则集中管理。
具体要求：
1.  在 `stitcher-common` 中创建 `AssetPathResolver` 类。
2.  封装 `get_doc_path` 和 `get_signature_path` 逻辑。
3.  重构 `stitcher-application` 的 `DocumentManager` 和 `SignatureManager` 以使用该解析器。
4.  重构 `stitcher-refactor` 的 `SidecarManager` 以使用该解析器。

### 评论
这是一个典型的“消除重复代码 (DRY)”和“单一事实来源 (SSoT)”的架构改进。目前，关于 Sidecar 文件存储位置的知识散落在多个包中，这导致未来修改存储结构（例如，如果我们要将 `.stitcher/signatures` 移动到其他位置）变得困难且容易出错。将此逻辑下沉到 `stitcher-common` 是正确的架构决策。

### 目标
1.  在 `stitcher-common` 中实现 `AssetPathResolver`，使其能够健壮地处理绝对路径和相对路径。
2.  更新 `stitcher-application`，移除硬编码的路径拼接逻辑，转而委托给 `AssetPathResolver`。
3.  更新 `stitcher-refactor` 的 `SidecarManager`，使其成为 `AssetPathResolver` 的瘦包装器（保留现有接口以减少对调用方的影响）。

### 基本原理
通过提取 `AssetPathResolver`，我们将物理文件系统的布局策略与业务逻辑解耦。
`AssetPathResolver` 将能够处理：
-   **Doc Path**: 总是与源文件同级，后缀为 `.stitcher.yaml`。
-   **Sig Path**: 总是位于项目根目录下的 `.stitcher/signatures` 中，保持与源文件相同的目录结构，后缀为 `.json`。
该解析器将智能判断输入路径是绝对路径还是相对路径，并进行相应的转换，从而满足不同调用场景（CLI 运行时的相对路径 vs 重构时的绝对路径）的需求。

### 标签
#intent/refine #flow/ready #priority/medium #comp/runtime #comp/refactor #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/asset-path-resolver #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 在 `stitcher-common` 中创建 `AssetPathResolver`

首先，我们在 `stitcher-common` 包中创建一个新的 `services` 模块，并实现 `AssetPathResolver` 类。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-common/src/stitcher/common/services
touch packages/stitcher-common/src/stitcher/common/services/__init__.py
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/services/asset_path_resolver.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Union


class AssetPathResolver:
    """
    Centralized resolver for Stitcher asset paths (Sidecars and Signatures).
    
    This class encapsulates the logic for mapping a source code file to its
    corresponding documentation sidecar (.stitcher.yaml) and signature file (.json).
    """

    def __init__(self, root_path: Path):
        self.root_path = root_path.resolve()
        self.sig_root = self.root_path / ".stitcher" / "signatures"

    def get_doc_path(self, source_path: Union[str, Path]) -> Path:
        """
        Returns the path to the documentation sidecar (.stitcher.yaml).
        The doc sidecar sits right next to the source file.
        """
        path = Path(source_path)
        return path.with_suffix(".stitcher.yaml")

    def get_signature_path(self, source_path: Union[str, Path]) -> Path:
        """
        Returns the path to the signature sidecar (.json).
        The signature sidecar sits in .stitcher/signatures/, mirroring the source tree.
        """
        path = Path(source_path)
        
        # If path is absolute, make it relative to root
        if path.is_absolute():
            try:
                # Resolve strictly to handle symlinks or .. components if necessary
                # though usually source_path comes from trusted traversal
                rel_path = path.resolve().relative_to(self.root_path)
            except ValueError:
                # If the path is absolute but not inside root_path, 
                # we can't map it to the internal signature store structure.
                raise ValueError(
                    f"Source path {path} is not within the project root {self.root_path}"
                )
        else:
            rel_path = path

        return self.sig_root / rel_path.with_suffix(".json")
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/services/asset_path_resolver.stitcher.yaml
~~~~~
~~~~~yaml
"AssetPathResolver": |-
  Centralized service for resolving paths to Stitcher assets (docs and signatures).
  Ensures consistent mapping between source files and their sidecars across the system.
"AssetPathResolver.get_doc_path": |-
  Resolves the path to the documentation sidecar (.stitcher.yaml).
  Strategy: Colocated with source file.
"AssetPathResolver.get_signature_path": |-
  Resolves the path to the signature file (.json).
  Strategy: Mirrored structure inside .stitcher/signatures/.
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/services/__init__.py
~~~~~
~~~~~python
from .asset_path_resolver import AssetPathResolver

__all__ = ["AssetPathResolver"]
~~~~~

#### Acts 2: 重构 `stitcher-application` 的 `DocumentManager`

我们将修改 `DocumentManager`，使其在内部使用 `AssetPathResolver`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
from stitcher.common import DocumentAdapter, YamlAdapter
from stitcher.adapter.python import RawDocstringParser, RawSerializer


class DocumentManager:
    def __init__(self, root_path: Path, adapter: Optional[DocumentAdapter] = None):
        self.root_path = root_path
        self.adapter = adapter or YamlAdapter()
        # Defaults to Raw mode for backward compatibility
        self.parser: DocstringParserProtocol = RawDocstringParser()
        self.serializer: DocstringSerializerProtocol = RawSerializer()

    def set_strategy(
~~~~~
~~~~~python.new
from stitcher.common import DocumentAdapter, YamlAdapter
from stitcher.adapter.python import RawDocstringParser, RawSerializer
from stitcher.common.services import AssetPathResolver


class DocumentManager:
    def __init__(self, root_path: Path, adapter: Optional[DocumentAdapter] = None):
        self.root_path = root_path
        self.adapter = adapter or YamlAdapter()
        self.resolver = AssetPathResolver(root_path)
        # Defaults to Raw mode for backward compatibility
        self.parser: DocstringParserProtocol = RawDocstringParser()
        self.serializer: DocstringSerializerProtocol = RawSerializer()

    def set_strategy(
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
    def save_docs_for_module(self, module: ModuleDef) -> Path:
        ir_map = self.flatten_module_docs(module)
        if not ir_map:
            return Path("")

        # Convert IRs to YAML-ready data (str or dict)
        yaml_data = {fqn: self._serialize_ir(ir) for fqn, ir in ir_map.items()}

        module_path = self.root_path / module.file_path
        output_path = module_path.with_suffix(".stitcher.yaml")
        self.adapter.save(output_path, yaml_data)
        return output_path

    def load_docs_for_module(self, module: ModuleDef) -> Dict[str, DocstringIR]:
        if not module.file_path:
            return {}
        module_path = self.root_path / module.file_path
        doc_path = module_path.with_suffix(".stitcher.yaml")

        raw_data = self.adapter.load(doc_path)  # returns Dict[str, Any] now ideally

        # Adapter.load is typed to return Dict[str, str], but YamlAdapter actually returns parsed YAML.
~~~~~
~~~~~python.new
    def save_docs_for_module(self, module: ModuleDef) -> Path:
        ir_map = self.flatten_module_docs(module)
        if not ir_map:
            return Path("")

        # Convert IRs to YAML-ready data (str or dict)
        yaml_data = {fqn: self._serialize_ir(ir) for fqn, ir in ir_map.items()}

        module_path = self.root_path / module.file_path
        output_path = self.resolver.get_doc_path(module_path)
        self.adapter.save(output_path, yaml_data)
        return output_path

    def load_docs_for_module(self, module: ModuleDef) -> Dict[str, DocstringIR]:
        if not module.file_path:
            return {}
        module_path = self.root_path / module.file_path
        doc_path = self.resolver.get_doc_path(module_path)

        raw_data = self.adapter.load(doc_path)  # returns Dict[str, Any] now ideally

        # Adapter.load is typed to return Dict[str, str], but YamlAdapter actually returns parsed YAML.
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
    def compute_yaml_content_hashes(self, module: ModuleDef) -> Dict[str, str]:
        # We need raw data here to compute the hash exactly as it is stored
        # But load_docs_for_module returns IRs.
        # We should load raw data directly from adapter for hashing.

        if not module.file_path:
            return {}
        module_path = self.root_path / module.file_path
        doc_path = module_path.with_suffix(".stitcher.yaml")

        # Load raw dict from YAML
        raw_data = self.adapter.load(doc_path)
~~~~~
~~~~~python.new
    def compute_yaml_content_hashes(self, module: ModuleDef) -> Dict[str, str]:
        # We need raw data here to compute the hash exactly as it is stored
        # But load_docs_for_module returns IRs.
        # We should load raw data directly from adapter for hashing.

        if not module.file_path:
            return {}
        module_path = self.root_path / module.file_path
        doc_path = self.resolver.get_doc_path(module_path)

        # Load raw dict from YAML
        raw_data = self.adapter.load(doc_path)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
    def reformat_docs_for_module(self, module: ModuleDef) -> bool:
        if not module.file_path:
            return False
        module_path = self.root_path / module.file_path
        doc_path = module_path.with_suffix(".stitcher.yaml")
        if not doc_path.exists():
            return False

        # Load raw to preserve everything, then deserialize->serialize to apply formatting rules
~~~~~
~~~~~python.new
    def reformat_docs_for_module(self, module: ModuleDef) -> bool:
        if not module.file_path:
            return False
        module_path = self.root_path / module.file_path
        doc_path = self.resolver.get_doc_path(module_path)
        if not doc_path.exists():
            return False

        # Load raw to preserve everything, then deserialize->serialize to apply formatting rules
~~~~~

#### Acts 3: 重构 `stitcher-application` 的 `SignatureManager`

同样地，我们将修改 `SignatureManager` 以使用 `AssetPathResolver`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    ModuleDef,
    Fingerprint,
    InvalidFingerprintKeyError,
    FingerprintStrategyProtocol,
)


class SignatureManager:
    def __init__(
        self, root_path: Path, fingerprint_strategy: FingerprintStrategyProtocol
    ):
        self.root_path = root_path
        self.sig_root = root_path / ".stitcher" / "signatures"
        self.fingerprint_strategy = fingerprint_strategy

    def get_sig_path(self, module: ModuleDef) -> Path:
        rel_path = Path(module.file_path)
        return self.sig_root / rel_path.with_suffix(".json")

    def compute_fingerprints(self, module: ModuleDef) -> Dict[str, Fingerprint]:
~~~~~
~~~~~python.new
from stitcher.spec import (
    ModuleDef,
    Fingerprint,
    InvalidFingerprintKeyError,
    FingerprintStrategyProtocol,
)
from stitcher.common.services import AssetPathResolver


class SignatureManager:
    def __init__(
        self, root_path: Path, fingerprint_strategy: FingerprintStrategyProtocol
    ):
        self.root_path = root_path
        self.resolver = AssetPathResolver(root_path)
        self.fingerprint_strategy = fingerprint_strategy

    def get_sig_path(self, module: ModuleDef) -> Path:
        return self.resolver.get_signature_path(module.file_path)

    def compute_fingerprints(self, module: ModuleDef) -> Dict[str, Fingerprint]:
~~~~~

#### Acts 4: 重构 `stitcher-refactor` 的 `SidecarManager`

最后，我们将 `SidecarManager` 重构为 `AssetPathResolver` 的瘦代理。这样可以保持 `SidecarManager` 在 `stitcher-refactor` 中的上下文意义，同时复用核心逻辑。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/sidecar/manager.py
~~~~~
~~~~~python.old
from pathlib import Path


class SidecarManager:
    def __init__(self, root_path: Path):
        self.root_path = root_path.resolve()
        self.sig_root = self.root_path / ".stitcher" / "signatures"

    def get_doc_path(self, source_file_path: Path) -> Path:
        return source_file_path.resolve().with_suffix(".stitcher.yaml")

    def get_signature_path(self, source_file_path: Path) -> Path:
        resolved_source = source_file_path.resolve()
        # This encapsulates the complex relative path logic
        try:
            relative_source_path = resolved_source.relative_to(self.root_path)
            return self.sig_root / relative_source_path.with_suffix(".json")
        except ValueError:
            # This can happen if source_file_path is not within root_path.
            # While unlikely in normal operation, it's safer to handle.
            # We'll re-raise a more informative error.
            raise ValueError(
                f"Source file {resolved_source} is not within the project root {self.root_path}"
            )
~~~~~
~~~~~python.new
from pathlib import Path
from stitcher.common.services import AssetPathResolver


class SidecarManager:
    def __init__(self, root_path: Path):
        self.resolver = AssetPathResolver(root_path)

    def get_doc_path(self, source_file_path: Path) -> Path:
        return self.resolver.get_doc_path(source_file_path)

    def get_signature_path(self, source_file_path: Path) -> Path:
        return self.resolver.get_signature_path(source_file_path)
~~~~~

### 下一步建议
我们已经完成了核心路径解析逻辑的统一。接下来，我们应该运行测试套件（特别是 `stitcher-application` 和 `stitcher-refactor` 的测试），以确保重构没有破坏现有的文件定位逻辑。特别是要关注涉及嵌套目录和相对路径处理的测试用例。
