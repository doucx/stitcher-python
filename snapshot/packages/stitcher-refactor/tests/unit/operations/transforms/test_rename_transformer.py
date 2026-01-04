import textwrap
from stitcher.refactor.operations.transforms.rename_transformer import apply_rename_transformer


def test_apply_rename_transformer():
    # 1. Setup
    source_code = textwrap.dedent("""
        from old_lib import old_func
        
        def main():
            result = old_func()
            return result
    """)
    
    rename_map = {"old_func": "new_func"}
    
    # These locations correspond to the start of 'old_func' tokens
    # (line, column), 0-indexed internally by LibCST but 1-indexed for humans.
    # LibCST Position is 1-indexed for lines, 0-indexed for columns.
    locations_to_modify = {
        (1, 20),  # from old_lib import old_func
        (4, 13),  # result = old_func()
    }

    # 2. Execute
    modified_code = apply_rename_transformer(source_code, rename_map, locations_to_modify)

    # 3. Verify
    expected_code = textwrap.dedent("""
        from old_lib import new_func
        
        def main():
            result = new_func()
            return result
    """)
    
    assert modified_code == expected_code