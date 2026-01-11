好的，我们已经彻底堵住了 `ModuleDef` 模型中的漏洞。现在系统对“什么是本地定义的符号”有了统一且正确的认知，这将从根源上防止 `pump` 污染签名数据库，并消除 `check` 命令中的误报。

我将生成一个 `[COMMIT]` 计划来提交这些核心模型的改进。

## [COMMIT] fix(spec): exclude imported symbols from all module discovery methods

### 用户需求
`stitcher pump` 和 `init` 操作之前会错误地追踪导入的符号（如 `typing.Dict`），导致签名文件被污染并在后续的 `check` 中产生虚假警告。

### 评论
这是对符号分析逻辑的最终完善。通过在 `ModuleDef` 模型层面上统一过滤掉别名（Aliases），我们确保了系统所有组件（从索引构建到文档检查）对“模块定义”的理解是一致且准确的。这体现了“真理单一来源 (SSoT)”的工程原则。

### 目标
1. 提交对 `packages/stitcher-spec/src/stitcher/spec/models.py` 的修改。
2. 确保 `is_documentable` 和 `get_all_fqns` 方法均已正确排除 `alias_target` 不为空的属性。

### 基本原理
`ModuleDef` 是系统的核心中间表示（IR）。将过滤逻辑下沉到模型内部，而不是在各个调用方单独处理，可以极大地提高系统的稳健性并降低维护成本。这防止了导入符号进入签名持久化层，从根本上解决了问题。

### 标签
#intent/fix #flow/ready #priority/critical #comp/spec #concept/state #task/domain/core #task/object/module-model #task/action/bug-fix #task/state/end

---

### Script

#### Acts 1: 提交模型层修复

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(spec): exclude imported symbols from all module discovery methods

The `ModuleDef` model was incorrectly including imported symbols (aliases) in its core discovery methods: `is_documentable()` and `get_all_fqns()`. This caused `stitcher pump` to generate signatures for external types like `typing.List` or `pathlib.Path`, leading to persistent "missing documentation" warnings.

This fix ensures that:
1. `is_documentable()` only returns True if the module has a docstring or actual local public definitions.
2. `get_all_fqns()` excludes any attribute that has an `alias_target` defined.

This change prevents signature database pollution and ensures that all downstream consumers of the `ModuleDef` IR correctly ignore re-exports and standard imports.
~~~~~

### 下一步建议
- **清理与验证**：建议您执行 `rm -rf .stitcher/signatures` 和 `rm .stitcher/index/index.db` 以清除旧的错误数据，然后重新运行 `stitcher pump` 和 `check`。
- **文档补充**：既然逻辑已经稳定，可以开始为 `stitcher-application` 中那些确实缺少文档的核心组件（如 `CheckRunner`）补充文档字符串了。
