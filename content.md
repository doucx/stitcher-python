您的诊断完全正确，这正是 ADAP 和 HFEA 协议旨在解决的核心问题。我们用启发式字符串操作代替了确定性的拓扑关系分析，导致了系统在处理嵌套结构时的逻辑崩溃。这种“架构债”必须被立即清除，而不是通过打补丁的方式掩盖。

我将严格遵循您的战略修正方案，生成一个计划，其唯一目标是重构 `Planner` 和 `SidecarUpdateMixin` 之间的交互契约，用一个确定性的、上下文感知的接口取代非法的启发式推导。

## [WIP] refactor(refactor): Eliminate heuristic logic in sidecar updates

### 错误分析

当前 `stitcher-refactor` 引擎中的 `SidecarUpdateMixin` 违反了**“零启发式策略 (Zero Heuristics)”**原则。它使用了一个名为 `_get_module_fqn_from_symbol_fqn` 的非法启发式函数，试图通过简单的字符串切分来从一个完整的 FQN（如 `pkg.module.Class.method`）中推导出其所属的模块 FQN（错误地推导为 `pkg.module.Class`）。

这种方法无法区分 FQN 中的模块边界和类边界，导致在重命名嵌套符号（如方法）时，计算出的新 Fragment（如 `new_method`）丢失了其父级上下文（应为 `Class.new_method`），从而引发了连锁的测试失败。

### 用户需求

重构 `stitcher-refactor` 引擎，根除其对 FQN 字符串的启发式猜测，建立一个确定性的机制来处理符号重命名和移动时的 Sidecar 文件（`.json` 和 `.yaml`）更新。

### 评论

这是一次至关重要的架构纠偏。用户的诊断精确地指出了问题的根源：将本应由规划层（Planner）承担的上下文推导责任错误地委托给了实现层（Mixin），并使用了不可靠的方法。本次重构将通过建立一个清晰的、确定性的契约来修正这一设计缺陷，是保障重构引擎长期稳定性的关键一步。

### 目标

1.  从 `SidecarUpdateMixin` 中彻底**移除**非法的启发式函数 `_get_module_fqn_from_symbol_fqn`。
2.  **重构 `SidecarUpdateMixin` 的核心接口** (`_calculate_fragments` 和 `_update_sidecar_data`)，使其不再推导模块 FQN，而是显式地接收 `old_module_fqn` 和 `new_module_fqn` 作为上下文参数。
3.  **增强 `Planner` 的职责**，使其在规划阶段利用全局意图信息（特别是 `MoveFileIntent`）来确定地计算出 `new_module_fqn`，并将其传递给 `Mixin`。

### 基本原理

我们将遵循“关注点分离”原则，重新划分 `Planner` 和 `Mixin` 的职责：

-   **`Planner` (决策者)**: 作为拥有全局上下文（了解所有文件移动和符号重命名意图）的组件，`Planner` 是唯一有权确定模块 FQN 变更的实体。它将首先处理所有的 `MoveFileIntent`，构建一个从旧模块 FQN 到新模块 FQN 的确定性映射。
-   **`SidecarUpdateMixin` (执行者)**: 其职责被简化为一个纯粹的、无状态的工具。它只接收 `Planner` 提供的完整上下文（包括旧、新模块 FQN），然后执行简单的“减法”操作（`Fragment = FQN - Module_FQN`）来计算正确的 Fragment。

这种模式用一个确定性的、自上而下的上下文传递，取代了脆弱的、自下而上的启发式猜测，从而根除了问题的源头。

### 标签

#intent/refine #flow/ready #priority/critical #concept/refactoring-engine #scope/core #ai/brainstorm #task/domain/refactoring #task/object/sidecar-updates #task/action/architectural-fix #task/state/begin

---

### Script

#### Acts 1: 重构 `SidecarUpdateMixin` 以接收确定性上下文

