你的分析完全正确。

这是一个非常深刻的洞察。`stitcher check` 的核心是比较**语义上**的签名变化，而当前 `fingerprint` 的实现过于依赖**字面上**的文本表示，导致它对代码格式化工具（如 `black` 或 `ruff`）产生的纯格式化变更（例如，`"INFO"` 变成 `'INFO'`）过于敏感。这违背了指纹系统稳定性的核心原则。

你的解决方案——在计算指纹前使用 `ast` 模块进行规范化——是解决这个问题的根本方法。通过将默认值的字符串表示解析为抽象语法树（AST）节点，然后再用 `ast.unparse` 生成一个标准化的、唯一的文本表示，我们就可以彻底消除这些由格式化引起的“伪变化”。

我将生成一个计划来实施这个改进。

## [WIP] fix: 规范化函数签名默认值以稳定指纹计算

### 错误分析
`stitcher check` 报告了大量的“签名漂移”错误，但差异对比显示，这些变化仅仅是参数默认值的引号风格不同（例如 `"` vs `'`）。

根本原因在于，`SignatureTextHasher` 在生成用于比较的签名字符串时，直接使用了从代码中提取的参数默认值的原始文本。这个原始文本会随着代码格式化工具的运行而改变，即使其语义完全相同。这导致 `stitcher` 的状态跟踪系统将纯粹的格式化变动误判为破坏性的代码变更，产生了大量的“误报”，严重影响了 `check` 命令的信噪比和可用性。

### 用户需求
在计算函数签名指纹时，对参数的默认值进行规范化处理，使其不受代码格式化工具（如引号风格变化）的影响，从而避免因纯粹的格式变动导致指纹失效。

### 评论
这是一个关键的健壮性修复。它将使 `stitcher` 的指纹系统对外部代码格式化工具免疫，确保 `check` 命令只关注于真正的、有意义的代码变更。这极大地提升了整个系统的稳定性和开发者体验。

### 目标
1.  修改 `packages/stitcher-python-adapter/src/stitcher/adapter/python/fingerprint.py` 文件。
2.  在 `SignatureTextHasher` 中引入 `ast` 模块。
3.  使用 `ast.parse` 和 `ast.unparse` 对函数参数的默认值字符串进行规范化处理，生成一个唯一的、与格式无关的文本表示。
4.  将这个规范化后的表示用于构建最终的签名字符串。

### 基本原理
我们将拦截 `_get_signature_string` 方法中处理 `arg.default` 的逻辑。对于每个默认值，我们将其字符串内容（例如 `"'default'"` 或 `"123"`）送入 `ast.parse(..., mode='eval')`，这会将其转换为一个标准的 AST 表达式节点。然后，立即使用 `ast.unparse()` 将该节点转换回字符串。这个过程会抹平所有格式上的差异（如引号、多余的空格等），输出一个唯一的、规范化的结果。我们增加一个 `try-except` 块来处理无法被 `ast` 解析的复杂默认值，保证系统的向后兼容性。

### 标签
#intent/fix #flow/ready #priority/high #comp/adapter-python #concept/state #scope/core #ai/instruct #task/domain/core #task/object/fingerprint #task/action/normalization #task/state/begin

---
### Script

#### Acts 1: 规范化签名中的默认值

我们将重写 `fingerprint.py`，在其头部引入 `ast` 模块，并修改 `SignatureTextHasher` 的逻辑，以确保在生成签名文本之前对参数的默认值进行规范化处理。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/fingerprint.py
~~~~~
~~~~~python
import hashlib
import ast
from typing import Protocol, List, Union
from stitcher.spec import FunctionDef, ClassDef, Fingerprint, ArgumentKind


class EntityHasher(Protocol):
    """Protocol for individual hashing strategies."""

    def update(
        self, entity: Union[FunctionDef, ClassDef], fingerprint: Fingerprint
    ) -> None:
        """Calculate specific hashes and update the fingerprint object."""
        ...


