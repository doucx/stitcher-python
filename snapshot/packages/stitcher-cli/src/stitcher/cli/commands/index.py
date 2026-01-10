import typer
from stitcher.common import stitcher_operator as nexus
from needle.pointer import L
from stitcher.cli.factories import make_app


def index_build_command():
    app_instance = make_app()
    app_instance.run_index_build()