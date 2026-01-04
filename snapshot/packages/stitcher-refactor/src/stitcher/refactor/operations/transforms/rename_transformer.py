from typing import Dict, Set, Tuple
import libcst as cst
import libcst.matchers as m
from libcst.metadata import PositionProvider


class SymbolRenamerTransformer(cst.CSTTransformer):
    """
    A LibCST transformer that renames symbols at specific locations.
    """
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, rename_map: Dict[str, str], locations_to_modify: Set[Tuple[int, int]]):
        self.rename_map = rename_map
        self.locations_to_modify = locations_to_modify

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        pos = self.get_metadata(PositionProvider, original_node)
        
        # Check if the start position of this Name node is one we need to modify
        if (pos.start.line, pos.start.column) in self.locations_to_modify:
            if original_node.value in self.rename_map:
                return updated_node.with_changes(value=self.rename_map[original_node.value])
        return updated_node


def apply_rename_transformer(
    source_code: str,
    rename_map: Dict[str, str],
    locations: Set[Tuple[int, int]],
) -> str:
    """
    Applies the SymbolRenamerTransformer to a given source code.
    """
    tree = cst.parse_module(source_code)
    wrapper = cst.MetadataWrapper(tree)
    transformer = SymbolRenamerTransformer(rename_map, locations)
    
    modified_tree = wrapper.visit(transformer)
    return modified_tree.code