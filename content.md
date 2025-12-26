## [WIP] fix(io): 恢复 Stub 中的属性值输出以修复 Dataclass 默认值丢失

### 错误分析
**现象**: `pyrefly check` 报错大量的 `Missing argument ... in function ...__init__`。
**原因**:
1.  **进展示意**: 上一步的修复成功让类型检查器识别到了 `@dataclass` 装饰器，因此它开始自动合成 `__init__` 方法。
2.  **默认值丢失**: 在当前的 `StubGenerator` 实现中，为了简化输出，**人为丢弃了属性的赋值部分**（即 `= value`）。
3.  **后果**: 对于 `dataclass` 而言，如果字段定义为 `x: List[int] = field(default_factory=list)`，但在 Stub 中被剥离为 `x: List[int]`，类型检查器就会认为 `x` 是一个**没有默认值**的字段。因此，在调用 `__init__` 时，这些参数变成了必填项，导致测试代码（未传递这些参数）报错。

### 用户需求
修复生成的 `.pyi` 文件，使其包含属性的默认值（特别是 `field(...)`），从而让类型检查器正确识别可选参数。

### 评论
这是一个非常典型的“好心办坏事”。原本为了 `.pyi` 的简洁性而移除赋值，却破坏了 `dataclass` 的语义完整性。在 Python 类型系统中，`= ...` 或具体的赋值是判断参数是否可选的唯一依据。

### 目标
修改 `StubGenerator`，使其在生成属性定义时，如果存在 `value`，则将其完整输出。

### 基本原理
恢复被注释掉的代码逻辑。由于 Scanner 已经完整提取了源码中的赋值表达式（例如 `"field(default_factory=list)"`），且我们保留了所有的 import，直接将这个值写入 `.pyi` 文件既能恢复语义，也是类型安全的。

### 标签
#intent/fix #flow/ready #priority/high #comp/engine #concept/generator #scope/core #task/domain/codemod #task/object/attribute-value #task/action/restore #task/state/continue

---

### Script

#### Acts 1: 恢复属性值输出

修改 `stub_generator.py`，取消对属性值的注释，使其被正确写入。

~~~~~act
patch_file
packages/stitcher-io/src/stitcher/io/stub_generator.py
~~~~~
~~~~~python.old
        annotation = attr.annotation if attr.annotation else "Any"
        line = f"{indent}{attr.name}: {annotation}"

        # If we wanted to include value:
        # if attr.value:
        #     line += f" = {attr.value}"

        return line
~~~~~
~~~~~python.new
        annotation = attr.annotation if attr.annotation else "Any"
        line = f"{indent}{attr.name}: {annotation}"

        if attr.value:
            line += f" = {attr.value}"

        return line
~~~~~

### 下一步建议
执行此计划后，再次运行 `stitcher generate` 重新生成所有存根文件，然后运行 `pyrefly check`。预期所有 `Missing argument` 错误都将消失。
