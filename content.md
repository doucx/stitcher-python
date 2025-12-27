沉默那些无意义的警告是优化开发者体验（DX）的关键一步。我将把这两步重构和测试的逻辑合并为一个提交。

## [COMMIT] refactor: Silence UNTRACKED warnings for boilerplate modules

### 用户需求
测试通过，要求创建 Git 提交。

### 评论
该系列修复解决了 `stitcher check` 在 Monorepo 环境中，对大量 `__init__.py` 或仅包含元数据的模块发出误导性 `UNTRACKED` 警告的问题。通过精炼 `ModuleDef.is_documentable` 方法，我们排除了 `__path__`、`__all__` 和其他私有属性，确保 `UNTRACKED` 状态只针对那些真正包含公共 API 且需要文档的文件发出。这极大地减少了噪音，提升了 `check` 作为工作流引导工具的可用性。

### 目标
1.  将 `is_documentable` 的逻辑更改应用到 `stitcher-spec`。
2.  将 `run_check` 中的文件存在性检查和 IR 内容检查的逻辑更改应用到 `stitcher-application`。
3.  提交所有文件，包括新的测试用例。

### 基本原理
我们继续遵循原子化提交原则，将整个逻辑改进作为一个完整的单元提交。

### 标签
#intent/refine #flow/ready #priority/high #comp/spec #comp/application #scope/ux #task/domain/documentation #task/object/check-logic #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将涉及到的所有文件添加到暂存区并创建提交。

~~~~~act
git_add
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/main.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/main.json
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-spec/src/stitcher/spec/models.py
tests/integration/test_check_file_tracking.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(check): Exclude boilerplate from documentable check and add UNTRACKED status

This commit finalizes the refactoring of the `stitcher check` command's file-level validation logic:

1.  **Implemented UNTRACKED Status**: A new status is reported when a Python source file has no corresponding `.stitcher.yaml` file, clearly guiding the user to run `init` or `hydrate`.
2.  **Ignored Boilerplate**: Modified `ModuleDef.is_documentable` to ignore files containing only boilerplate code (`__path__`, `__all__`, private attributes) that do not require external documentation. This prevents false positive `UNTRACKED` warnings for files like empty `__init__.py`.

This significantly reduces noise and improves the developer experience.
~~~~~

### 下一步建议

现在 `stitcher check` 的基础逻辑已经非常健壮和智能。现在你应该再次运行 `stitcher check`，确认你之前报告的所有 `UNTRACKED` 警告都已消失，只剩下真正的逻辑文件或 `PENDING` 错误。

运行：
```bash
stitcher check
```