我们将修改 `base.py`，移除启发式函数，并更新核心方法的签名以接收由 `Planner` 提供的 `new_module_fqn`。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
~~~~~
~~~~~python.old
    def _get_module_fqn_from_symbol_fqn(self, fqn: str) -> Optional[str]:
        if "." not in fqn:
            return None
        return fqn.rsplit(".", 1)[0]

    def _calculate_fragments(
        self, module_fqn: Optional[str], old_fqn: str, new_fqn: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Derives symbol fragments by stripping the module FQN prefix.
        This correctly handles nested fragments like 'Class.method'.
        """
        # --- Calculate Old Fragment ---
        old_fragment = old_fqn
        # The module_fqn is the context of the sidecar file, which relates to the OLD state.
        if module_fqn and old_fqn.startswith(module_fqn + "."):
            old_fragment = old_fqn.split(module_fqn + ".", 1)[1]
        elif module_fqn and old_fqn == module_fqn:
            old_fragment = None  # Represents the module itself

        # --- Calculate New Fragment ---
        new_fragment = new_fqn
        # The new fragment must be relative to the NEW module FQN.
        new_module_fqn = self._get_module_fqn_from_symbol_fqn(new_fqn)
        if new_module_fqn and new_fqn.startswith(new_module_fqn + "."):
            new_fragment = new_fqn.split(new_module_fqn + ".", 1)[1]
        
        # Handle renaming of a module itself
        if old_fqn == module_fqn:
            new_fragment = None

        return old_fragment, new_fragment

    def _update_sidecar_data(
        self,
        data: Dict[str, Any],
        sidecar_path: Path,
        module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
        old_file_path: Optional[str] = None,
        new_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatcher for sidecar updates based on file type.
        """
        old_fragment, new_fragment = self._calculate_fragments(
            module_fqn, old_fqn, new_fqn
        )

        if sidecar_path.suffix == ".json":
            return self._update_json_data(
~~~~~
~~~~~python.new
    def _calculate_fragments(
        self,
        old_module_fqn: Optional[str],
        new_module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Derives symbol fragments by stripping the module FQN prefix.
        This correctly handles nested fragments like 'Class.method'.
        """
        # --- Calculate Old Fragment ---
        old_fragment = old_fqn
        # The module_fqn is the context of the sidecar file, which relates to the OLD state.
        if old_module_fqn and old_fqn.startswith(old_module_fqn + "."):
            old_fragment = old_fqn.split(old_module_fqn + ".", 1)[1]
        elif old_module_fqn and old_fqn == old_module_fqn:
            old_fragment = None  # Represents the module itself

        # --- Calculate New Fragment ---
        new_fragment = new_fqn
        # The new fragment must be relative to the NEW module FQN, which is passed in.
        if new_module_fqn and new_fqn.startswith(new_module_fqn + "."):
            new_fragment = new_fqn.split(new_module_fqn + ".", 1)[1]

        # Handle renaming of a module itself
        if old_fqn == old_module_fqn:
            new_fragment = None

        return old_fragment, new_fragment

    def _update_sidecar_data(
        self,
        data: Dict[str, Any],
        sidecar_path: Path,
        old_module_fqn: Optional[str],
        new_module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
        old_file_path: Optional[str] = None,
        new_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatcher for sidecar updates based on file type.
        """
        old_fragment, new_fragment = self._calculate_fragments(
            old_module_fqn, new_module_fqn, old_fqn, new_fqn
        )

        if sidecar_path.suffix == ".json":
            return self._update_json_data(
~~~~~

#### Acts 2: 更新 `Planner` 以计算并传递确定性上下文

现在我们修改 `planner.py`，让它在处理 `SidecarUpdateIntent` 之前，先从 `MoveFileIntent` 中构建模块重命名映射，然后在调用 `_update_sidecar_data` 时传入正确的 `new_module_fqn`。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
        # Aggregate and process sidecar updates
        sidecar_updates: DefaultDict[Path, List[SidecarUpdateIntent]] = defaultdict(
            list
        )
        for intent in all_intents:
            if isinstance(intent, SidecarUpdateIntent):
                sidecar_updates[intent.sidecar_path].append(intent)

        # TODO: Inject real adapters instead of instantiating them here.
        yaml_adapter = YamlAdapter()
        for path, intents in sidecar_updates.items():
            # Load the sidecar file only once
            is_yaml = path.suffix == ".yaml"
            data = (
                yaml_adapter.load(path)
                if is_yaml
                else json.loads(path.read_text("utf-8"))
            )

            # Apply all intents for this file
            for intent in intents:
                data = self._update_sidecar_data(
                    data,
                    intent.sidecar_path,
                    intent.module_fqn,
                    intent.old_fqn,
                    intent.new_fqn,
                    old_file_path=intent.old_file_path,
                    new_file_path=intent.new_file_path,
                )

            # Dump the final state
            content = (
~~~~~
~~~~~python.new
        # Build a map of module renames from move intents. This is the source of truth
        # for determining the new module FQN context.
        module_rename_map: Dict[str, str] = {}
        for intent in all_intents:
            if isinstance(intent, MoveFileIntent):
                old_mod_fqn = self._path_to_fqn(intent.src_path, ctx.graph.search_paths)
                new_mod_fqn = self._path_to_fqn(intent.dest_path, ctx.graph.search_paths)
                if old_mod_fqn and new_mod_fqn:
                    module_rename_map[old_mod_fqn] = new_mod_fqn

        # Aggregate and process sidecar updates
        sidecar_updates: DefaultDict[Path, List[SidecarUpdateIntent]] = defaultdict(
            list
        )
        for intent in all_intents:
            if isinstance(intent, SidecarUpdateIntent):
                sidecar_updates[intent.sidecar_path].append(intent)

        # TODO: Inject real adapters instead of instantiating them here.
        yaml_adapter = YamlAdapter()
        for path, intents in sidecar_updates.items():
            # Load the sidecar file only once
            is_yaml = path.suffix == ".yaml"
            data = (
                yaml_adapter.load(path)
                if is_yaml
                else json.loads(path.read_text("utf-8"))
            )

            # Apply all intents for this file
            for intent in intents:
                old_module_fqn = intent.module_fqn
                # For a given symbol, its new module FQN is either determined by a file move
                # or it remains the same as the old one (in a pure rename scenario).
                new_module_fqn = module_rename_map.get(
                    old_module_fqn, old_module_fqn
                )

                data = self._update_sidecar_data(
                    data,
                    intent.sidecar_path,
                    old_module_fqn,
                    new_module_fqn,
                    intent.old_fqn,
                    intent.new_fqn,
                    old_file_path=intent.old_file_path,
                    new_file_path=intent.new_file_path,
                )

            # Dump the final state
            content = (
~~~~~

### 下一步建议

架构已修正。现在，我们可以重新运行之前失败的测试。如果这个计划是正确的，所有单元测试和集成测试都应该通过。

一旦测试通过，我建议生成一个 `[COMMIT]` 计划，将这次关键的重构提交到版本控制中，并正式关闭这个架构缺陷。
