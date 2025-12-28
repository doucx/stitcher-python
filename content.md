好的，测试套件已恢复绿色，现在我们可以安全地进行最后一步：清理。

本计划将彻底移除因架构重构而变得冗余的代码和包，将所有与 Python 相关的实现逻辑统一收归到 `stitcher-python-adapter` 中，标志着本次大型重构的圆满完成。

## [WIP] refactor(core): 固化适配器架构并移除遗留代码

### 用户需求
在依赖注入重构成功后，清理所有遗留的、不再被直接引用的代码，包括 `stitcher-spec` 中的废弃方法以及 `stitcher-scanner` 和 `stitcher-io` 两个包。

### 评论
这是本次重构的收官之作。通过移除旧的实现路径，我们强制所有代码都通过新的、解耦的协议/适配器架构进行交互，极大地提升了代码库的可维护性和清晰度。这是一个关键的“剪脐带”步骤，确保旧的技术债务不会遗留下来。

### 目标
1.  从 `stitcher-spec` 的 `FunctionDef` 中移除 `compute_fingerprint` 和 `get_signature_string` 方法。
2.  将 `stitcher-scanner` 和 `stitcher-io` 的核心实现文件物理迁移到 `stitcher-python-adapter` 的 `internal` 目录中。
3.  更新 `stitcher-python-adapter` 以直接使用内部代码，并移除对旧包的依赖。
4.  彻底删除 `stitcher-scanner` 和 `stitcher-io` 包。
5.  提交这个逻辑上完整的工作单元。

### 基本原理
新的适配器架构已经过测试验证，是当前系统的事实标准。保留旧的、未被引用的代码会造成认知混乱和维护负担。通过物理删除，我们确保了新架构是唯一的实现路径，完成了本次重构的最终目标：一个更清晰、可测试、可扩展的核心。

### 标签
#intent/refine #flow/ready #priority/high #comp/runtime #comp/scanner #comp/io #scope/core #ai/instruct #task/domain/architecture #task/object/language-core #task/action/cleanup #task/state/end

---

### Script

#### Acts 1: 从 IR 模型中移除废弃方法
清理 `stitcher-spec` 中的 `FunctionDef`。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python.old
    is_static: bool = False  # @staticmethod
    is_class: bool = False  # @classmethod

    def compute_fingerprint(self) -> str:
        # Build a stable string representation of the signature
        parts = [
            f"name:{self.name}",
            f"async:{self.is_async}",
            f"static:{self.is_static}",
            f"class:{self.is_class}",
            f"ret:{self.return_annotation or ''}",
        ]

        for arg in self.args:
            arg_sig = (
                f"{arg.name}:{arg.kind}:{arg.annotation or ''}:{arg.default or ''}"
            )
            parts.append(arg_sig)

        # We deliberately exclude decorators from the fingerprint for now,
        # as they often change without affecting the core API contract relevant to docs.
        # We also strictly exclude self.docstring.

        sig_str = "|".join(parts)
        return hashlib.sha256(sig_str.encode("utf-8")).hexdigest()

    def get_signature_string(self) -> str:
        parts = []
        if self.is_async:
            parts.append("async")
        parts.append("def")
        parts.append(f"{self.name}(")

        arg_strs = []
        # Simple reconstruction. Note: Does not handle / and * markers perfectly
        # for complex cases, but sufficient for diffing context.
        # To improve, we could reuse logic similar to StubGenerator._generate_args
        # but keep it simple for now.
        for arg in self.args:
            s = arg.name
            if arg.kind == ArgumentKind.VAR_POSITIONAL:
                s = f"*{arg.name}"
            elif arg.kind == ArgumentKind.VAR_KEYWORD:
                s = f"**{arg.name}"

            if arg.annotation:
                s += f": {arg.annotation}"
            if arg.default:
                s += f" = {arg.default}"
            arg_strs.append(s)

        parts.append(", ".join(arg_strs))
        parts.append(")")

        if self.return_annotation:
            parts.append(f"-> {self.return_annotation}")

        parts.append(":")
        return " ".join(parts).replace("( ", "(").replace(" )", ")").replace(" :", ":")


