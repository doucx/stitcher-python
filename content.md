检测到“确定性缺失”违例：否。
用户提供了明确的错误日志和代码上下文，架构重构方案是基于确定的性能瓶颈分析和设计原则制定的。

### [WIP] refactor: 分离文档序列化协议并修复 Sidecar 索引一致性

### 错误分析
1.  **Hash 不一致 (`assert success is True` 失败)**:
    *   `stitcher check` 的核心逻辑是对比 `symbols.docstring_hash` (代码现状) 和 `doc_entries.content_hash` (文档索引)。
    *   当前 `RawSerializer.to_yaml_object` 返回字符串（为了兼容 `ruamel.yaml`），但在索引路径中，如果不经转换直接计算哈希，或者使用了不同的 JSON 序列化参数，会导致与运行时计算的哈希值不一致。
    *   这种不一致导致即使内容未变，系统也会误判为“Conflict”。

2.  **FK Constraint Failed**:
    *   日志显示 `Failed to parse ...: FOREIGN KEY constraint failed`。这表明在 `FileIndexer` 试图往 `doc_entries` 表插入数据时，引用的 `file_id` 无效。
    *   虽然 `IndexStore.sync_file` 应该先创建文件记录，但在事务边界处理不当的情况下（尤其是在 `ensure_index_fresh` 的大事务中），可能会导致此问题。不过，解决 Hash 一致性是首要任务。

3.  **不稳定性**:
    *   测试失败数量的波动（11 -> 15）通常暗示了非确定性的哈希计算（例如字典序问题）或数据库状态污染。我们将通过强制 JSON 序列化时的 `sort_keys=True` 来消除哈希的不确定性。

### 用户需求
修复因架构重构导致的测试套件崩溃，确保 `check` 命令能正确、稳定地工作。

### 目标
1.  **重构协议**: 将 `DocstringSerializerProtocol` 拆分为“面向存储(DTO)”和“面向文件(Presentation)”两个明确的契约。
2.  **统一哈希源**: 确保无论是写入数据库索引，还是在运行时计算对比哈希，都统一使用 DTO 产生的规范化 JSON。
3.  **修复实现**: 更新 `RawSerializer` 和 `SidecarAdapter` 以遵循新协议。

### 基本原理
通过强制分离 DTO 和 Presentation，我们建立了一个“真理层”（DTO）：
*   **DTO (Data Transfer Object)**: 纯字典，无格式信息，key排序。这是哈希计算和数据库存储的唯一依据。
*   **Presentation**: 包含 `ruamel.yaml` 特殊对象（如 `LiteralScalarString`），仅用于文件读写，不参与逻辑比对。

### 标签
#intent/refine #flow/ready #priority/critical #comp/interfaces #comp/runtime #concept/state #task/domain/storage #task/object/sidecar-index #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 重构序列化协议定义

明确区分 DTO 转换和 YAML 对象转换。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/protocols.py
~~~~~
~~~~~python.old
class DocstringSerializerProtocol(Protocol):
    # For data transfer, hashing, and database storage (must be JSON-safe and deterministic)
    def to_serializable_dict(self, ir: DocstringIR) -> Dict[str, Any]: ...
    def from_serializable_dict(self, data: Dict[str, Any]) -> DocstringIR: ...

    # For high-fidelity writing to .yaml files (may contain format-specific objects)
    def to_yaml_object(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]: ...
    def from_yaml_object(self, data: Union[str, Dict[str, Any]]) -> DocstringIR: ...
~~~~~
~~~~~python.new
class DocstringSerializerProtocol(Protocol):
    # For data transfer, hashing, and database storage (must be JSON-safe and deterministic)
    def to_serializable_dict(self, ir: DocstringIR) -> Dict[str, Any]: ...
    def from_serializable_dict(self, data: Dict[str, Any]) -> DocstringIR: ...

    # For high-fidelity writing to .yaml files (may contain format-specific objects like LiteralScalarString)
    # The return type allows str for Raw mode, or Dict for structured modes.
    def to_yaml_object(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]: ...
    
    # Reconstructing IR from loaded YAML data (which might be str or dict)
    def from_yaml_object(self, data: Union[str, Dict[str, Any]]) -> DocstringIR: ...
~~~~~

#### Acts 2: 更新 Serializer 实现

