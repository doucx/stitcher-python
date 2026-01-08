import typer
from needle.pointer import L
from stitcher.common import bus, stitcher_operator as nexus
from stitcher.cli.factories import make_app


def generate_command(
    dry_run: bool = typer.Option(
        False, "--dry-run", help=nexus(L.cli.option.refactor_dry_run.help)
    ),
):
    app_instance = make_app()
    app_instance.run_from_config(dry_run=dry_run)


def init_command():
    app_instance = make_app()
    app_instance.run_init()


def strip_command(
    dry_run: bool = typer.Option(
        False, "--dry-run", help=nexus(L.cli.option.refactor_dry_run.help)
    ),
):
    if not dry_run and not typer.confirm(bus.render_to_string(L.strip.run.confirm)):
        bus.warning(L.strip.run.aborted)
        raise typer.Abort()

    app_instance = make_app()
    app_instance.run_strip(dry_run=dry_run)


def inject_command(
    dry_run: bool = typer.Option(
        False, "--dry-run", help=nexus(L.cli.option.refactor_dry_run.help)
    ),
):
    if not dry_run and not typer.confirm(bus.render_to_string(L.inject.run.confirm)):
        bus.warning(L.inject.run.aborted)
        raise typer.Abort()

    app_instance = make_app()
    app_instance.run_inject(dry_run=dry_run)