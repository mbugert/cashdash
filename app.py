from typing import Optional

import click

from cashdash import create_app


@click.command()
@click.option(
    "--backend",
    type=click.STRING,
    help='Backend for Sankey diagrams, "cvxpy" or "minizinc"',
)
@click.argument("data_path", type=click.Path(exists=True, dir_okay=False))
def run(data_path, backend: Optional[str] = None):
    app = create_app(data_path, backend=backend)
    app.run(debug=True, port="8080", host="0.0.0.0")


if __name__ == "__main__":
    run()

# TODO
#   - wishlist:
#      - colors for cashflow from sample_books account colors
#      - load multiple files at once
#      - persist interesting settings
#      - when not using CLI, offer large drag & drop area
#      - put some effort in UI