重写 `RawSerializer` 以严格遵循新语义：`to_serializable_dict` 必须返回字典。

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/docstring/serializers.py
~~~~~
~~~~~python.old
class RawSerializer(BaseSerializer):
    def to_yaml_object(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        summary = ir.summary or ""
        if ir.addons:
            data = {"Raw": summary}
            data.update(ir.addons)
            return data
        return summary

    def from_yaml_object(self, data: Union[str, Dict[str, Any]]) -> DocstringIR:
        if isinstance(data, str):
            return DocstringIR(summary=data)

        ir = DocstringIR()
        if isinstance(data, dict):
            ir.summary = data.get("Raw", "")
            ir.addons = self._extract_addons(data)
        return ir

    def to_serializable_dict(self, ir: DocstringIR) -> Dict[str, Any]:
        dto: Dict[str, Any] = {"summary": ir.summary or ""}
        if ir.addons:
            dto["addons"] = ir.addons
        return dto

    def from_serializable_dict(self, data: Dict[str, Any]) -> DocstringIR:
        return DocstringIR(
            summary=data.get("summary", ""),
            addons=data.get("addons", {}),
        )
~~~~~
~~~~~python.new
class RawSerializer(BaseSerializer):
    def to_yaml_object(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        # For YAML file: prefer raw string if no addons, for readability.
        summary = ir.summary or ""
        if ir.addons:
            data = {"Raw": summary}
            data.update(ir.addons)
            return data
        return summary

    def from_yaml_object(self, data: Union[str, Dict[str, Any]]) -> DocstringIR:
        # From YAML file: handle both raw string and dict (if addons exist)
        if isinstance(data, str):
            return DocstringIR(summary=data)

        ir = DocstringIR()
        if isinstance(data, dict):
            # Support both "Raw" key and implicit summary from dict if structure changed? 
            # Ideally Raw mode dictates a schema.
            ir.summary = data.get("Raw", "")
            ir.addons = self._extract_addons(data)
        return ir

    def to_serializable_dict(self, ir: DocstringIR) -> Dict[str, Any]:
        # For DB/Hash: MUST be a dict to be distinct and extensible.
        dto: Dict[str, Any] = {"summary": ir.summary or ""}
        if ir.addons:
            dto["addons"] = ir.addons
        return dto

    def from_serializable_dict(self, data: Dict[str, Any]) -> DocstringIR:
        # From DB/Hash: Assume it's always the dict structure we defined above.
        return DocstringIR(
            summary=data.get("summary", ""),
            addons=data.get("addons", {}),
        )
~~~~~

#### Acts 3: 修正 DocumentManager 的哈希计算

这是修复“运行时哈希不匹配”的关键点。

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/manager.py
~~~~~
~~~~~python.old
    def _serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        return self._sidecar_adapter.serialize_ir(ir, self.serializer)

    def _deserialize_ir(self, data: Union[str, Dict[str, Any]]) -> DocstringIR:
        return self.serializer.from_yaml_object(data)

    def serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        return self._serialize_ir(ir)

    def compute_ir_hash(self, ir: DocstringIR) -> str:
        serialized = self._serialize_ir(ir)
        return self.compute_yaml_content_hash(serialized)
~~~~~
~~~~~python.new
    def _serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        # Default behavior for file writing: use YAML object
        return self._sidecar_adapter.serialize_ir(ir, self.serializer)

    def _deserialize_ir(self, data: Union[str, Dict[str, Any]]) -> DocstringIR:
        return self.serializer.from_yaml_object(data)

    def serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        return self._serialize_ir(ir)

    def compute_ir_hash(self, ir: DocstringIR) -> str:
        # CRITICAL FIX: Use the DTO serializer for hashing to ensure consistency
        # between Runtime (here) and Indexer (SidecarAdapter.parse)
        dto = self.serializer.to_serializable_dict(ir)
        return self.compute_yaml_content_hash(dto)
~~~~~

#### Acts 4: 修正 SidecarAdapter 的索引解析逻辑

这是修复“数据库哈希不匹配”的关键点。确保索引器写入 DB 的是经过 `sort_keys=True` 且基于 DTO 的 JSON。

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
~~~~~
~~~~~python.old
                # Full parsing for DocEntryRecord creation
                data = self._yaml.load(content)
                # Use RawSerializer as a default for the indexing path
                serializer = RawSerializer()

                if isinstance(data, dict):
                    for fragment, raw_ir_obj in data.items():
                        # 1. Determine location (line/col) from ruamel
                        lineno = 0
                        lc = getattr(data, "lc", None)
                        if lc and hasattr(lc, "item"):
                            pos = lc.item(fragment)
                            if pos:
                                lineno = pos[0] + 1

                        # 2. Generate SURI for the symbol
                        suri = self.uri_generator.generate_symbol_uri(
                            rel_py_path, str(fragment)
                        )

                        try:
                            # 3. Normalize to IR, then to a JSON-safe DTO
                            ir = serializer.from_yaml_object(raw_ir_obj)
                            ir_dict = serializer.to_serializable_dict(ir)
                            ir_json = json.dumps(ir_dict, sort_keys=True)

                            # 4. Compute deterministic hash from the JSON string
                            content_hash = hashlib.sha256(
                                ir_json.encode("utf-8")
                            ).hexdigest()

                            # 5. Create the DocEntryRecord for the indexer
~~~~~
~~~~~python.new
                # Full parsing for DocEntryRecord creation
                data = self._yaml.load(content)
                # Use RawSerializer as a default for the indexing path.
                # TODO: Ideally this should come from config, but for now Raw is safe default.
                serializer = RawSerializer()

                if isinstance(data, dict):
                    for fragment, raw_ir_obj in data.items():
                        # 1. Determine location (line/col) from ruamel
                        lineno = 0
                        lc = getattr(data, "lc", None)
                        if lc and hasattr(lc, "item"):
                            pos = lc.item(fragment)
                            if pos:
                                lineno = pos[0] + 1

                        # 2. Generate SURI for the symbol
                        suri = self.uri_generator.generate_symbol_uri(
                            rel_py_path, str(fragment)
                        )

                        try:
                            # 3. Normalize to IR, then to a JSON-safe DTO
                            # This uses from_yaml_object because raw_ir_obj comes from ruamel.yaml.load
                            ir = serializer.from_yaml_object(raw_ir_obj)
                            
                            # Convert to DTO for storage and hashing
                            ir_dict = serializer.to_serializable_dict(ir)
                            
                            # Ensure deterministic JSON
                            ir_json = json.dumps(ir_dict, sort_keys=True, ensure_ascii=False)

                            # 4. Compute deterministic hash from the JSON string
                            content_hash = hashlib.sha256(
                                ir_json.encode("utf-8")
                            ).hexdigest()

                            # 5. Create the DocEntryRecord for the indexer
~~~~~

### 下一步建议
运行 `pytest packages/stitcher-application/tests/integration/test_check_command.py` 验证 Hash 一致性是否修复。如果 FK 错误持续，可能需要检查测试夹具中文件的创建顺序。
