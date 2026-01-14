You are absolutely right. My apologies, in my attempt to break the circular dependency by removing the top-level import, I overlooked that the `add_map` helper method within `MigrationSpec` still directly instantiated `RenameSymbolOperation`. This created the `NameError` you've correctly identified.

This is an excellent catch and a classic example of a refactoring side-effect. The solution is to keep the module-level dependency broken while still allowing the method to function. We can achieve this by using a local import *inside* the `add_map` method. This solves the immediate error and preserves the architectural decoupling that the static analysis tool was pushing for.

Here is the plan to fix this oversight.

## [WIP] fix: Correct NameError in MigrationSpec by using a local import

### 错误分析

The previous plan correctly identified a circular dependency between `migration/spec.py` and the `operations` package. To break it, I removed the top-level import of `RenameSymbolOperation` from `spec.py`.

However, the `MigrationSpec.add_map` method, a convenience helper for users, directly calls `RenameSymbolOperation(...)`. Without the import, this name is undefined at runtime, leading to the `reportUndefinedVariable` error from the type checker and a `NameError` if the method were called.

### 用户需求

Fix the `NameError` / `reportUndefinedVariable` in `migration/spec.py` that was introduced by the previous refactoring.

### 评论

Your feedback is invaluable. This is a perfect example of why type checking is so important—it caught a runtime error before it could happen. The proposed solution is a standard Python pattern for breaking import cycles while maintaining API convenience.

### 目标

Modify the `MigrationSpec.add_map` method to use a local, function-scoped import for `RenameSymbolOperation`.

### 基本原理

By moving the import statement inside the method, we achieve two things:
1.  **Breaks the Circular Dependency**: The module-level dependency is gone, which satisfies static analysis tools and prevents circular import errors during initialization.
2.  **Preserves Functionality**: The name `RenameSymbolOperation` is resolved only when `add_map` is actually called, at which point all modules have been loaded. This fixes the error while keeping the convenient helper method for the user.

### 标签

#intent/fix #flow/ready #priority/high #comp/refactor #scope/core #ai/instruct #task/domain/testing #task/object/architecture-linting #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: Apply local import to `MigrationSpec.add_map`

We will modify the `add_map` method in `spec.py` to include a local import, resolving the `NameError`.

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/migration/spec.py
~~~~~
~~~~~python.old
    def add_map(self, rename_map: Dict[str, str]) -> "MigrationSpec":
        for old_fqn, new_fqn in rename_map.items():
            self.add(RenameSymbolOperation(old_fqn, new_fqn))
        return self
~~~~~
~~~~~python.new
    def add_map(self, rename_map: Dict[str, str]) -> "MigrationSpec":
        from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation

        for old_fqn, new_fqn in rename_map.items():
            self.add(RenameSymbolOperation(old_fqn, new_fqn))
        return self
~~~~~

### 下一步建议

With this correction, all identified architectural issues should now be resolved. I recommend running the static analysis or type checker again to confirm that the `reportUndefinedVariable` error is gone and no new issues have been introduced.