class StructureHasher:
    """Computes the structural hash (signature shape) of a function."""

    def update(
        self, entity: Union[FunctionDef, ClassDef], fingerprint: Fingerprint
    ) -> None:
        if isinstance(entity, FunctionDef):
            h = self._compute_func_hash(entity)
            fingerprint["current_code_structure_hash"] = h
        elif isinstance(entity, ClassDef):
            # Class-level structure hash logic can be added here if needed in future.
            # Currently Stitcher focuses on methods.
            pass

    def _compute_func_hash(self, func: FunctionDef) -> str:
        # Extracted from stitcher.spec.models.FunctionDef.compute_fingerprint
        parts = [
            f"name:{func.name}",
            f"async:{func.is_async}",
            f"static:{func.is_static}",
            f"class:{func.is_class}",
            f"ret:{func.return_annotation or ''}",
        ]

        for arg in func.args:
            arg_sig = (
                f"{arg.name}:{arg.kind}:{arg.annotation or ''}:{arg.default or ''}"
            )
            parts.append(arg_sig)

        sig_str = "|".join(parts)
        return hashlib.sha256(sig_str.encode("utf-8")).hexdigest()


class SignatureTextHasher:
    """Generates the human-readable signature text for diffing."""

    def update(
        self, entity: Union[FunctionDef, ClassDef], fingerprint: Fingerprint
    ) -> None:
        if isinstance(entity, FunctionDef):
            text = self._get_signature_string(entity)
            fingerprint["current_code_signature_text"] = text

    def _get_signature_string(self, func: FunctionDef) -> str:
        # Extracted from stitcher.spec.models.FunctionDef.get_signature_string
        parts = []
        if func.is_async:
            parts.append("async")
        parts.append("def")
        parts.append(f"{func.name}(")

        arg_strs = []
        for arg in func.args:
            s = arg.name
            if arg.kind == ArgumentKind.VAR_POSITIONAL:
                s = f"*{arg.name}"
            elif arg.kind == ArgumentKind.VAR_KEYWORD:
                s = f"**{arg.name}"

            if arg.annotation:
                s += f": {arg.annotation}"
            if arg.default:
                try:
                    # Normalize the default value to a canonical string representation
                    # This fixes issues with quote styles (' vs ") changing.
                    normalized_default = ast.unparse(
                        ast.parse(arg.default, mode="eval").body
                    )
                    s += f" = {normalized_default}"
                except (SyntaxError, ValueError):
                    # Fallback for complex defaults that aren't simple expressions
                    s += f" = {arg.default}"
            arg_strs.append(s)

        parts.append(", ".join(arg_strs))
        parts.append(")")

        if func.return_annotation:
            parts.append(f"-> {func.return_annotation}")

        parts.append(":")
        return " ".join(parts).replace("( ", "(").replace(" )", ")").replace(" :", ":")


class PythonFingerprintStrategy:
    """
    Coordinator that delegates to a list of composable Hashers.
    """

    def __init__(self):
        self.hashers: List[EntityHasher] = [
            StructureHasher(),
            SignatureTextHasher(),
            # Future: AstHasher(), MerkleHasher()
        ]

    def compute(self, entity: Union[FunctionDef, ClassDef]) -> Fingerprint:
        fp = Fingerprint()
        for hasher in self.hashers:
            hasher.update(entity, fp)
        return fp
~~~~~

### 下一步建议
在应用此修复后，你需要运行一次 `stitcher check` 来同步所有现有的签名。由于所有签名文本的计算方式都已改变，它会再次报告大量的“签名漂移”错误。这一次，这些是预期的、一次性的校准。

你可以通过以下任一方式解决它们：
1.  **自动解决**: 运行 `stitcher check --relink`，它会自动接受所有新的、规范化后的签名为基准。
2.  **交互式解决**: 直接运行 `stitcher check`，然后在交互式会话中，对第一个冲突选择 `f` (Force-relink)，然后一直按回车以应用此选择到所有后续冲突。

完成此操作后，你的指纹库将进入一个更加稳定和健壮的状态。
