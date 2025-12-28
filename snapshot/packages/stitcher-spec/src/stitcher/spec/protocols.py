from typing import Protocol, Dict, Union
from .models import ModuleDef, FunctionDef, ClassDef
from .fingerprint import Fingerprint


class LanguageParserProtocol(Protocol):
    """
    Defines the contract for parsing source code into Stitcher's IR (ModuleDef).
    """

    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
        """
        Parse the given source code string into a ModuleDef intermediate representation.

        Args:
            source_code: The raw source code of the file.
            file_path: Optional relative path for error reporting and metadata.
        """
        ...


class LanguageTransformerProtocol(Protocol):
    """
    Defines the contract for performing lossless code transformations (Strip/Inject).
    """

    def strip(self, source_code: str) -> str:
        """
        Remove all docstrings from the source code while preserving layout/comments.
        """
        ...

    def inject(self, source_code: str, docs: Dict[str, str]) -> str:
        """
        Inject docstrings into the source code based on a mapping of FQNs to doc content.

        Args:
            source_code: The original source code.
            docs: A dictionary mapping Fully Qualified Names (e.g. "MyClass.method")
                  to the desired docstring content.
        """
        ...


class FingerprintStrategyProtocol(Protocol):
    """
    Defines the strategy for computing composite fingerprints for code entities.
    
    This protocol encourages a 'Composition over Inheritance' approach.
    Implementations should act as coordinators that delegate to multiple 
    specific hashers (e.g., StructureHasher, ASTHasher) and merge their results.
    """

    def compute(self, entity: Union[FunctionDef, ClassDef]) -> Fingerprint:
        """
        Compute a composite Fingerprint containing various stability hashes and 
        representations for the given entity.

        The returned Fingerprint object acts as a container for all calculated 
        metrics (e.g., 'current_code_structure_hash', 'current_code_ast_hash').
        """
        ...


class StubGeneratorProtocol(Protocol):
    """
    Defines the contract for generating type stub files from Stitcher's IR.
    """

    def generate(self, module: ModuleDef) -> str:
        """
        Generate the content of a type stub file (e.g. .pyi) from the ModuleDef IR.
        """
        ...