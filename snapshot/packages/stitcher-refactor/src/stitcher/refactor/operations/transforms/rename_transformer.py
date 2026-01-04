import libcst as cst
from libcst.metadata import PositionProvider, CodeRange
from typing import Dict, List, Tuple, Optional
from stitcher.refactor.engine.graph import UsageLocation


class SymbolRenamerTransformer(cst.CSTTransformer):
    """
    A LibCST transformer that renames symbols at specific locations.
    It does NOT perform semantic analysis; it blindly trusts the provided locations.
    """
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, rename_map: Dict[str, str], target_locations: List[UsageLocation]):
        """
        Args:
            rename_map: Mapping from old_name to new_name.
                        Note: For simple Name nodes, this is just the identifier.
            target_locations: List of locations that MUST be renamed.
        """
        self.rename_map = rename_map
        self._location_index = self._build_location_index(target_locations)

    def _build_location_index(self, locations: List[UsageLocation]) -> Dict[Tuple[int, int], UsageLocation]:
        """
        Builds a lookup index (start_line, start_col) -> UsageLocation for O(1) access.
        """
        index = {}
        for loc in locations:
            # Griffe locations are usually 1-based for lines.
            # LibCST CodeRange is also 1-based for lines, 0-based for columns.
            # We assume UsageLocation stores data compatible with the parser we used (Griffe).
            # We'll use (start_line, start_col) as a unique key for "Name" nodes.
            key = (loc.lineno, loc.col_offset)
            index[key] = loc
        return index

    def _is_target(self, node: cst.CSTNode) -> Optional[str]:
        """
        Checks if the current node matches a target location.
        Returns the new name if it should be renamed, else None.
        """
        pos = self.get_metadata(PositionProvider, node)
        # pos is a CodeRange object: start=(line, col), end=(line, col)
        
        # Check exact match on start position
        # Note: We might need more fuzzy matching depending on how Griffe reports positions 
        # vs LibCST. For now, we assume exact match on start.
        key = (pos.start.line, pos.start.column)
        
        if key in self._location_index:
            # Found a match! Now we need to determine the new name.
            # In a real scenario, the UsageLocation might carry the specific transformation.
            # For this MVP, we look up the node's current value in the map.
            # But wait, rename_map is old->new. 
            
            # If the node is a Name, its value is the name.
            if isinstance(node, cst.Name):
                old_name = node.value
                return self.rename_map.get(old_name)
            
        return None

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        new_name = self._is_target(original_node)
        if new_name:
            return updated_node.with_changes(value=new_name)
        return updated_node

    # TODO: Add leave_Attribute, leave_ImportFrom, etc. in future iterations.