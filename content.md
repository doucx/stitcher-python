# [WIP] fix: 防止 Import 语句中的节点被重复访问

## [WIP] fix: 防止 Import 语句中的节点被重复访问

### 错误分析
单元测试失败显示 `ImportFrom` 语句中的符号被注册了两次。
原因在于 `visit_ImportFrom`（和 `visit_Import`）目前返回 `True`，导致 LibCST 继续遍历其子节点（如 `cst.Name`）。
1.  **第一次注册**: 在 `visit_ImportFrom` 中，我们手动解析并注册了节点（通常作为 `IMPORT_PATH` 或 `SYMBOL`）。同时，我们将该符号添加到了 `active_symbols` 中。
2.  **第二次注册**: LibCST 继续遍历子节点，触发 `visit_Name`。`visit_Name` 在 `active_symbols` 中发现了该符号，于是将其再次注册为 `SYMBOL` 类型的使用。

### 用户需求
修复重复注册问题，确保 Import 语句中的每个符号只产生一条正确的引用记录。

### 评论
这是在使用 Visitor 模式维护状态时常见的问题。对于像 Import 这样具有“定义”性质的语句，我们通常希望完全接管其处理逻辑，而不让通用的 `visit_Name` 逻辑干扰。

### 目标
修改 `UsageScanVisitor` 中的 `visit_Import` 和 `visit_ImportFrom`，使其返回 `False`，从而阻止对子节点的默认遍历。

### 基本原理
通过返回 `False`，我们要么显式地处理了子节点（如在 `visit_ImportFrom` 中我们确实遍历了 `node.names`），要么明确表示子节点不需要通用的处理逻辑。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #scope/core #ai/instruct #task/domain/analysis #task/object/usage-visitor #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修改 UsageScanVisitor 返回 False

~~~~~act
patch_file
packages/stitcher-python-analysis/src/stitcher/python/analysis/cst/usage_visitor.py
~~~~~
~~~~~python.old
                # Case 2: import a.b.c -> local 'a' maps to 'a'
                else:
                    top_level = absolute_module.split(".")[0]
                    self.active_symbols[top_level] = top_level

        return True

    def visit_ImportFrom(self, node: cst.ImportFrom) -> Optional[bool]:
~~~~~
~~~~~python.new
                # Case 2: import a.b.c -> local 'a' maps to 'a'
                else:
                    top_level = absolute_module.split(".")[0]
                    self.active_symbols[top_level] = top_level

        # Prevent visiting children to avoid double-counting in visit_Name
        return False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> Optional[bool]:
~~~~~

~~~~~act
patch_file
packages/stitcher-python-analysis/src/stitcher/python/analysis/cst/usage_visitor.py
~~~~~
~~~~~python.old
                        if alias.asname and isinstance(alias.asname.name, cst.Name):
                            local_name = alias.asname.name.value
                        
                        self.active_symbols[local_name] = full_fqn
                        
        return True

    def visit_Attribute(self, node: cst.Attribute) -> Optional[bool]:
~~~~~
~~~~~python.new
                        if alias.asname and isinstance(alias.asname.name, cst.Name):
                            local_name = alias.asname.name.value
                        
                        self.active_symbols[local_name] = full_fqn
        
        # Prevent visiting children to avoid double-counting in visit_Name
        return False

    def visit_Attribute(self, node: cst.Attribute) -> Optional[bool]:
~~~~~

### 下一步建议
重新运行 `packages/stitcher-python-adapter/tests/unit/test_index_adapter_references.py` 和 `packages/stitcher-python-analysis/tests/unit/cst/test_usage_visitor.py` 测试。
