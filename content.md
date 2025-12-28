好的，收到指令。我将根据《架构公理：哈希强制长命名规范》对代码库进行审查，并生成一个重构计划以修正所有不符合规范的命名。

经过审查，我发现 `stitcher-application` 的核心状态机逻辑 (`core.py`) 及其相关的服务和测试，在处理哈希时使用了 `code_structure_hash` 和 `yaml_content_hash` 等短命名，这严重违反了公理。这些短命名造成了“来源”和“状态”的歧义，是必须被消除的“概念性债务”。

我将生成一个计划，通过 `patch_file` 操作，将这些不合规的变量和字典键重构为完全自文档化的长命名（例如 `baseline_code_structure_hash`），并同步更新所有依赖这些名称的测试代码，以确保系统的健壮性和可维护性。

## [WIP] refactor: 强制执行哈希变量长命名规范

### 用户需求
严格遵循《架构公理：哈希强制长命名规范》，审查并重构代码库中所有与哈希相关的变量命名和数据结构键名。

### 评论
这是一项至关重要的架构维护任务。公理正确地指出了使用短命名（如 `s_current`, `doc_hash`）会积累巨大的“概念性债务”，增加认知负荷并可能引发难以调试的逻辑错误。

本次重构将彻底消除这种歧义，特别是使 `StitcherApp._analyze_file` 中的核心状态机逻辑变得完全自文档化，极大地提升了代码的可读性和长期可维护性。

### 目标
1.  **统一数据契约**: 修改存储在 `.stitcher/signatures/*.json` 文件中的数据结构，使其键名严格遵循 `[Source]_[Object]_[State]_hash` 规范（例如，使用 `baseline_code_structure_hash`）。
2.  **重构核心逻辑**: 更新 `stitcher.app.core.py` 中负责状态比较的核心逻辑，使其在内部使用符合规范的长命名变量，并能正确读写新的数据结构。
3.  **同步更新测试**: 修改所有依赖于旧哈希键名和变量名的测试用例，确保整个测试套件在重构后能够完全通过，验证重构的正确性。

### 基本原理
本次重构的核心是将在物理磁盘上持久化的哈希数据结构（`.json` 文件）视为核心“契约”。通过修改这个契约的键名，我们能够自上而下地强制所有与该数据结构交互的代码（主要是 `core.py` 中的 `run_init` 和 `_analyze_file` 方法）进行相应的调整。

我们将使用 `patch_file` 指令精确地替换所有不合规的变量名和字典键。同时，更新单元测试（`test_signature_manager.py`）和集成测试（`test_check_state_machine.py`）是验证此次重构是否成功的关键闭环。

### 标签
#intent/refine #flow/ready #priority/high #comp/engine #concept/state #scope/core #scope/dx #ai/instruct #task/domain/refactoring #task/object/naming-convention #task/action/enforcement #task/state/begin

---
### Script

#### Acts 1: 更新核心应用逻辑以遵循命名规范

首先，我们将修改 `stitcher.app.core.py`。这是最关键的一步，我们将重命名 `_analyze_file` 方法中所有与哈希相关的变量和字典键，并更新 `run_init` 方法中创建哈希记录的逻辑。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
                code_hashes = self.sig_manager.compute_code_structure_hashes(module)
                yaml_hashes = self.doc_manager.compute_yaml_content_hashes(module)
                combined = {}
                all_fqns = set(code_hashes.keys()) | set(yaml_hashes.keys())
                for fqn in all_fqns:
                    combined[fqn] = {
                        "code_structure_hash": code_hashes.get(fqn),
                        "yaml_content_hash": yaml_hashes.get(fqn),
                    }
                self.sig_manager.save_composite_hashes(module, combined)
                if output_path and output_path.name:
~~~~~
~~~~~python.new
                code_hashes = self.sig_manager.compute_code_structure_hashes(module)
                yaml_hashes = self.doc_manager.compute_yaml_content_hashes(module)
                combined = {}
                all_fqns = set(code_hashes.keys()) | set(yaml_hashes.keys())
                for fqn in all_fqns:
                    combined[fqn] = {
                        "baseline_code_structure_hash": code_hashes.get(fqn),
                        "baseline_yaml_content_hash": yaml_hashes.get(fqn),
                    }
                self.sig_manager.save_composite_hashes(module, combined)
                if output_path and output_path.name:
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        current_code_structure_map = self.sig_manager.compute_code_structure_hashes(module)
        current_yaml_content_map = self.doc_manager.compute_yaml_content_hashes(module)
        stored_hashes_map = self.sig_manager.load_composite_hashes(module)
        new_hashes_map = stored_hashes_map.copy()

        all_fqns = set(current_code_structure_map.keys()) | set(stored_hashes_map.keys())

        for fqn in sorted(list(all_fqns)):
            current_code_structure_hash = current_code_structure_map.get(fqn)
            current_yaml_content_hash = current_yaml_content_map.get(fqn)
            stored = stored_hashes_map.get(fqn, {})
            stored_code_structure_hash = stored.get("code_structure_hash")
            stored_yaml_content_hash = stored.get("yaml_content_hash")

            # Case: Extra (In Storage, Not in Code)
            if not current_code_structure_hash and stored_code_structure_hash:
                if fqn in new_hashes_map:
                    new_hashes_map.pop(fqn, None)
                continue

            # Case: New (In Code, Not in Storage)
            if current_code_structure_hash and not stored_code_structure_hash:
                if is_tracked:
                    new_hashes_map[fqn] = {
                        "code_structure_hash": current_code_structure_hash,
                        "yaml_content_hash": current_yaml_content_hash,
                    }
                continue

            # Case: Existing
            code_structure_matches = current_code_structure_hash == stored_code_structure_hash
            yaml_content_matches = current_yaml_content_hash == stored_yaml_content_hash

            if code_structure_matches and yaml_content_matches:
                pass  # Synchronized
            elif code_structure_matches and not yaml_content_matches:
                # Doc Improvement: INFO, Auto-reconcile
                result.infos["doc_improvement"].append(fqn)
                if fqn in new_hashes_map:
                    new_hashes_map[fqn]["yaml_content_hash"] = current_yaml_content_hash
                result.auto_reconciled_count += 1
            elif not code_structure_matches and yaml_content_matches:
                # Signature Drift
                if force_relink:
                    result.reconciled["force_relink"].append(fqn)
                    if fqn in new_hashes_map:
                        new_hashes_map[fqn]["code_structure_hash"] = current_code_structure_hash
                else:
                    result.errors["signature_drift"].append(fqn)
            elif not code_structure_matches and not yaml_content_matches:
                # Co-evolution
                if reconcile:
                    result.reconciled["reconcile"].append(fqn)
                    new_hashes_map[fqn] = {
                        "code_structure_hash": current_code_structure_hash,
                        "yaml_content_hash": current_yaml_content_hash,
                    }
                else:
                    result.errors["co_evolution"].append(fqn)
