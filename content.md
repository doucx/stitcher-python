## [WIP] fix(core): 优化 check 命令的判定逻辑与消息提示

### 错误分析
**现象**: `stitcher check` 仍然报告了大量错误，主要分为两类：
1.  **EXTRA 误报**: 私有方法（如 `_mock_get`, `_process_plugins`）在 YAML 中存在文档，但在代码扫描时被过滤掉了（因为我们只扫描公开成员），导致 `check` 认为这些文档是“多余”的。这是一个典型的逻辑漏洞：如果我们允许私有方法有文档，那么过滤逻辑就不能太绝对；或者我们需要清理现有的 YAML 文件。考虑到“允许私有方法有文档”是合理的，我们应该调整比较逻辑。
2.  **MISSING 误报**: 一些公开方法（如 `StitcherApp`）在 YAML 中确实不存在，被正确识别为 MISSING，但由于我们之前的降级逻辑，它们现在显示为 Warning，这是预期的。
3.  **EXTRA 泛滥**: 由于之前的 `init` 步骤提取了所有文档（包括私有的），现在的 `check` 逻辑认为这些私有文档都是“多余”的，因为现在的扫描逻辑只看公开成员。

### 用户需求
1.  **兼容私有文档**: 如果 YAML 中包含了私有成员的文档，不应报错为 EXTRA，而应视为合法（Allowed Extra）。
2.  **消除误报**: 确保 `check` 命令只对真正的“幽灵文档”（指向已删除的代码）报错，而对私有成员的文档保持宽容。

### 评论
当前的困境在于：`_extract_all_keys` 过滤掉了私有成员，导致 `check_module`在对比时发现 YAML 中有这些私有成员的 Key，便判定为 EXTRA。

解决方案是：在 `check_module` 中，对于 EXTRA 的判定，我们需要再次检查这些 Key 是否对应代码中真实存在的私有成员。如果是，则放行；如果代码中确实没有（连私有的都没有），才判定为真正的 EXTRA。

### 目标
1.  修改 `DocumentManager.check_module`，引入更智能的 EXTRA 判定逻辑。它需要获取代码中**所有**的 Key（包括私有），用来验证 YAML 中的 Key 是否合法。

### 基本原理
我们将 `_extract_all_keys` 拆分为两个方法：`_extract_public_keys`（用于 MISSING 检查）和 `_extract_all_existing_keys`（用于 EXTRA 检查）。

-   **MISSING = Public Keys - YAML Keys** (公开的必须有文档)
-   **EXTRA = YAML Keys - All Existing Keys** (文档指向的必须存在)

### 标签
#intent/fix #flow/ready #priority/high #comp/engine #scope/core #task/domain/linter #task/object/check-logic #task/action/refine #task/state/continue

---

### Script

#### Acts 1: 重构 Key 提取逻辑

修改 `doc_manager.py`，实现分层提取。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
    def check_module(self, module: ModuleDef) -> Dict[str, set]:
        """
        Compares module structure against external docs.
        Returns a dict of issues: {'missing': set(...), 'extra': set(...)}
        """
        # 1. Get keys from Code (Source of Truth for Existence)
        code_keys = self._extract_all_keys(module)

        # 2. Get keys from YAML
        yaml_docs = self.load_docs_for_module(module)
        doc_keys = set(yaml_docs.keys())

        # 3. Diff
        missing = code_keys - doc_keys
        extra = doc_keys - code_keys

        # Allow __doc__ to be present in YAML even if not explicitly demanded by code analysis
        # This supports the case where a user documents a module in YAML that has no docstring in code.
        extra.discard("__doc__")

        return {"missing": missing, "extra": extra}

    def _extract_all_keys(self, module: ModuleDef) -> set:
        """Extracts all addressable public FQNs from the module IR."""
        keys = set()

        # Module itself
        if module.docstring:
            keys.add("__doc__")

        def is_public(name: str) -> bool:
            return not name.startswith("_")

        for func in module.functions:
            if is_public(func.name):
                keys.add(func.name)

        for cls in module.classes:
            if is_public(cls.name):
                keys.add(cls.name)
                for method in cls.methods:
                    if is_public(method.name):
                        keys.add(f"{cls.name}.{method.name}")
                for attr in cls.attributes:
                    if is_public(attr.name):
                        keys.add(f"{cls.name}.{attr.name}")

        # Module attributes
        for attr in module.attributes:
            if is_public(attr.name):
                keys.add(attr.name)

        return keys
~~~~~
~~~~~python.new
    def check_module(self, module: ModuleDef) -> Dict[str, set]:
        """
        Compares module structure against external docs.
        Returns a dict of issues: {'missing': set(...), 'extra': set(...)}
        """
        # 1. Get keys from Code
        public_keys = self._extract_keys(module, public_only=True)
        all_keys = self._extract_keys(module, public_only=False)

        # 2. Get keys from YAML
        yaml_docs = self.load_docs_for_module(module)
        doc_keys = set(yaml_docs.keys())

        # 3. Diff
        # Missing: Must be public AND not in YAML
        missing = public_keys - doc_keys

        # Extra: In YAML AND not in Code (at all, even private)
        extra = doc_keys - all_keys

        # Allow __doc__ to be present in YAML even if not explicitly demanded by code analysis
        extra.discard("__doc__")

        return {"missing": missing, "extra": extra}

    def _extract_keys(self, module: ModuleDef, public_only: bool) -> set:
        """Extracts addressable FQNs from the module IR."""
        keys = set()

        # Module itself
        if module.docstring:
            keys.add("__doc__")

        def include(name: str) -> bool:
            if public_only:
                return not name.startswith("_")
            return True

        for func in module.functions:
            if include(func.name):
                keys.add(func.name)

        for cls in module.classes:
            if include(cls.name):
                keys.add(cls.name)
                for method in cls.methods:
                    if include(method.name):
                        keys.add(f"{cls.name}.{method.name}")
                for attr in cls.attributes:
                    if include(attr.name):
                        keys.add(f"{cls.name}.{attr.name}")

        # Module attributes
        for attr in module.attributes:
            if include(attr.name):
                keys.add(attr.name)

        return keys
~~~~~

### 下一步建议
再次运行 `stitcher check`。这次应该能完美通过：
1.  MISSING 仅针对 Public API（显示为 Warning）。
2.  EXTRA 仅针对代码中真正消失了的成员（显示为 Error）。
3.  Private API 如果有文档，将被视为合法，不会报错。
