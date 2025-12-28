## [WIP] build: 创建 stitcher-python-adapter 并实现核心策略

### 用户需求
创建 `stitcher-python-adapter` 包，并实现 `stitcher-spec` 中定义的四大核心协议。特别地，需要设计并实现一个基于组合模式的 `PythonFingerprintStrategy`，以支持未来哈希算法的灵活扩展。

### 评论
我们采取“先封装，后迁移”的策略。为了避免在架构切换期间破坏现有系统，新的 Adapter 将暂时作为现有 `stitcher-scanner` 和 `stitcher-io` 逻辑的“薄层封装（Wrapper）”。待 `StitcherApp` 完成依赖注入的改造后，我们将执行物理代码迁移。
对于 `FingerprintStrategy`，我们将从 `FunctionDef` 中剥离指纹计算逻辑，重构为独立的 `Hasher` 组件。

### 目标
1.  建立 `packages/stitcher-python-adapter` 的包结构和构建配置。
2.  实现 `PythonParser`, `PythonTransformer`, `PythonStubGenerator`，它们暂时代理现有逻辑。
3.  **核心重点**: 实现 `PythonFingerprintStrategy`，包含 `StructureHasher` 和 `SignatureTextHasher`，并支持通过列表组合更多 Hasher。

### 基本原理
-   **组合优于继承**: `PythonFingerprintStrategy` 不包含具体的哈希逻辑，而是作为 Coordinator 遍历 `hashers` 列表。这使得添加 `AstHasher` 或 `MerkleHasher` 变得极其简单且无需修改核心代码。
-   **平滑演进**: 通过 Wrapper 模式，我们可以在不破坏现有 import 路径的情况下构建新架构，降低了重构风险。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #scope/core #ai/instruct #task/domain/architecture #task/object/language-adapter #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 初始化包结构与配置
创建包目录和 `pyproject.toml`。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-python-adapter/src/stitcher/adapter/python
~~~~~

~~~~~act
write_file
packages/stitcher-python-adapter/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-python-adapter"
version = "0.1.0"
description = "Python language adapter for Stitcher, implementing core protocols."
requires-python = ">=3.10"
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-scanner", # Temporary dependency for wrapping
    "stitcher-io",      # Temporary dependency for wrapping
    "libcst",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-scanner = { workspace = true }
stitcher-io = { workspace = true }
~~~~~

#### Acts 2: 实现指纹策略 (组合模式)
这是本次的核心创新点。我们将逻辑从 DTO 中剥离，放入 Hasher 中。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/fingerprint.py
~~~~~
~~~~~python
import hashlib
from typing import Protocol, List, Union, Dict
from stitcher.spec import FunctionDef, ClassDef, Fingerprint, ArgumentKind

class EntityHasher(Protocol):
    """Protocol for individual hashing strategies."""
    def update(self, entity: Union[FunctionDef, ClassDef], fingerprint: Fingerprint) -> None:
        """Calculate specific hashes and update the fingerprint object."""
        ...

class StructureHasher:
    """Computes the structural hash (signature shape) of a function."""
    
    def update(self, entity: Union[FunctionDef, ClassDef], fingerprint: Fingerprint) -> None:
        if isinstance(entity, FunctionDef):
            h = self._compute_func_hash(entity)
            fingerprint["current_code_structure_hash"] = h
        elif isinstance(entity, ClassDef):
            # Class-level structure hash logic can be added here if needed in future.
            # Currently Stitcher focuses on methods.
            pass

    def _compute_func_hash(self, func: FunctionDef) -> str:
        # Extracted from stitcher.spec.models.FunctionDef.compute_fingerprint
        parts = [
            f"name:{func.name}",
            f"async:{func.is_async}",
            f"static:{func.is_static}",
            f"class:{func.is_class}",
            f"ret:{func.return_annotation or ''}",
        ]

        for arg in func.args:
            arg_sig = (
                f"{arg.name}:{arg.kind}:{arg.annotation or ''}:{arg.default or ''}"
            )
            parts.append(arg_sig)

        sig_str = "|".join(parts)
        return hashlib.sha256(sig_str.encode("utf-8")).hexdigest()

