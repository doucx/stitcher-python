这里有一个修复 `doc_manager.py` 中 `__doc__` 键处理逻辑的计划。

## [WIP] fix: 修复 `check` 命令因缺失模块文档字符串而误报的问题

### 错误分析
测试 `test_generate_updates_signatures` 失败的原因是 `StitcherApp.run_check()` 返回了 `False`，这表明它在检查过程中发现了“不一致”。

深入分析 `doc_manager.py` 的逻辑发现：
1.  **现有逻辑**: `_extract_all_keys` 方法无条件地将 `__doc__` 添加到 `code_keys` 集合中（即认为所有模块*必须*有文档字符串）。
2.  **测试场景**: 测试用例中动态创建的 `src/main.py` 没有模块级文档字符串（Module Docstring），且生成的 YAML 文件中也没有 `__doc__` 键。
3.  **冲突**: `check` 命令对比发现 `code_keys` 包含 `__doc__` 但 YAML 中没有，因此报告 `MISSING: __doc__`，导致检查失败。
4.  **矛盾**: `init` 命令（依赖 `flatten_module_docs`）仅在源码存在文档字符串时才生成 YAML 条目。这意味着 `init` 刚刚初始化完一个没有文档字符串的模块，紧接着运行 `check` 就会失败。这是不合理的行为。

### 用户需求
用户需要 `check` 命令能够正确通过 `tests/integration/test_check_signatures.py` 中的测试，确保存根生成 (`generate`) 后签名基线被正确更新，且不会因为模块缺少文档字符串而报错。

### 评论
这是一个典型的“隐式假设”导致的 Bug。我们不能假设所有模块都有文档字符串，也不能强制要求 YAML 中必须包含它（除非源码中就有）。同时，我们也要允许用户在 YAML 中为源码中没有文档字符串的模块添加文档（即“幽灵文档”），而不能将其标记为 Extra。

### 目标
修改 `doc_manager.py` 的逻辑：
1.  仅当源码确实存在文档字符串时，才将 `__doc__` 视为 Code 中的有效键。
2.  在计算 Extra 键时，始终忽略（允许）YAML 中存在的 `__doc__`，即使 Code 中不存在。

### 基本原理
通过放宽 `__doc__` 的存在性检查，我们消除了 `init` 和 `check` 之间的逻辑不一致。
-   **Missing 检查**: 只有当 Code 有文档但 YAML 没文档时，才报 Missing。
-   **Extra 检查**: 即使 Code 没文档，YAML 有文档也不报 Extra（允许纯外部文档化）。

### 标签
#intent/fix #flow/ready #priority/high
#comp/application #concept/docs #scope/core
#ai/instruct
#task/domain/dev-tools #task/object/check-command #task/action/bug-fix
#task/state/continue

---

### Script

#### Acts 1: 修正 `doc_manager.py` 的键提取与比对逻辑

我们将修改 `_extract_all_keys` 以有条件地添加 `__doc__`，并在 `check_module` 中从 `extra` 集合中排除 `__doc__`。

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
        # We use flatten_module_docs to get all addressable keys in the code.
        # Note: flatten_module_docs currently extracts keys ONLY if docstring exists?
        # Let's check implementation.
        # Wait, flatten_module_docs extracts keys for functions/classes regardless of docstring?
        # Looking at _extract_from_function:
        #   if func.docstring: docs[full_name] = func.docstring
        # This is a problem for 'check'. We want to know if the symbol EXISTS,
        # not just if it has a docstring in code.
        # We need a method that extracts ALL keys.

        code_keys = self._extract_all_keys(module)

        # 2. Get keys from YAML
        yaml_docs = self.load_docs_for_module(module)
        doc_keys = set(yaml_docs.keys())

        # 3. Diff
        missing = code_keys - doc_keys
        extra = doc_keys - code_keys

        return {"missing": missing, "extra": extra}

    def _extract_all_keys(self, module: ModuleDef) -> set:
        """Extracts all addressable FQNs from the module IR."""
        keys = set()

        # Module itself
        # We always expect a module to optionally have a docstring.
        # Should we force __doc__ key? Maybe not strict for now.
        # keys.add("__doc__")

        # But if the user put __doc__ in YAML, and we don't put it in keys, it shows as Extra.
        # So we should consider __doc__ as a valid key for any module.
        keys.add("__doc__")

        for func in module.functions:
~~~~~
~~~~~python.new
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
        """Extracts all addressable FQNs from the module IR."""
        keys = set()

        # Module itself
        # Only expect __doc__ if the source code actually has a docstring.
        if module.docstring:
            keys.add("__doc__")

        for func in module.functions:
~~~~~

### 下一步建议

执行此计划后，再次运行测试 `tests/integration/test_check_signatures.py`。它应该能够通过，因为 `check` 不再会因为缺少模块文档字符串而报告错误，从而允许我们专注于验证签名变更的检测逻辑。
