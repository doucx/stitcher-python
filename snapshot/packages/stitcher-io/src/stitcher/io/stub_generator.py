from typing import List
from stitcher.spec import (
    ModuleDef,
    FunctionDef,
    ClassDef,
    Attribute,
    Argument,
    ArgumentKind,
)


class StubGenerator:
    def generate(self, module: ModuleDef) -> str:
        """
        Generates the content of a .pyi file from a ModuleDef IR.
        """
        parts = []

        if module.docstring:
            parts.append(f'"""{module.docstring}"""')

        if module.attributes:
            if parts:
                parts.append("")  # Add a blank line
            for attr in module.attributes:
                parts.append(self._generate_attribute(attr))
        
        if module.functions:
            for func in module.functions:
                if parts:
                    parts.append("\n")
                parts.append(self._generate_function(func))

        if module.classes:
            for cls in module.classes:
                if parts:
                    parts.append("\n")
                parts.append(self._generate_class(cls))

        return "\n".join(parts)

    def _generate_attribute(self, attr: Attribute, indent_level: int = 0) -> str:
        indent = "    " * indent_level
        if attr.annotation:
            return f"{indent}{attr.name}: {attr.annotation}"
        return f"{indent}{attr.name}: ..."

    def _generate_arguments(self, args: List[Argument]) -> str:
        parts = []
        for arg in args:
            part = arg.name
            if arg.annotation:
                part += f": {arg.annotation}"
            if arg.default:
                part += f" = {arg.default}"
            parts.append(part)
        return ", ".join(parts)

    def _generate_function(self, func: FunctionDef, indent_level: int = 0) -> str:
        indent = "    " * indent_level
        lines = []

        # Decorators
        for dec in func.decorators:
            lines.append(f"{indent}{dec}")
        
        # Signature
        signature = f"{indent}"
        if func.is_async:
            signature += "async "
        signature += f"def {func.name}({self._generate_arguments(func.args)})"
        if func.return_annotation:
            signature += f" -> {func.return_annotation}"
        
        # Body
        if func.docstring:
            signature += ":"
            lines.append(signature)
            docstring_indent = "    " * (indent_level + 1)
            lines.append(f'{docstring_indent}"""{func.docstring}"""')
            lines.append(f"{docstring_indent}...")
        else:
            signature += ": ..."
            lines.append(signature)

        return "\n".join(lines)

    def _generate_class(self, cls: ClassDef, indent_level: int = 0) -> str:
        indent = "    " * indent_level
        lines = []

        # Class header
        bases = f"({', '.join(cls.bases)})" if cls.bases else ""
        lines.append(f"{indent}class {cls.name}{bases}:")

        child_indent_level = indent_level + 1
        child_indent = "    " * child_indent_level
        
        # Docstring
        if cls.docstring:
            lines.append(f'{child_indent}"""{cls.docstring}"""')

        # Attributes and methods
        body_parts = []
        if cls.attributes:
            for attr in cls.attributes:
                body_parts.append(self._generate_attribute(attr, child_indent_level))

        if cls.methods:
            for method in cls.methods:
                if body_parts:
                     # Add a blank line between attributes and first method, or between methods
                     body_parts.append("")
                body_parts.append(self._generate_function(method, child_indent_level))
        
        if not body_parts:
            lines.append(f"{child_indent}...")
        else:
            lines.extend(body_parts)

        return "\n".join(lines)