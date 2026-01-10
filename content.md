Excellent. We will now proceed with the second step: migrating the logic.

As per your instruction, this step will be a "copy" operation. I will create the new files in the `stitcher-stubgen` package with the necessary code, but I will **not** delete the original source files yet. This is a safe, incremental approach.

I'll create a plan that populates the new package with the migrated and slightly adapted code.

## [WIP] refactor(arch): Migrate stubgen logic to new package

### 用户需求

将存根生成的核心逻辑（`PythonStubGenerator`, `GenerateRunner`, `StubPackageManager`）从 `stitcher-python-adapter` 和 `stitcher-application` 迁移到新创建的 `stitcher-stubgen` 包中。此阶段仅执行代码的复制和适应性修改，不删除源文件。

### 评论

这是解耦重构的核心执行步骤。通过将相关的代码物理上移动到其所属的新领域边界（`stitcher-stubgen` 包），我们正在将架构意图转化为代码的物理现实。这种“先复制，后切换，再删除”的三步走策略是进行此类重构最安全、最可控的方式，它确保了在任何时刻，系统都处于一个可编译、可测试的状态。

### 目标

1.  在 `stitcher-stubgen` 中创建 `generator.py`，并将 `stitcher-python-adapter` 中的 `StubGenerator` 核心逻辑迁移至此，并将其重命名为 `PythonStubGenerator` 作为公共接口。
2.  在 `stitcher-stubgen` 中创建 `services.py`，并将 `stitcher-application` 中的 `StubPackageManager` 逻辑迁移至此。
3.  在 `stitcher-stubgen` 中创建 `runners.py`，并将 `stitcher-application` 中的 `GenerateRunner` 逻辑迁移至此，同时更新其内部导入以指向新的 `services.py`。

### 基本原理

我们使用 `write_file` 来创建三个核心的新模块文件。

1.  对于 `generator.py`，我们直接将 `internal.stub_generator` 的实现作为新的 `PythonStubGenerator` 的实现，这简化了代码结构，移除了不必要的内部包装层。
2.  对于 `services.py`，这是一个直接的文件内容复制。
3.  对于 `runners.py`，在复制 `GenerateRunner` 的同时，我们必须主动修正其对 `StubPackageManager` 的导入路径，使其从 `stitcher.app.services` 指向新的 `stitcher.stubgen.services`。这确保了新包内部的模块间依赖是自洽的，为下一步的集成做好了准备。

### 标签

#intent/refine #flow/ready #priority/high #comp/python-adapter #comp/application #scope/core #task/domain/architecture #task/object/stubgen-package #task/action/migration #task/state/continue

---

### Script

#### Acts 1: 迁移生成器 (Generator) 逻辑

我们将 `stitcher-python-adapter` 内部的 `StubGenerator` 逻辑复制并重构为 `stitcher-stubgen` 包中公开的 `PythonStubGenerator`。

~~~~~act
write_file
packages/stitcher-stubgen/src/stitcher/stubgen/generator.py
~~~~~
~~~~~python
from typing import List
from stitcher.spec import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
)


