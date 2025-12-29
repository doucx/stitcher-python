import ast
import griffe
from typing import List, Optional, Any
from stitcher.spec import (
    ModuleDef,
    LanguageParserProtocol,
    FunctionDef,
    Argument,
    ArgumentKind,
    ClassDef,
    Attribute
)


class GriffePythonParser(LanguageParserProtocol):
    """
    A Python parser implementation using Griffe.
    """

    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
        """
        Parses the given source code into a Stitcher ModuleDef IR using Griffe.
        """
        # 1. Parse into AST
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            # Wrap SyntaxError or let it bubble? For now, standard behavior.
            raise ValueError(f"Syntax error in {file_path}: {e}") from e

        # 2. Visit with Griffe
        # We use a virtual module name based on file path or default
        module_name = file_path.replace("/", ".").replace(".py", "") or "module"
        griffe_module = griffe.visit(module_name, filepath=None, code=source_code)

        # 3. Map to Stitcher IR
        return self._map_module(griffe_module, file_path)

    def _map_module(self, gm: griffe.Module, file_path: str) -> ModuleDef:
        functions = []
        # Filter and map top-level functions
        for member in gm.members.values():
            if member.is_function:
                functions.append(self._map_function(member))
            # TODO: Add Class handling in next iteration
            # if member.is_class:
            #     classes.append(self._map_class(member))

        # TODO: Extract module-level docstring and attributes
        # Griffe module docstring parsing
        docstring = gm.docstring.value if gm.docstring else None

        return ModuleDef(
            file_path=file_path,
            docstring=docstring,
            functions=functions,
            # Placeholders for future iterations
            classes=[],
            attributes=[],
            imports=[]
        )

    def _map_function(self, gf: griffe.Function) -> FunctionDef:
        args = [self._map_argument(p) for p in gf.parameters]
        
        # Griffe stores return annotation object, we need source string or name
        return_annotation = None
        if gf.returns:
            # gf.returns is typically an ExprName or similar. We want the string representation.
            # Griffe < 1.0 might act differently, assuming modern/stable API behavior:
            # We use .source or try to stringify
             return_annotation = str(gf.returns)

        docstring = gf.docstring.value if gf.docstring else None

        return FunctionDef(
            name=gf.name,
            args=args,
            return_annotation=return_annotation,
            docstring=docstring,
            is_async="async" in gf.labels,
            decorators=[str(d.value) for d in gf.decorators],
            is_static="staticmethod" in gf.labels,
            is_class="classmethod" in gf.labels,
        )

    def _map_argument(self, param: griffe.Parameter) -> Argument:
        # Map Kind
        # Griffe kind is usually string-like or inspect.Parameter.kind compatible
        kind_map = {
            "positional-only": ArgumentKind.POSITIONAL_ONLY,
            "positional-or-keyword": ArgumentKind.POSITIONAL_OR_KEYWORD,
            "keyword-only": ArgumentKind.KEYWORD_ONLY,
            "variadic positional": ArgumentKind.VAR_POSITIONAL,
            "variadic keyword": ArgumentKind.VAR_KEYWORD,
        }
        
        # Griffe's kind.value (if enum) or str(kind) needs to be checked
        # griffe.ParameterKind is an Enum.
        st_kind = ArgumentKind.POSITIONAL_OR_KEYWORD # Default
        if param.kind:
             # Convert Griffe kind to our enum. 
             # Logic simplifies depending on Griffe version. 
             # We assume param.kind.name or param.kind.value matches convention
             slug = str(param.kind.value)
             st_kind = kind_map.get(slug, ArgumentKind.POSITIONAL_OR_KEYWORD)

        annotation = str(param.annotation) if param.annotation else None
        default = str(param.default) if param.default else None

        return Argument(
            name=param.name,
            kind=st_kind,
            annotation=annotation,
            default=default
        )