from textwrap import dedent
from stitcher.test_utils import WorkspaceFactory, create_test_app


def test_generate_with_google_style_renders_correctly(tmp_path):
    """
    E2E test to verify that setting docstring_style = "google" in pyproject.toml
    results in a correctly rendered .pyi file with merged type and doc info.
    """
    project_root = (
        WorkspaceFactory(tmp_path)
        .with_config({"scan_paths": ["src"], "docstring_style": "google"})
        .with_source(
            "src/main.py",
            "def calculate(value: int, multiplier: float = 1.0) -> float: ...",
        )
        .with_docs(
            "src/main.stitcher.yaml",
            {
                "calculate": {
                    "Summary": "Performs a calculation.",
                    "Args": {
                        "value": "The input integer.",
                        "multiplier": "The factor to multiply by.",
                    },
                    "Returns": {"float": "The calculated result."},
                }
            },
        )
        .build()
    )

    app = create_test_app(root_path=project_root)
    app.run_from_config()

    pyi_path = project_root / "src/main.pyi"
    assert pyi_path.exists()

    expected_content = dedent(
        '''
        def calculate(value: int, multiplier: float = 1.0) -> float:
            """
            Performs a calculation.

            Args:
                value (int): The input integer.
                multiplier (float): The factor to multiply by.

            Returns:
                float: The calculated result.
            """
            ...
        '''
    ).strip()

    actual_content = pyi_path.read_text().strip()
    assert actual_content == expected_content