class PythonStubGenerator:
    def __init__(self, indent_spaces: int = 4):
        self._indent_str = " " * indent_spaces

    def generate(self, module: ModuleDef) -> str:
        lines = []

        # 1. Module Docstring (Ignored in skeleton generation)

        # 2. Imports (TODO: Pass these through from scanner later)
        if module.imports:
            for imp in module.imports:
                lines.append(imp)
            lines.append("")

        # 2.5. __all__
        if module.dunder_all:
            lines.append(f"__all__ = {module.dunder_all}")
            lines.append("")

        # 3. Module Attributes
        for attr in module.attributes:
            lines.append(self._generate_attribute(attr, 0))
        if module.attributes:
            lines.append("")

        # 4. Functions
        for func in module.functions:
            lines.append(self._generate_function(func, 0))
            lines.append("")

        # 5. Classes
        for cls in module.classes:
            lines.append(self._generate_class(cls, 0))
            lines.append("")

        return "\n".join(lines).strip()

    def _indent(self, level: int) -> str:
        return self._indent_str * level

    def _generate_attribute(
        self, attr: Attribute, level: int, include_value: bool = True
    ) -> str:
        indent = self._indent(level)
        # In .pyi files, we prefer Type Hints:  name: type
        # If value is present (constant), we might output: name: type = value
        # But PEP 484 recommends name: type = ... for constants or just name: type
        # For class attributes, we purposefully exclude values to avoid scoping issues.

        annotation = attr.annotation if attr.annotation else "Any"
        line = f"{indent}{attr.name}: {annotation}"

        if include_value and attr.value:
            line += f" = {attr.value}"

        return line

    def _generate_args(self, args: List[Argument]) -> str:
        # This is tricky because of POSITIONAL_ONLY (/) and KEYWORD_ONLY (*) markers.
        # We need to detect transitions between kinds.

        # Simplified approach for MVP:
        # Just join them. Correctly handling / and * requires looking ahead/behind or state machine.
        # Let's do a slightly better job:

        parts = []

        # Check if we have pos-only args
        has_pos_only = any(a.kind == ArgumentKind.POSITIONAL_ONLY for a in args)
        pos_only_emitted = False

        kw_only_marker_emitted = False

        for i, arg in enumerate(args):
            # Handle POSITIONAL_ONLY end marker
            if has_pos_only and not pos_only_emitted:
                if arg.kind != ArgumentKind.POSITIONAL_ONLY:
                    parts.append("/")
                    pos_only_emitted = True

            # Handle KEYWORD_ONLY start marker
            if arg.kind == ArgumentKind.KEYWORD_ONLY and not kw_only_marker_emitted:
                # If the previous arg was VAR_POSITIONAL (*args), we don't need a bare *
                # Otherwise, we do.
                prev_was_var_pos = (
                    i > 0 and args[i - 1].kind == ArgumentKind.VAR_POSITIONAL
                )
                if not prev_was_var_pos:
                    parts.append("*")
                kw_only_marker_emitted = True

            # Format the argument itself
            arg_str = arg.name
            if arg.kind == ArgumentKind.VAR_POSITIONAL:
                arg_str = f"*{arg.name}"
            elif arg.kind == ArgumentKind.VAR_KEYWORD:
                arg_str = f"**{arg.name}"

            if arg.annotation:
                arg_str += f": {arg.annotation}"

            if arg.default:
                arg_str += f" = {arg.default}"

            parts.append(arg_str)

        # Edge case: If all args were pos-only, we need to append / at the end
        if has_pos_only and not pos_only_emitted:
            parts.append("/")

        return ", ".join(parts)

    def _generate_function(self, func: FunctionDef, level: int) -> str:
        indent = self._indent(level)
        lines = []

        # Decorators
        for dec in func.decorators:
            # dec is raw code like "staticmethod", we need to prepend @
            # But wait, LibCST might or might not include @?
            # In our scanner we did: code_for_node(dec.decorator). So it is just the name/call.
            lines.append(f"{indent}@{dec}")

        # Async
        prefix = "async " if func.is_async else ""

        # Def
        args_str = self._generate_args(func.args)
        ret_str = f" -> {func.return_annotation}" if func.return_annotation else ""

        def_line = f"{indent}{prefix}def {func.name}({args_str}){ret_str}:"

        # Body - Always use ellipsis for skeleton
        lines.append(f"{def_line} ...")

        return "\n".join(lines)

    def _generate_class(self, cls: ClassDef, level: int) -> str:
        indent = self._indent(level)
        lines = []

        # Decorators
        for dec in cls.decorators:
            lines.append(f"{indent}@{dec}")

        # Class Def
        bases_str = ""
        if cls.bases:
            bases_str = f"({', '.join(cls.bases)})"

        lines.append(f"{indent}class {cls.name}{bases_str}:")

        # Body
        has_content = False

        # Docstring (Ignored in skeleton)

        # Attributes
        for attr in cls.attributes:
            # We explicitly DISABLE value generation for class attributes.
            # This prevents bugs where instance attributes initialized from __init__ arguments
            # (e.g. self.x = x) are generated as class attrs with invalid values (x: Any = x).
            lines.append(self._generate_attribute(attr, level + 1, include_value=False))
            has_content = True

        if has_content and cls.methods:
            lines.append("")  # Spacer between attrs and methods

        # Methods
        for i, method in enumerate(cls.methods):
            lines.append(self._generate_function(method, level + 1))
            if i < len(cls.methods) - 1:
                lines.append("")  # Spacer between methods
            has_content = True

        if not has_content:
            lines.append(f"{self._indent(level + 1)}...")

        return "\n".join(lines)
~~~~~

