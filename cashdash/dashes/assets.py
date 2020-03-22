import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from dash import Dash
from plotly import graph_objects as go

from cashdash.dashes.base import DashBlueprintFactory
from cashdash.data import (
    BookData,
    ACCOUNT,
    NAME,
    TRANSACTION,
    DATE,
    VALUE,
    TYPE,
    CASH,
    ASSET,
    BANK,
)

# TODO y start on plots looks like data is wrong
class AssetDashFactory(DashBlueprintFactory):
    """
    Stacked area chart of transactions in asset accounts.
    """

    def get_dash_name(self) -> str:
        return "Assets"

    def _setup_dash(self, dash: Dash, data: BookData) -> None:
        accounts, transactions, splits = data.accounts, data.transactions, data.splits

        # find cash, asset, bank accounts
        asset_accounts = accounts.loc[accounts[TYPE].isin([CASH, ASSET, BANK])]

        # We want a stacked area chart. For this to work, all lines need common x values (== dates). We therefore look
        # up all transactions of ASSET and CASH accounts, concat them into a common DF and then create one line per
        # account.
        asset_account_transactions = []
        asset_account_names = []
        for account_guid, row in asset_accounts.iterrows():
            # look up splits and join with transactions to obtain date information
            splits_of_account = splits.loc[splits[ACCOUNT] == account_guid]
            if splits_of_account.empty:
                continue
            transactions_of_account = splits_of_account.merge(
                transactions, left_on=TRANSACTION, right_index=True
            )
            transactions_of_account = transactions_of_account.groupby(
                DATE
            ).sum()  # aggregate for one day, use date as index

            asset_account_transactions.append(transactions_of_account[VALUE])
            asset_account_names.append(accounts.at[account_guid, NAME])
        common_index = pd.concat(asset_account_transactions, axis=1).fillna(0)
        common_index.columns = asset_account_names

        # create lines
        lines = []
        for column in common_index:
            trace = go.Scatter(
                x=common_index.index.to_pydatetime(),
                y=common_index[column].cumsum(),
                mode="lines",
                line_shape="hv",
                stackgroup="default",
                name=column,
            )
            lines.append(trace)

        fig = go.Figure(data=lines, layout_title_text="Assets over time")
        fig.update_layout(
            xaxis=go.layout.XAxis(
                rangeselector=dict(
                    buttons=list(
                        [
                            dict(
                                count=1, label="1m", step="month", stepmode="backward"
                            ),
                            dict(
                                count=6, label="6m", step="month", stepmode="backward"
                            ),
                            dict(count=1, label="YTD", step="year", stepmode="todate"),
                            dict(count=1, label="1y", step="year", stepmode="backward"),
                            dict(step="all"),
                        ]
                    )
                ),
                rangeslider=dict(visible=True),
                type="date",
                tickson="boundaries",
            )
        )

        dash.layout = html.Div(
            children=[dcc.Loading(children=dcc.Graph(id="assets-graph", figure=fig))]
        )
