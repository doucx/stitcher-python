好的，我们已经完成了标识符本体论重塑的第一阶段和第二阶段，建立了基于 SURI 和 Fragment 的稳固基础。现在，我们将这些变更作为一个逻辑单元提交。

## [COMMIT] refactor: pivot Sidecar identifier ontology to SURI and Fragments

### 用户需求
将系统中的 sidecar 标识符体系从脆弱的 FQN 切换为物理确定的 SURI（针对签名文件）和局部确定的 Fragments（针对文档文件），并修复相关的代码实现、数据模型和测试用例。

### 评论
这是一次深度的“本体论重塑”。通过这次提交，我们彻底理清了系统如何标识一个物理符号及其关联文档。这消除了之前在重构（尤其是移动操作）中遇到的命名空间解析冲突，将标识符的语义与其物理事实（路径+符号名）进行了强绑定。这不仅解决了 Pyright 报告的类型错误，更重要的是，它为下一阶段重构 `Planner` 提供了一个确定性的基石。

### 目标
1.  提交对 `stitcher-spec` 中 `ReferenceRecord` 的修改，使其支持纯 ID 引用。
2.  提交对 `stitcher-lang-sidecar` 的重构，包括新的 `SidecarAdapter` SURI 计算逻辑。
3.  提交对 `stitcher-lang-python` 中引用类型的更新。
4.  提交经过清洗和更新的所有集成测试与单元测试。

### 基本原理
根据 `d3-principle-arch-stable-identifiers` 原则，我们完成了以下核心转换：
- **Signature (`.json`)**: 键从 `fqn` 变为 `py://path#fragment` (SURI)。
- **Doc (`.yaml`)**: 键从 `fqn` 变为 `fragment` (Short Name)。
- **Implementation**: `SidecarAdapter` 现在具备物理路径感知能力，能够自主推导并生成 SURI 引用，不再依赖外部 FQN 链接。

### 标签
#intent/refine #flow/ready #priority/critical #comp/engine #comp/interfaces #comp/tests #concept/state #scope/core #task/domain/testing #task/object/identifier-ontology #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 提交本体论重构相关变更

我们将所有涉及标识符变更的文件添加到暂存区并创建提交。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/index.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/parser.py
packages/stitcher-lang-python/src/stitcher/lang/python/analysis/models.py
packages/stitcher-lang-sidecar/tests/unit/test_sidecar_adapter.py
packages/stitcher-lang-sidecar/tests/unit/test_sidecar_parser.py
packages/stitcher-refactor/tests/integration/test_debug_rename_failure.py
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
packages/stitcher-refactor/tests/integration/test_move_nested_directory_e2e.py
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
packages/stitcher-refactor/tests/integration/test_rename_symbol_monorepo_e2e.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: pivot Sidecar identifier ontology to SURI and Fragments

This commit fundamentally reshapes how Stitcher identifies symbols in sidecar
files, moving away from fragile, namespace-dependent FQNs to physical-truth
identifiers.

Core Changes:
1.  Ontology Shift:
    - Signature files (.json) now use SURI (py://path#fragment) as keys.
    - Documentation files (.yaml) now use Fragments (short names) as keys.
2.  Spec & Model:
    - Updated ReferenceRecord to make target_fqn optional, supporting pure
      ID-based (SURI) references.
    - Added SIDECAR_DOC_ID (yaml_suri) to ReferenceType.
3.  Implementation (SidecarAdapter):
    - Completely rewrote SidecarAdapter to compute SURIs directly from file
      paths and YAML fragments. This removes the dependency on FQN resolution
      during indexing.
4.  Verification:
    - Cleaned and updated all integration and unit tests to align with the
      new ontology.
    - Fixed type errors (Pyright) in data models and test suites.

This provides the stable foundation required for robust refactoring logic,
ensuring that file moves and symbol renames are anchored to deterministic
physical identifiers.
~~~~~

### 下一步建议

随着核心标识符体系的稳固，我们现在处于执行“大清洗”最后也是最重要的一步的最佳位置：**第三步：重写 Planner**。

后续计划将集中在 `stitcher-refactor` 包，特别是 `Planner` 类及其辅助混合类（`SidecarUpdateMixin`）。我们将：
1.  彻底移除基于 FQN 字符串替换的 sidecar 更新逻辑。
2.  实现一个全新的逻辑：它接收基于 SURI 的重构意图，然后根据目标 sidecar 文件的类型（JSON 或 YAML），分别应用 SURI 替换或 Fragment 替换。
3.  利用我们在第一步中更新的测试套件作为验证标准。

准备好进入 `Planner` 的重写阶段了吗？