#### Acts 2: 迁移服务 (Services) 逻辑

我们将 `StubPackageManager` 移动到新包的 `services.py` 模块中。

~~~~~act
write_file
packages/stitcher-stubgen/src/stitcher/stubgen/services.py
~~~~~
~~~~~python
from pathlib import Path
import tomli_w

from stitcher.common.transaction import TransactionManager


class StubPackageManager:
    @staticmethod
    def _get_pep561_logical_path(logical_path: Path) -> Path:
        if not logical_path.parts:
            return logical_path

        namespace = logical_path.parts[0]
        rest_of_path = logical_path.parts[1:]
        # e.g. my_app/main.py -> my_app-stubs/main.py
        return Path(f"{namespace}-stubs", *rest_of_path)

    def scaffold(
        self,
        package_path: Path,
        source_project_name: str,
        package_namespace: str,
        tm: TransactionManager,
        root_path: Path,
    ) -> bool:
        config_path = package_path / "pyproject.toml"
        if config_path.exists():
            return False

        # Note: Directory creation is now handled implicitly by add_write.
        stub_src_dirname = self._get_pep561_logical_path(
            Path(package_namespace)
        ).as_posix()

        # Create pyproject.toml
        pyproject_content = {
            "build-system": {
                "requires": ["hatchling"],
                "build-backend": "hatchling.build",
            },
            "project": {
                "name": f"{source_project_name}-stubs",
                "version": "0.1.0",  # Placeholder version
                "description": f"PEP 561 type stubs for {source_project_name}",
            },
            "tool": {
                "hatch": {
                    "build": {
                        "targets": {
                            "wheel": {
                                # Essential for packaging .pyi files correctly under the namespace
                                "packages": [f"src/{stub_src_dirname}"]
                            }
                        }
                    }
                }
            },
        }
        # Convert dict to TOML string
        toml_bytes = tomli_w.dumps(pyproject_content).encode("utf-8")

        # Add operation to transaction manager
        relative_config_path = config_path.relative_to(root_path)
        tm.add_write(str(relative_config_path), toml_bytes.decode("utf-8"))

        return True
~~~~~

#### Acts 3: 迁移运行器 (Runner) 逻辑

最后，我们将 `GenerateRunner` 移动到新包的 `runners.py` 模块，并更新其导入路径。

~~~~~act
write_file
packages/stitcher-stubgen/src/stitcher/stubgen/runners.py
~~~~~
~~~~~python
from typing import List, Optional
from pathlib import Path

from stitcher.common import bus
from needle.pointer import L
from stitcher.config import StitcherConfig
from typing import Dict

from stitcher.spec import (
    ModuleDef,
    StubGeneratorProtocol,
    LanguageTransformerProtocol,
    DocstringRendererProtocol,
)
from stitcher.app.services import (
    DocumentManager,
    ScannerService,
)
from stitcher.common.transaction import TransactionManager
from .services import StubPackageManager


