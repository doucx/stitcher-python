简要回答
还有一个残留的断言需要更新。我们将 `func_alias()` 的期望 SURI 从本地别名修改为指向 `defs.py` 中的原始定义。

## [WIP] fix: 修正集成测试中 func_alias 的断言

### 错误分析
测试中 `func_alias()` 的断言仍然期望链接到本地别名 `py://pkg/main.py#func_alias`。然而，正如之前的分析，我们的系统已经正确地穿透了别名，将其直接链接到了 `py://pkg/defs.py#my_func`。

### 用户需求
修正 `test_scanner_aliases.py` 中最后一个不匹配的断言。

### 评论
这次修改将完成测试用例与“直接到定义”链接逻辑的全面同步。

### 目标
1.  修改 `packages/stitcher-index/tests/integration/test_scanner_aliases.py`，将 `func_alias()` 的断言更新为指向 `py://pkg/defs.py#my_func`。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #ai/instruct #task/domain/storage #task/object/linker #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正最后一个测试断言

~~~~~act
patch_file
packages/stitcher-index/tests/integration/test_scanner_aliases.py
~~~~~
~~~~~python.old
    # pkg.defs.my_func() -> Should resolve 'pkg' to the package and link to the function
    assert "py://pkg/defs.py#my_func" in ref_targets

    # func_alias() -> Should reference the func_alias alias
    assert "py://pkg/main.py#func_alias" in ref_targets
~~~~~
~~~~~python.new
    # pkg.defs.my_func() -> Should resolve 'pkg' to the package and link to the function
    assert "py://pkg/defs.py#my_func" in ref_targets

    # func_alias() -> Should resolve 'func_alias' to its original definition
    assert "py://pkg/defs.py#my_func" in ref_targets
~~~~~

### 下一步建议
运行测试。这将确认跨文件别名解析和引用链接在本项目中已完全调通。下一步我们将进入 Phase 3，开始将 `stitcher-refactor` 的查询逻辑迁移到这个索引数据库之上。
