from typing import OrderedDict

from dash import Dash
from flask import Blueprint, render_template
from flask.blueprints import BlueprintSetupState

from cashdash.data import BookData


class DashBlueprintFactory:
    dash_url: str = None

    def create_blueprint(self, data: BookData, navigation: OrderedDict) -> Blueprint:
        """
        :param data:
        :param navigation:
        :return:
        """
        bp = Blueprint("dash_" + self.get_dash_name(), __name__)

        # The best way to integrate Dash with a surrounding Flask application is to serve a Dash with the same Flask app
        # instance, then referencing it through an iframe. We host the Dash itself at '/<dash-name>/dash' (because it's
        # cleaner this way, but <dash-name> is only known once this blueprint is registered. Therefore, the wiring
        # happens in `Blueprint.record_once` and the iframe Dash URL is written to the class attribute `dash_url`.

        @bp.record_once
        def on_first_register(state: BlueprintSetupState):
            self.dash_url = state.url_prefix + "/dash/"
            dash = Dash(
                server=state.app,
                url_base_pathname=self.dash_url,
                external_stylesheets=["https://codepen.io/chriddyp/pen/bWLwgP.css"],
            )
            self._setup_dash(dash, data)

        @bp.route("/")
        def root():
            assert self.dash_url is not None
            return render_template(
                "dash_page.html",
                dash_url=self.dash_url,
                navigation=navigation,
                active_page=self.get_dash_name(),
            )

        return bp

    def _setup_dash(self, dash: Dash, data: BookData) -> None:
        """
        Set up the Dash layout, transform the data, etc.
        :param dash:
        :param data:
        """
        raise NotImplementedError

    def get_dash_name(self) -> str:
        """
        Return speaking name for this dash, to be shown in the navigation bar
        :return:
        """
        raise NotImplementedError
