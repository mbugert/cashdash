from collections import OrderedDict
from pathlib import Path
from typing import Optional

from flask import Flask, render_template

from cashdash.dashes import *
from cashdash.data.gnucash import GnucashXmlBookDataReader


def create_app(data_path: str, backend: Optional[str] = None):
    resources_root = Path(__file__).parent / "resources"
    static_folder = resources_root / "static"
    app = Flask(
        __name__,
        static_folder=static_folder,
        template_folder=resources_root / "templates",
    )
    app.url_map.strict_slashes = False

    reader = GnucashXmlBookDataReader()
    data = reader.read(data_path)

    # TODO this should also be configurable via command line or settings
    data.remove_book_closing_transactions()

    dashes = [
        ("/assets", AssetDashFactory()),
        ("/expenses", ExpensesDashFactory()),
        ("/cashflow", CashflowDashFactory(backend)),
    ]

    navigation = OrderedDict((url, factory.get_dash_name()) for url, factory in dashes)

    # create all dashes
    css_folder = static_folder / "css"
    for url, factory in dashes:
        blueprint = factory.create_blueprint(data, navigation, str(css_folder))
        app.register_blueprint(blueprint, url_prefix=url)

    @app.route("/")
    def index():
        return render_template("index.html", navigation=navigation)

    return app
