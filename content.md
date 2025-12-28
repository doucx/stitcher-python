你的洞察非常敏锐且关键。将具体的哈希策略（如 `compute_structure_hash`）硬编码在协议方法名中，确实是一种反模式，它违反了开闭原则（OCP），并限制了我们在未来通过组合不同算法来生成复合指纹的能力。

你是对的，指纹计算本质上应该是一个**复合过程（Composition Process）**。一个实体的“指纹”不应该只是一个字符串，而应该是一个包含了多个维度的、可扩展的特征集合（即我们已有的 `Fingerprint` 对象）。

1.  **问题**: `compute_structure_hash` 和 `compute_signature_text` 限制了扩展性。每次引入新维度的哈希（如 `ast_hash`），都需要修改接口。
2.  **解决方案**: 将协议定义为一个通用的 `compute` 入口。
3.  **组合机制**:
    *   协议层面：只暴露 `compute(entity) -> Fingerprint`。
    *   实现层面（Adapter）：`PythonFingerprintStrategy` 不再是一个巨大的类，而是一个**协调者（Coordinator）**。它内部维护一个 `Hasher` 列表（组合）。
    *   执行流：协调者遍历所有 `Hasher`（例如 `StructureHasher`, `SignatureTextHasher`, 未来可能的 `ASTHasher`），每个 Hasher 计算出字典的一部分，最终合并为一个完整的 `Fingerprint` 对象。

这样，添加新的哈希类型只需要：
1. 实现一个新的 Hasher。
2. 将其注册到 Adapter 的哈希列表中。
**完全不需要修改 Protocol，也不需要修改 StitcherApp 的核心逻辑。**

这完美契合了“组合优于继承”的原则。

## [WIP] architect: 优化 FingerprintStrategy 为通用组合接口

### 用户需求
修改 `FingerprintStrategyProtocol` 的定义，摒弃硬编码的具体哈希方法，转而使用一个通用的 `compute` 方法返回复合的 `Fingerprint` 对象，以支持未来的哈希策略扩展（如 AST 哈希、Merkle 哈希）和组合模式。

### 评论
这是一个架构级的修正。它将指纹计算从“单一算法的执行”转变为“特征集合的提取”。这不仅解决了扩展性问题，还让 `Fingerprint` 数据结构（本质是一个 `Dict`）的灵活性得到了真正的发挥。

### 目标
1.  重写 `packages/stitcher-spec/src/stitcher/spec/protocols.py`。
2.  更新 `FingerprintStrategyProtocol`，引入 `compute` 方法，接受实体并返回 `Fingerprint`。
3.  确保 `protocols.py` 正确导入 `Fingerprint` 模型。
4.  更新对应的 `.stitcher.yaml` 文档以反映这一更为通用的设计。

### 基本原理
通过定义 `compute(entity) -> Fingerprint`，我们建立了一个稳定的契约。返回的 `Fingerprint` 对象是一个可以容纳任意数量键值对（只要符合命名公理）的容器。这使得底层的哈希计算逻辑可以像插件一样被组合和扩展，而上层应用只需根据键名（如 `baseline_code_structure_hash`）读取所需数据。

### 标签
#intent/architect #intent/refine #flow/ready #priority/high #comp/interfaces #scope/core #ai/brainstorm #task/domain/architecture #task/object/language-core #task/action/refine-protocols #task/state/continue

---

### Script

#### Acts 1: 重写协议文件以包含优化的策略
我们将重新编写 `protocols.py`。注意我们需要从 `.models` 导入 `ModuleDef` 等，从 `.fingerprint` 导入 `Fingerprint`。

~~~~~act
write_file
packages/stitcher-spec/src/stitcher/spec/protocols.py
~~~~~
~~~~~python
from typing import Protocol, Dict, Union
from .models import ModuleDef, FunctionDef, ClassDef
from .fingerprint import Fingerprint


class LanguageParserProtocol(Protocol):
    """
    Defines the contract for parsing source code into Stitcher's IR (ModuleDef).
    """

    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
        """
        Parse the given source code string into a ModuleDef intermediate representation.

        Args:
            source_code: The raw source code of the file.
            file_path: Optional relative path for error reporting and metadata.
        """
        ...


