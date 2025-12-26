好的，既然验证已经通过，我们现在将这些关键修复作为一个完整的逻辑单元提交。

这组修改解决了 `stitcher` 在自举（Dogfooding）过程中的一个重大阻碍：由于丢失了类装饰器（尤其是 `@dataclass`）和属性默认值，导致生成的类型存根（Stubs）无法被类型检查器正确解析。

## [COMMIT] fix(core): 支持类装饰器与属性赋值以修复数据类存根

### 用户需求
确保生成的 `.pyi` 文件能够高保真地还原代码的语义结构，特别是针对 `dataclass` 的类型推断能力。

### 评论
这是一次重要的架构补完。通过恢复装饰器和属性值的透传，我们确保了 `stitcher` 生成的存根不仅在视觉上相似，而且在语义上对静态分析工具（Pyright/Mypy）是完全透明且准确的。

### 目标
1.  提交对 `stitcher-spec` 中 `ClassDef` 模型的扩展。
2.  提交对 `stitcher-scanner` 中类装饰器提取逻辑的改进。
3.  提交对 `stitcher-io` 中存根生成逻辑的修复（恢复属性赋值）。

### 基本原理
在现代 Python 开发中，装饰器（如 `@dataclass`, `@property`）和赋值（定义默认值）承载了大量的类型元数据。将这些信息纳入 IR 并在生成环节还原，是实现“高保真存根”这一核心愿景的必然要求。

### 标签
#intent/fix #flow/ready #comp/engine #concept/parser #concept/generator #scope/core #ai/instruct #task/domain/codemod #task/object/decorators #task/action/fix #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交代码修改

我们将把涉及 Spec、Scanner 和 IO 三个包的修改添加并提交。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/models.py
packages/stitcher-scanner/src/stitcher/scanner/parser.py
packages/stitcher-io/src/stitcher/io/stub_generator.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(core): support class decorators and attribute values in stubs

This commit fixes a major type-checking failure encountered during dogfooding.
Previously, generated .pyi files lost @dataclass decorators and default values
for attributes, which caused Pyright/Mypy to fail on every constructor call
due to missing __init__ signatures or mandatory arguments.

- Spec: Added 'decorators' field to ClassDef model.
- Scanner: Updated CST visitor to extract decorators for classes.
- IO: Updated StubGenerator to output @decorators and restore attribute 
  assignments (e.g., field default factories), ensuring full semantic 
  fidelity for dataclasses.
~~~~~

### 下一步建议
- **更新项目存根**: 既然修复已提交，建议在项目根目录再次运行 `stitcher generate`。由于现在支持了装饰器和默认值，你将看到项目自身的 IDE 报错彻底消失。
- **验证 `check` 命令**: 运行 `stitcher check` 确保当前的逻辑修改没有影响代码与文档的同步性。