class GenerateRunner:
    def __init__(
        self,
        root_path: Path,
        scanner: ScannerService,
        doc_manager: DocumentManager,
        stub_pkg_manager: StubPackageManager,
        generator: StubGeneratorProtocol,
        transformer: LanguageTransformerProtocol,
    ):
        self.root_path = root_path
        self.scanner = scanner
        self.doc_manager = doc_manager
        self.stub_pkg_manager = stub_pkg_manager
        self.generator = generator
        self.transformer = transformer
        self.renderer: Optional[DocstringRendererProtocol] = None

    def set_renderer(self, renderer: DocstringRendererProtocol) -> None:
        self.renderer = renderer

    def _render_docs_for_module(self, module: ModuleDef) -> Dict[str, str]:
        docs = {}
        if not self.renderer:
            return {}

        # Module doc
        if module.docstring_ir:
            docs["__doc__"] = self.renderer.render(module.docstring_ir, context=module)

        # Functions
        for func in module.functions:
            if func.docstring_ir:
                docs[func.name] = self.renderer.render(func.docstring_ir, context=func)

        # Classes
        for cls in module.classes:
            if cls.docstring_ir:
                docs[cls.name] = self.renderer.render(cls.docstring_ir, context=cls)
            # Methods
            for method in cls.methods:
                if method.docstring_ir:
                    fqn = f"{cls.name}.{method.name}"
                    docs[fqn] = self.renderer.render(
                        method.docstring_ir, context=method
                    )

        return docs

    def _scaffold_stub_package(
        self,
        config: StitcherConfig,
        stub_base_name: Optional[str],
        tm: TransactionManager,
    ):
        if not config.stub_package or not stub_base_name:
            return
        pkg_path = self.root_path / config.stub_package
        package_namespace: str = ""
        for path_str in config.scan_paths:
            path_parts = Path(path_str).parts
            if path_parts and path_parts[-1] != "src":
                # This handles cases like 'src/my_app' where 'my_app' is the namespace.
                package_namespace = path_parts[-1]
                break

        if not package_namespace:
            # Fallback for when all scan_paths end in 'src'.
            # Derives namespace from the target name (e.g., 'stitcher-cli' -> 'stitcher').
            package_namespace = stub_base_name.split("-")[0]
        stub_pkg_name = f"{stub_base_name}-stubs"
        bus.info(L.generate.stub_pkg.scaffold, name=stub_pkg_name)
        created = self.stub_pkg_manager.scaffold(
            pkg_path, stub_base_name, package_namespace, tm, self.root_path
        )
        if created:
            bus.success(L.generate.stub_pkg.success, name=stub_pkg_name)
        else:
            bus.info(L.generate.stub_pkg.exists, name=stub_pkg_name)

    def run_batch(
        self,
        modules: List[ModuleDef],
        config: StitcherConfig,
        tm: TransactionManager,
        project_name: Optional[str] = None,
    ) -> List[Path]:
        generated_files: List[Path] = []
        created_py_typed: set[Path] = set()

        if config.stub_package:
            stub_base_name = config.name if config.name != "default" else project_name
            self._scaffold_stub_package(config, stub_base_name, tm)

        for module in modules:
            self.doc_manager.apply_docs_to_module(module)

            # Phase 1: Generate Skeleton
            skeleton_code = self.generator.generate(module)

            # Phase 2: Render Docs
            docs_map = self._render_docs_for_module(module)

            # Phase 3: Inject Docs
            final_content = self.transformer.inject(skeleton_code, docs_map)

            if config.stub_package:
                logical_path = self.scanner.derive_logical_path(module.file_path)
                stub_logical_path = self.stub_pkg_manager._get_pep561_logical_path(
                    logical_path
                )
                output_path = (
                    self.root_path
                    / config.stub_package
                    / "src"
                    / stub_logical_path.with_suffix(".pyi")
                )
                if stub_logical_path.parts:
                    top_level_pkg_dir = (
                        self.root_path
                        / config.stub_package
                        / "src"
                        / stub_logical_path.parts[0]
                    )
                    if top_level_pkg_dir not in created_py_typed:
                        py_typed_path = top_level_pkg_dir / "py.typed"
                        tm.add_write(str(py_typed_path.relative_to(self.root_path)), "")
                        created_py_typed.add(top_level_pkg_dir)
            elif config.stub_path:
                logical_path = self.scanner.derive_logical_path(module.file_path)
                output_path = (
                    self.root_path / config.stub_path / logical_path.with_suffix(".pyi")
                )
            else:
                output_path = self.root_path / Path(module.file_path).with_suffix(
                    ".pyi"
                )

            relative_path = output_path.relative_to(self.root_path)

            if config.stub_package:
                src_root = self.root_path / config.stub_package / "src"
                current = output_path.parent
                while current != src_root and src_root in current.parents:
                    init_path = current / "__init__.pyi"
                    tm.add_write(str(init_path.relative_to(self.root_path)), "")
                    current = current.parent

            tm.add_write(str(relative_path), final_content)
            bus.success(L.generate.file.success, path=relative_path)
            generated_files.append(output_path)
        return generated_files
~~~~~

### 下一步建议

我们已成功将所有与存根生成相关的逻辑代码复制到了新的 `stitcher-stubgen` 包中。目前，代码存在于两个地方。

下一步是执行**第 3 步和第 4 步：定义新服务接口并重构消费方**。我将生成一个计划来：
1.  在 `stitcher-stubgen` 中创建一个高级别的 `StubgenService` 外观类。
2.  修改 `stitcher-application` 中的 `StitcherApp`，使其不再使用本地的 `GenerateRunner`，而是调用新的 `StubgenService`。
3.  在完成切换后，最后一步将是删除 `stitcher-application` 和 `stitcher-python-adapter` 中被废弃的旧文件。