~~~~~
~~~~~python.new
        current_code_structure_map = self.sig_manager.compute_code_structure_hashes(module)
        current_yaml_content_map = self.doc_manager.compute_yaml_content_hashes(module)
        stored_hashes_map = self.sig_manager.load_composite_hashes(module)
        new_hashes_map = stored_hashes_map.copy()

        all_fqns = set(current_code_structure_map.keys()) | set(stored_hashes_map.keys())

        for fqn in sorted(list(all_fqns)):
            current_code_structure_hash = current_code_structure_map.get(fqn)
            current_yaml_content_hash = current_yaml_content_map.get(fqn)
            stored = stored_hashes_map.get(fqn, {})
            baseline_code_structure_hash = stored.get("baseline_code_structure_hash")
            baseline_yaml_content_hash = stored.get("baseline_yaml_content_hash")

            # Case: Extra (In Storage, Not in Code)
            if not current_code_structure_hash and baseline_code_structure_hash:
                if fqn in new_hashes_map:
                    new_hashes_map.pop(fqn, None)
                continue

            # Case: New (In Code, Not in Storage)
            if current_code_structure_hash and not baseline_code_structure_hash:
                if is_tracked:
                    new_hashes_map[fqn] = {
                        "baseline_code_structure_hash": current_code_structure_hash,
                        "baseline_yaml_content_hash": current_yaml_content_hash,
                    }
                continue

            # Case: Existing
            code_structure_matches = current_code_structure_hash == baseline_code_structure_hash
            yaml_content_matches = current_yaml_content_hash == baseline_yaml_content_hash

            if code_structure_matches and yaml_content_matches:
                pass  # Synchronized
            elif code_structure_matches and not yaml_content_matches:
                # Doc Improvement: INFO, Auto-reconcile
                result.infos["doc_improvement"].append(fqn)
                if fqn in new_hashes_map:
                    new_hashes_map[fqn]["baseline_yaml_content_hash"] = current_yaml_content_hash
                result.auto_reconciled_count += 1
            elif not code_structure_matches and yaml_content_matches:
                # Signature Drift
                if force_relink:
                    result.reconciled["force_relink"].append(fqn)
                    if fqn in new_hashes_map:
                        new_hashes_map[fqn]["baseline_code_structure_hash"] = current_code_structure_hash
                else:
                    result.errors["signature_drift"].append(fqn)
            elif not code_structure_matches and not yaml_content_matches:
                # Co-evolution
                if reconcile:
                    result.reconciled["reconcile"].append(fqn)
                    new_hashes_map[fqn] = {
                        "baseline_code_structure_hash": current_code_structure_hash,
                        "baseline_yaml_content_hash": current_yaml_content_hash,
                    }
                else:
                    result.errors["co_evolution"].append(fqn)
~~~~~

#### Acts 2: 更新 Signature Manager 的文档

我们将更新 `signature_manager.py` 中 `save_composite_hashes` 的文档字符串，使其明确声明新的数据契约。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python.old
    def save_composite_hashes(self, module: ModuleDef, hashes: Dict[str, Any]) -> None:
        """
        Saves the composite hash map for a module.
        Expected format: { "FQN": { "code_structure_hash": "...", "yaml_content_hash": "..." } }
        """
        if not hashes:
            sig_path = self._get_sig_path(module)
~~~~~
~~~~~python.new
    def save_composite_hashes(self, module: ModuleDef, hashes: Dict[str, Any]) -> None:
        """
        Saves the composite hash map for a module.
        Expected format: { "FQN": { "baseline_code_structure_hash": "...", "baseline_yaml_content_hash": "..." } }
        """
        if not hashes:
            sig_path = self._get_sig_path(module)
~~~~~

#### Acts 3: 更新相关测试用例

最后，我们将更新 `test_signature_manager.py` 和 `test_check_state_machine.py` 中的测试数据和断言，以匹配新的哈希键名，确保测试套件通过。

~~~~~act
patch_file
packages/stitcher-application/tests/test_signature_manager.py
~~~~~
~~~~~python.old
def test_manager_save_and_load_composite_hashes(tmp_path: Path):
    # Arrange
    manager = SignatureManager(root_path=tmp_path)
    module = ModuleDef(file_path="src/main.py", functions=[create_func(name="foo")])

    hashes_to_save = {
        "foo": {"code_structure_hash": "abc", "yaml_content_hash": "def"},
        "bar": {"code_structure_hash": "123", "yaml_content_hash": None},
    }

    # Act: Save
    manager.save_composite_hashes(module, hashes_to_save)

    # Assert: File exists and has correct structure
    sig_path = tmp_path / ".stitcher/signatures/src/main.json"
    assert sig_path.exists()

    with sig_path.open("r") as f:
        data = json.load(f)
        assert data["foo"]["code_structure_hash"] == "abc"
        assert data["foo"]["yaml_content_hash"] == "def"
        assert data["bar"]["code_structure_hash"] == "123"
        assert data["bar"]["yaml_content_hash"] is None

    # Act: Load
    loaded = manager.load_composite_hashes(module)
    assert loaded == hashes_to_save