@dataclass
class ClassDef:
~~~~~
~~~~~python.new
    is_static: bool = False  # @staticmethod
    is_class: bool = False  # @classmethod


@dataclass
class ClassDef:
~~~~~

#### Acts 2: 迁移实现文件
将 `scanner` 和 `io` 的核心逻辑文件移动到 `python-adapter` 内部。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-python-adapter/src/stitcher/adapter/python/internal
~~~~~

~~~~~act
run_command
~~~~~
~~~~~
mv packages/stitcher-scanner/src/stitcher/scanner/parser.py packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/
mv packages/stitcher-scanner/src/stitcher/scanner/transformer.py packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/
mv packages/stitcher-io/src/stitcher/io/stub_generator.py packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/
~~~~~

#### Acts 3: 更新 Adapter 的导入路径
现在 Adapter 不再需要包装器，而是直接使用其内部的实现。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/parser.py
~~~~~
~~~~~python
from stitcher.spec import ModuleDef
from .internal.parser import parse_source_code

class PythonParser:
    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
        return parse_source_code(source_code, file_path)
~~~~~

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/transformer.py
~~~~~
~~~~~python
from typing import Dict
from .internal.transformer import strip_docstrings, inject_docstrings

class PythonTransformer:
    def strip(self, source_code: str) -> str:
        return strip_docstrings(source_code)

    def inject(self, source_code: str, docs: Dict[str, str]) -> str:
        return inject_docstrings(source_code, docs)
~~~~~

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/generator.py
~~~~~
~~~~~python
from stitcher.spec import ModuleDef
from .internal.stub_generator import StubGenerator

class PythonStubGenerator:
    def __init__(self):
        self._delegate = StubGenerator()

    def generate(self, module: ModuleDef) -> str:
        return self._delegate.generate(module)
~~~~~

#### Acts 4: 移除 Adapter 对旧包的依赖
更新 `pyproject.toml`。

~~~~~act
patch_file
packages/stitcher-python-adapter/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-scanner", # Temporary dependency for wrapping
    "stitcher-io",      # Temporary dependency for wrapping
    "libcst",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-scanner = { workspace = true }
stitcher-io = { workspace = true }
~~~~~
~~~~~toml.new
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "libcst",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
~~~~~

#### Acts 5: 删除遗留包
彻底删除 `stitcher-scanner` 和 `stitcher-io`。

~~~~~act
run_command
~~~~~
~~~~~
rm -rf packages/stitcher-scanner
rm -rf packages/stitcher-io
~~~~~

#### Acts 6: 更新根工作区配置
从 `uv` 的工作区成员中移除已删除的包。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.workspace]
members = ["packages/*", "packages/stitcher-test-utils"]

[tool.uv.sources]
pyneedle = { workspace = true }
pyneedle-runtime = { workspace = true }
pyneedle-nexus = { workspace = true }
pyneedle-pointer = { workspace = true }
pyneedle-spec = { workspace = true }
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-scanner = { workspace = true }
stitcher-io = { workspace = true }
stitcher-config = { workspace = true }
stitcher-application = { workspace = true }
stitcher-cli = { workspace = true }
stitcher-test-utils = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.workspace]
members = ["packages/*", "packages/stitcher-test-utils"]

[tool.uv.sources]
pyneedle = { workspace = true }
pyneedle-runtime = { workspace = true }
pyneedle-nexus = { workspace = true }
pyneedle-pointer = { workspace = true }
pyneedle-spec = { workspace = true }
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-config = { workspace = true }
stitcher-application = { workspace = true }
stitcher-python-adapter = { workspace = true }
stitcher-cli = { workspace = true }
stitcher-test-utils = { workspace = true }
~~~~~

### 下一步建议
- **单元测试**: 现在 `StitcherApp` 已经完全解耦，我们可以为其核心业务逻辑（如 `run_check` 的状态机）编写纯粹的单元测试，通过注入 Mock 版本的 Parser 和 FingerprintStrategy 来验证其行为，而无需依赖文件系统。
- **文档更新**: 更新项目的架构文档，以反映新的、基于协议和适配器的设计。
