from typing import List, cast
from pathlib import Path
import griffe.expressions
from griffe.loader import GriffeLoader
from griffe.dataclasses import (
    Module as GriffeModule,
    Class as GriffeClass,
    Function as GriffeFunction,
    Attribute as GriffeAttribute,
    Kind,
)

from stitcher.spec import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
    SourceLocation,
    SourcePosition,
)


class GriffePythonParser:
    """A parser that uses Griffe to generate a ModuleDef IR."""

    def __init__(self):
        self._loader = GriffeLoader()

    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
        """Parse source code into a ModuleDef."""
        try:
            # Griffe's parse method is better for in-memory content
            module = self._loader.load_module(Path(file_path))
        except Exception:
            # Fallback for syntax errors or issues
            return ModuleDef(file_path=file_path)
        return self._map_module(module)

    def _get_location(self, obj) -> SourceLocation:
        """Extracts location from a Griffe object."""
        return SourceLocation(
            start=SourcePosition(line=obj.lineno, column=obj.col_offset),
            end=SourcePosition(line=obj.end_lineno or obj.lineno, column=obj.end_col_offset or 0),
        )

    def _map_module(self, griffe_mod: GriffeModule) -> ModuleDef:
        """Map a Griffe Module to a ModuleDef."""
        imports: List[str] = []
        for imp in griffe_mod.imports:
            imports.append(str(imp))

        # Reconstruct dunder_all from the Griffe attribute
        dunder_all_attr = griffe_mod.attributes.get("__all__")
        dunder_all_val = dunder_all_attr.value if dunder_all_attr else None

        return ModuleDef(
            file_path=str(griffe_mod.filepath),
            docstring=griffe_mod.docstring.value if griffe_mod.docstring else None,
            attributes=[
                self._map_attribute(attr)
                for name, attr in griffe_mod.attributes.items()
                if not name.startswith("_")
            ],
            functions=[
                self._map_function(func) for func in griffe_mod.functions.values()
            ],
            classes=[self._map_class(cls) for cls in griffe_mod.classes.values()],
            imports=imports,
            dunder_all=dunder_all_val,
            location=self._get_location(griffe_mod),
        )

    def _map_attribute(self, griffe_attr: GriffeAttribute) -> Attribute:
        """Map a Griffe Attribute to an Attribute."""
        return Attribute(
            name=griffe_attr.name,
            annotation=griffe_attr.annotation_str,
            value=griffe_attr.value,
            docstring=griffe_attr.docstring.value if griffe_attr.docstring else None,
            location=self._get_location(griffe_attr),
        )

    def _map_class(self, griffe_cls: GriffeClass) -> ClassDef:
        """Map a Griffe Class to a ClassDef."""
        return ClassDef(
            name=griffe_cls.name,
            bases=[base.name for base in griffe_cls.bases],
            decorators=[str(d.callable) for d in griffe_cls.decorators],
            docstring=griffe_cls.docstring.value if griffe_cls.docstring else None,
            attributes=[
                self._map_attribute(attr) for attr in griffe_cls.attributes.values()
            ],
            methods=[self._map_function(func) for func in griffe_cls.functions.values()],
            location=self._get_location(griffe_cls),
        )

    def _map_function(self, griffe_func: GriffeFunction) -> FunctionDef:
        """Map a Griffe Function to a FunctionDef."""

        def _map_arg_kind(kind: Kind) -> ArgumentKind:
            mapping = {
                Kind.POSITIONAL_ONLY: ArgumentKind.POSITIONAL_ONLY,
                Kind.POSITIONAL_OR_KEYWORD: ArgumentKind.POSITIONAL_OR_KEYWORD,
                Kind.VAR_POSITIONAL: ArgumentKind.VAR_POSITIONAL,
                Kind.KEYWORD_ONLY: ArgumentKind.KEYWORD_ONLY,
                Kind.VAR_KEYWORD: ArgumentKind.VAR_KEYWORD,
            }
            return mapping.get(kind, ArgumentKind.POSITIONAL_OR_KEYWORD)

        args = [
            Argument(
                name=param.name,
                kind=_map_arg_kind(param.kind),
                annotation=str(param.annotation) if param.annotation else None,
                default=param.default,
            )
            for param in griffe_func.parameters
        ]

        # Check for staticmethod/classmethod decorators
        is_static = any("staticmethod" in str(d.callable) for d in griffe_func.decorators)
        is_class = any("classmethod" in str(d.callable) for d in griffe_func.decorators)

        return FunctionDef(
            name=griffe_func.name,
            args=args,
            return_annotation=str(griffe_func.returns)
            if griffe_func.returns is not None
            else None,
            decorators=[str(d.callable) for d in griffe_func.decorators],
            docstring=griffe_func.docstring.value if griffe_func.docstring else None,
            is_async=griffe_func.is_async,
            is_static=is_static,
            is_class=is_class,
            location=self._get_location(griffe_func),
        )