~~~~~
~~~~~python.new
def test_manager_save_and_load_composite_hashes(tmp_path: Path):
    # Arrange
    manager = SignatureManager(root_path=tmp_path)
    module = ModuleDef(file_path="src/main.py", functions=[create_func(name="foo")])

    hashes_to_save = {
        "foo": {"baseline_code_structure_hash": "abc", "baseline_yaml_content_hash": "def"},
        "bar": {"baseline_code_structure_hash": "123", "baseline_yaml_content_hash": None},
    }

    # Act: Save
    manager.save_composite_hashes(module, hashes_to_save)

    # Assert: File exists and has correct structure
    sig_path = tmp_path / ".stitcher/signatures/src/main.json"
    assert sig_path.exists()

    with sig_path.open("r") as f:
        data = json.load(f)
        assert data["foo"]["baseline_code_structure_hash"] == "abc"
        assert data["foo"]["baseline_yaml_content_hash"] == "def"
        assert data["bar"]["baseline_code_structure_hash"] == "123"
        assert data["bar"]["baseline_yaml_content_hash"] is None

    # Act: Load
    loaded = manager.load_composite_hashes(module)
    assert loaded == hashes_to_save
~~~~~
~~~~~act
patch_file
tests/integration/test_check_state_machine.py
~~~~~
~~~~~python.old
    spy_bus.assert_id_called(L.check.state.doc_updated, level="info")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["code_structure_hash"] == initial_hashes["func"]["code_structure_hash"]
    
    expected_hash = app.doc_manager.compute_yaml_content_hash(new_doc_content)
    assert final_hashes["func"]["yaml_content_hash"] == expected_hash
~~~~~
~~~~~python.new
    spy_bus.assert_id_called(L.check.state.doc_updated, level="info")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["baseline_code_structure_hash"] == initial_hashes["func"]["baseline_code_structure_hash"]
    
    expected_hash = app.doc_manager.compute_yaml_content_hash(new_doc_content)
    assert final_hashes["func"]["baseline_yaml_content_hash"] == expected_hash
~~~~~
~~~~~act
patch_file
tests/integration/test_check_state_machine.py
~~~~~
~~~~~python.old
    spy_bus.assert_id_called(L.check.state.relinked, level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    
    assert final_hashes["func"]["code_structure_hash"] != initial_hashes["func"]["code_structure_hash"]
    assert final_hashes["func"]["yaml_content_hash"] == initial_hashes["func"]["yaml_content_hash"]
~~~~~
~~~~~python.new
    spy_bus.assert_id_called(L.check.state.relinked, level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    
    assert final_hashes["func"]["baseline_code_structure_hash"] != initial_hashes["func"]["baseline_code_structure_hash"]
    assert final_hashes["func"]["baseline_yaml_content_hash"] == initial_hashes["func"]["baseline_yaml_content_hash"]
~~~~~
~~~~~act
patch_file
tests/integration/test_check_state_machine.py
~~~~~
~~~~~python.old
    spy_bus.assert_id_called(L.check.state.reconciled, level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["code_structure_hash"] != initial_hashes["func"]["code_structure_hash"]
    assert final_hashes["func"]["yaml_content_hash"] != initial_hashes["func"]["yaml_content_hash"]
    
    expected_doc_hash = app.doc_manager.compute_yaml_content_hash(new_doc_content)
    assert final_hashes["func"]["yaml_content_hash"] == expected_doc_hash
~~~~~
~~~~~python.new
    spy_bus.assert_id_called(L.check.state.reconciled, level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["baseline_code_structure_hash"] != initial_hashes["func"]["baseline_code_structure_hash"]
    assert final_hashes["func"]["baseline_yaml_content_hash"] != initial_hashes["func"]["baseline_yaml_content_hash"]
    
    expected_doc_hash = app.doc_manager.compute_yaml_content_hash(new_doc_content)
    assert final_hashes["func"]["baseline_yaml_content_hash"] == expected_doc_hash
~~~~~

### 下一步建议
我们已经完成了对核心逻辑和相关测试的修改。下一步，我建议创建一个 `[COMMIT]` 计划来提交这些变更。这将把本次重构作为一个独立的、原子化的工作单元记录在版本历史中。