class LanguageTransformerProtocol(Protocol):
    """
    Defines the contract for performing lossless code transformations (Strip/Inject).
    """

    def strip(self, source_code: str) -> str:
        """
        Remove all docstrings from the source code while preserving layout/comments.
        """
        ...

    def inject(self, source_code: str, docs: Dict[str, str]) -> str:
        """
        Inject docstrings into the source code based on a mapping of FQNs to doc content.

        Args:
            source_code: The original source code.
            docs: A dictionary mapping Fully Qualified Names (e.g. "MyClass.method")
                  to the desired docstring content.
        """
        ...


class FingerprintStrategyProtocol(Protocol):
    """
    Defines the strategy for computing composite fingerprints for code entities.
    
    This protocol encourages a 'Composition over Inheritance' approach.
    Implementations should act as coordinators that delegate to multiple 
    specific hashers (e.g., StructureHasher, ASTHasher) and merge their results.
    """

    def compute(self, entity: Union[FunctionDef, ClassDef]) -> Fingerprint:
        """
        Compute a composite Fingerprint containing various stability hashes and 
        representations for the given entity.

        The returned Fingerprint object acts as a container for all calculated 
        metrics (e.g., 'current_code_structure_hash', 'current_code_ast_hash').
        """
        ...


class StubGeneratorProtocol(Protocol):
    """
    Defines the contract for generating type stub files from Stitcher's IR.
    """

    def generate(self, module: ModuleDef) -> str:
        """
        Generate the content of a type stub file (e.g. .pyi) from the ModuleDef IR.
        """
        ...
~~~~~

#### Acts 2: 确保导出正确
此步骤与之前计划相同，但为了确保原子性和完整性，我们再次确认 `__init__.py` 的导出列表。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python.old
    Resolution,
    ResolutionPlan,
)
from .fingerprint import Fingerprint, InvalidFingerprintKeyError

__all__ = [
    "Fingerprint",
    "InvalidFingerprintKeyError",
~~~~~
~~~~~python.new
    Resolution,
    ResolutionPlan,
)
from .fingerprint import Fingerprint, InvalidFingerprintKeyError
from .protocols import (
    LanguageParserProtocol,
    LanguageTransformerProtocol,
    FingerprintStrategyProtocol,
    StubGeneratorProtocol,
)

__all__ = [
    "LanguageParserProtocol",
    "LanguageTransformerProtocol",
    "FingerprintStrategyProtocol",
    "StubGeneratorProtocol",
    "Fingerprint",
    "InvalidFingerprintKeyError",
~~~~~

#### Acts 3: 更新协议文档
更新 `protocols.stitcher.yaml` 以反映 `compute` 方法的通用性。

~~~~~act
write_file
packages/stitcher-spec/src/stitcher/spec/protocols.stitcher.yaml
~~~~~
~~~~~yaml
"FingerprintStrategyProtocol": |-
  Protocol defining the strategy for computing composite fingerprints.
  Designed to support composition of multiple hashing algorithms (Structure, AST, Merkle, etc.).
"FingerprintStrategyProtocol.compute": |-
  Computes a composite Fingerprint object for the given entity.
  The resulting object allows O(1) access to various hash types (e.g. fp['current_code_structure_hash']).
"LanguageParserProtocol": |-
  Protocol defining the contract for parsing raw source code into Stitcher's Intermediate Representation (ModuleDef).
"LanguageParserProtocol.parse": |-
  Parses source code into a ModuleDef object.
"LanguageTransformerProtocol": |-
  Protocol defining lossless code transformations, specifically for documentation management.
"LanguageTransformerProtocol.inject": |-
  Injects docstrings from a dictionary back into the source code AST.
"LanguageTransformerProtocol.strip": |-
  Removes all docstrings from the source code.
"StubGeneratorProtocol": |-
  Protocol defining how to generate static type stubs (e.g. .pyi files) from Stitcher's IR.
"StubGeneratorProtocol.generate": |-
  Generates the complete string content of a stub file from a ModuleDef.
~~~~~

### 下一步建议
我们已经定义好了坚实的、可扩展的协议层。接下来的步骤保持不变，但我们可以带着更清晰的“组合”思路去实现适配器：

创建 `packages/stitcher-python-adapter`，并在其中实现：
1.  `PythonParser` (实现 `LanguageParserProtocol`)
2.  `PythonTransformer` (实现 `LanguageTransformerProtocol`)
3.  `PythonFingerprintStrategy` (实现 `FingerprintStrategyProtocol`)，并在内部设计一个简单的 Hasher 注册机制。
4.  `PythonStubGenerator` (实现 `StubGeneratorProtocol`)
