import textwrap


def parse_docstring(raw_docstring: str) -> str:
    """
    Parses a raw docstring from source code into its clean, canonical form.

    This is the inverse of `format_docstring`. It removes outer quotes and
    common leading whitespace from multiline strings.

    Args:
        raw_docstring: The raw string literal, including quotes.

    Returns:
        The clean, dedented content of the docstring.
    """
    # This logic assumes the input is a valid docstring literal string.
    # It's not a full Python parser, but handles common cases from CST/AST.
    content = raw_docstring.strip()

    # Naively strip matching triple quotes
    if content.startswith('"""') and content.endswith('"""'):
        content = content[3:-3]
    elif content.startswith("'''") and content.endswith("'''"):
        content = content[3:-3]
    # Naively strip matching single quotes
    elif content.startswith('"') and content.endswith('"'):
        content = content[1:-1]
    elif content.startswith("'") and content.endswith("'"):
        content = content[1:-1]

    # Dedent and strip any leading/trailing blank lines that result
    return textwrap.dedent(content).strip()


def format_docstring(content: str, indent_str: str) -> str:
    """
    Formats a clean docstring into a raw string literal for source code insertion.

    This is the inverse of `parse_docstring`. It follows ruff/black style.

    Args:
        content: The clean, canonical content of the docstring.
        indent_str: The indentation string to apply to the docstring block.

    Returns:
        The formatted, quoted, and indented docstring literal.
    """
    # Strip leading/trailing whitespace from the docstring itself to handle
    # potential formatting from YAML loader.
    content = content.strip()
    lines = content.split("\n")

    if len(lines) == 1:
        # Single line: keep it compact and escape internal quotes
        processed_doc = content.replace('"""', '\\"\\"\\"')
        return f'"""{processed_doc}"""'

    # Multi-line: adopt the ruff/black style for readability
    # Re-indent all lines to match the current level.
    # Note: The start quotes do NOT have indentation here, as that is handled
    # by the caller (StubGenerator) or the AST wrapper (LibCST).
    # However, internal lines MUST have the indentation.
    indented_body = "\n".join(f"{indent_str}{line}" for line in lines)
    return f'"""\n{indented_body}\n{indent_str}"""'