class SignatureTextHasher:
    """Generates the human-readable signature text for diffing."""

    def update(self, entity: Union[FunctionDef, ClassDef], fingerprint: Fingerprint) -> None:
        if isinstance(entity, FunctionDef):
            text = self._get_signature_string(entity)
            fingerprint["current_code_signature_text"] = text
    
    def _get_signature_string(self, func: FunctionDef) -> str:
        # Extracted from stitcher.spec.models.FunctionDef.get_signature_string
        parts = []
        if func.is_async:
            parts.append("async")
        parts.append("def")
        parts.append(f"{func.name}(")

        arg_strs = []
        for arg in func.args:
            s = arg.name
            if arg.kind == ArgumentKind.VAR_POSITIONAL:
                s = f"*{arg.name}"
            elif arg.kind == ArgumentKind.VAR_KEYWORD:
                s = f"**{arg.name}"

            if arg.annotation:
                s += f": {arg.annotation}"
            if arg.default:
                s += f" = {arg.default}"
            arg_strs.append(s)

        parts.append(", ".join(arg_strs))
        parts.append(")")

        if func.return_annotation:
            parts.append(f"-> {func.return_annotation}")

        parts.append(":")
        return " ".join(parts).replace("( ", "(").replace(" )", ")").replace(" :", ":")

class PythonFingerprintStrategy:
    """
    Coordinator that delegates to a list of composable Hashers.
    """
    def __init__(self):
        self.hashers: List[EntityHasher] = [
            StructureHasher(),
            SignatureTextHasher(),
            # Future: AstHasher(), MerkleHasher()
        ]

    def compute(self, entity: Union[FunctionDef, ClassDef]) -> Fingerprint:
        fp = Fingerprint()
        for hasher in self.hashers:
            hasher.update(entity, fp)
        return fp
~~~~~

#### Acts 3: 实现 Parser (Wrapper)
暂时封装 `stitcher.scanner`。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/parser.py
~~~~~
~~~~~python
from stitcher.spec import ModuleDef
from stitcher.scanner import parse_source_code

class PythonParser:
    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
        return parse_source_code(source_code, file_path)
~~~~~

#### Acts 4: 实现 Transformer (Wrapper)
暂时封装 `stitcher.scanner`。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/transformer.py
~~~~~
~~~~~python
from typing import Dict
from stitcher.scanner import strip_docstrings, inject_docstrings

class PythonTransformer:
    def strip(self, source_code: str) -> str:
        return strip_docstrings(source_code)

    def inject(self, source_code: str, docs: Dict[str, str]) -> str:
        return inject_docstrings(source_code, docs)
~~~~~

#### Acts 5: 实现 Generator (Wrapper)
暂时封装 `stitcher.io`。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/generator.py
~~~~~
~~~~~python
from stitcher.spec import ModuleDef
from stitcher.io import StubGenerator

class PythonStubGenerator:
    def __init__(self):
        self._delegate = StubGenerator()

    def generate(self, module: ModuleDef) -> str:
        return self._delegate.generate(module)
~~~~~

#### Acts 6: 导出与文档
完成包的封装。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py
~~~~~
~~~~~python
from .parser import PythonParser
from .transformer import PythonTransformer
from .generator import PythonStubGenerator
from .fingerprint import PythonFingerprintStrategy

__all__ = [
    "PythonParser",
    "PythonTransformer",
    "PythonStubGenerator",
    "PythonFingerprintStrategy",
]
~~~~~

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.stitcher.yaml
~~~~~
~~~~~yaml
"PythonFingerprintStrategy": |-
  Strategy for computing fingerprints for Python entities.
  Uses a composite approach (StructureHasher + SignatureTextHasher).
"PythonParser": |-
  Adapter for parsing Python source code into Stitcher IR.
"PythonStubGenerator": |-
  Adapter for generating Python type stubs (.pyi).
"PythonTransformer": |-
  Adapter for transforming Python source code (strip/inject docstrings).
~~~~~

### 下一步建议
我们已经完成了 Adapter 的构建。下一步，我们需要修改 `StitcherApp` 以支持依赖注入，并在 CLI 层（组合根）实例化这些新的 Python 适配器，传入 `StitcherApp`，从而完成架构的切换。切换验证无误后，我们将着手清理 `stitcher-spec` 中的冗余逻辑和旧的 scanner/io 代码。
