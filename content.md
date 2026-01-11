## [WIP] feat: 升级 PythonAdapter 以支持文档哈希与签名文本提取

### 用户需求
为了支持“Index-First”架构，需要在索引阶段提取代码实体的原始签名文本 (`signature_text`) 和文档字符串哈希 (`docstring_hash`)。

### 评论
通过在 `PythonFingerprintStrategy` 中引入 `DocstringHasher`，我们使得“指纹计算”这一逻辑更加内聚。同时，更新 `PythonAdapter` 将这些计算出的指纹数据持久化到 `stitcher-index` 数据库中，完成了数据流的闭环。

### 目标
1.  在 `stitcher-python-adapter` 中实现 `DocstringHasher`，用于计算 `current_code_docstring_hash`。
2.  将 `DocstringHasher` 注册到 `PythonFingerprintStrategy` 中。
3.  更新 `PythonAdapter`，从计算出的指纹中提取 `signature_text` 和 `docstring_hash` 并存入 `SymbolRecord`。

### 基本原理
-   **指纹策略扩展**: 现有的指纹策略已包含结构哈希和签名文本哈希。新增文档哈希是为了支持快速的“文档脏检查”。
-   **适配器升级**: `PythonAdapter` 是连接解析器与数据库的桥梁。它负责调用策略计算指纹，并将结果映射到数据库记录模型 (`SymbolRecord`)。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/python-adapter #task/action/upgrade-extraction #task/state/continue

---

### Script

#### Acts 1: 实现 DocstringHasher 并注册

在 `fingerprint.py` 中添加 `DocstringHasher` 类，并在 `PythonFingerprintStrategy` 的初始化列表中注册它。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/fingerprint.py
~~~~~
~~~~~python.old
        parts.append(":")
        return " ".join(parts).replace("( ", "(").replace(" )", ")").replace(" :", ":")


class PythonFingerprintStrategy:
    def __init__(self):
        self.hashers: List[EntityHasher] = [
            StructureHasher(),
            SignatureTextHasher(),
            # Future: AstHasher(), MerkleHasher()
        ]

    def compute(self, entity: Union[FunctionDef, ClassDef]) -> Fingerprint:
~~~~~
~~~~~python.new
        parts.append(":")
        return " ".join(parts).replace("( ", "(").replace(" )", ")").replace(" :", ":")


class DocstringHasher:
    def update(
        self, entity: Union[FunctionDef, ClassDef], fingerprint: Fingerprint
    ) -> None:
        doc = getattr(entity, "docstring", None)
        if doc:
            h = hashlib.sha256(doc.encode("utf-8")).hexdigest()
            fingerprint["current_code_docstring_hash"] = h


class PythonFingerprintStrategy:
    def __init__(self):
        self.hashers: List[EntityHasher] = [
            StructureHasher(),
            SignatureTextHasher(),
            DocstringHasher(),
        ]

    def compute(self, entity: Union[FunctionDef, ClassDef]) -> Fingerprint:
~~~~~

#### Acts 2: 更新 PythonAdapter 提取逻辑

修改 `index_adapter.py` 中的 `_extract_symbols` 方法，提取新的指纹字段并填充到 `SymbolRecord` 中。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python.old
            canonical_fqn = f"{logical_module_fqn}.{fragment}"

            # Compute Hash
            sig_hash = None
            if entity_for_hash:
                fp = self.hasher.compute(entity_for_hash)  # type: ignore
                sig_hash = fp.get("current_code_structure_hash")

            # Location Handling
            loc = getattr(entity_for_hash, "location", None)
~~~~~
~~~~~python.new
            canonical_fqn = f"{logical_module_fqn}.{fragment}"

            # Compute Hash & Metadata
            sig_hash = None
            sig_text = None
            doc_hash = None

            if entity_for_hash:
                fp = self.hasher.compute(entity_for_hash)  # type: ignore
                sig_hash = fp.get("current_code_structure_hash")
                sig_text = fp.get("current_code_signature_text")
                doc_hash = fp.get("current_code_docstring_hash")

            # Location Handling
            loc = getattr(entity_for_hash, "location", None)
~~~~~

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python.old
                    canonical_fqn=canonical_fqn,
                    alias_target_fqn=alias_target_fqn,
                    alias_target_id=None,  # Decoupled: Linker will fill this
                    signature_hash=sig_hash,
                )
            )
            return fragment
~~~~~
~~~~~python.new
                    canonical_fqn=canonical_fqn,
                    alias_target_fqn=alias_target_fqn,
                    alias_target_id=None,  # Decoupled: Linker will fill this
                    signature_hash=sig_hash,
                    signature_text=sig_text,
                    docstring_hash=doc_hash,
                )
            )
            return fragment
~~~~~

### 下一步建议

现在 `stitcher-index` 和 `PythonAdapter` 都已升级，能够存储和提取所需的所有语义信息。接下来我们将进入 **阶段 2：基准存档与 SURI 对齐**。

下一步的具体任务是：
1.  **重构 `SignatureManager`**: 修改其序列化逻辑，将 JSON 的键（Key）从局部 `fragment` 升级为完整的 `SURI`。
2.  同时，使其支持存储新的基准字段：`baseline_code_signature_text` 和 `baseline_code_docstring_hash`。
