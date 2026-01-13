from typing import Dict
import networkx as nx

from stitcher.spec import IndexStoreProtocol


class GraphBuilder:
    def build_dependency_graph(self, store: IndexStoreProtocol) -> nx.DiGraph:
        """
        Builds a file-level dependency graph from the index store.

        Nodes: File paths (str)
        Edges: Represent an import from source file to target file.
        """
        graph = nx.DiGraph()
        fqn_to_path_cache: Dict[str, str | None] = {}

        # 1. Add all source files as nodes
        all_files = store.get_all_files()
        for file_record in all_files:
            graph.add_node(file_record.path)

        # 2. Add edges based on import references
        all_edges = store.get_all_dependency_edges()
        for edge in all_edges:
            source_path = edge.source_path
            target_fqn = edge.target_fqn

            # Skip if we've already processed this FQN and found it unresolvable
            if target_fqn in fqn_to_path_cache and fqn_to_path_cache[target_fqn] is None:
                continue

            # Resolve FQN to a file path
            if target_fqn not in fqn_to_path_cache:
                symbol_result = store.find_symbol_by_fqn(target_fqn)
                if symbol_result:
                    _, target_path = symbol_result
                    fqn_to_path_cache[target_fqn] = target_path
                else:
                    # Mark as unresolvable (likely an external library)
                    fqn_to_path_cache[target_fqn] = None

            target_path = fqn_to_path_cache.get(target_fqn)

            # Add edge if the target is an internal, resolved file
            if target_path and source_path != target_path:
                graph.add_edge(source_path, target_path)

        return graph