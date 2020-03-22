import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from anytree import PostOrderIter
from anytree.search import find
from dash import Dash
from dash.dependencies import Output, Input
from plotly import graph_objects as go

from cashdash.dashes.base import DashBlueprintFactory
from cashdash.data import (
    BookData,
    TYPE,
    ACCOUNT,
    NAME,
    TRANSACTION,
    DATE,
    VALUE,
    EXPENSE,
)

EXPENSES_GRAPH = "expenses-graph"
DATE_AGGREGATION = "date-aggregation"
ACCOUNTS_SELECTION = "accounts-selection"


class ExpensesDashFactory(DashBlueprintFactory):
    """
    Flexible bar chart of transactions from expense-type accounts.
    """

    def get_dash_name(self) -> str:
        return "Expenses"

    def _setup_dash(self, dash: Dash, data: BookData):
        accounts, transactions, splits = data.accounts, data.transactions, data.splits

        # Iterate over the account tree to create the account dropdown options.
        account_dropdown_options = []
        visited = set()
        is_expense_acc = lambda node: data.accounts.at[node.name, TYPE] == EXPENSE
        for node in PostOrderIter(data.account_hierarchy, filter_=is_expense_acc):
            guid = node.name
            account_has_transactions = len(splits.loc[splits[ACCOUNT] == guid]) > 0

            # All leaf accounts with at least one transaction are included. All inner accounts in the hierarchy where
            # at least one child account has a transaction are included as well.
            if account_has_transactions or any(
                child in visited for child in node.children
            ):
                # kludge for indenting accounts which are deeper in the hierarchy via non-breaking spaces
                option = {
                    "label": u"\u00a0\u00a0" * (node.depth - 1)
                    + accounts.at[guid, NAME],
                    "value": guid,
                }
                account_dropdown_options.append(option)
                visited.add(node)
        # reverse options to negate post-order traversal
        account_dropdown_options = account_dropdown_options[::-1]

        account_dropdown = dcc.Dropdown(
            id=ACCOUNTS_SELECTION, options=account_dropdown_options, multi=True
        )

        date_aggregation_dropdown = dcc.Dropdown(
            id=DATE_AGGREGATION,
            options=[
                {"label": s, "value": s}
                for s in ["Day", "Week", "Month", "Quarter", "Year", "Decade"]
            ],
            value="Month",
        )

        dash.layout = html.Div(
            className="container-fluid mt-2",
            children=html.Div(
                className="row",
                children=[
                    html.Div(
                        className="col-md-3",
                        children=[
                            html.Div(
                                className="form-group",
                                children=[
                                    html.Label("Accounts", htmlFor=ACCOUNTS_SELECTION),
                                    account_dropdown,
                                ],
                            ),
                            html.Div(
                                className="form-group",
                                children=[
                                    html.Label(
                                        "Aggregate by", htmlFor=DATE_AGGREGATION
                                    ),
                                    date_aggregation_dropdown,
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="col-md-9",
                        children=[dcc.Loading(children=dcc.Graph(id=EXPENSES_GRAPH))],
                    ),
                ],
            ),
        )

        def update(date_aggregation, selected_accounts) -> go.Figure:
            date_settings = {
                "Day": ("D", "%d.%m.%y"),
                "Week": ("W", "W%W %Y"),
                "Month": ("MS", "%B %y"),
                "Quarter": ("Q", "Q%q %Y"),
                "Year": ("Y", "%Y"),
                "Decade": ("10Y", "%Y"),
            }
            # TODO ticks for anything but month are still off
            rule, tick_format = date_settings[date_aggregation]

            # set up one set of bars for each selected account
            bars = []
            if selected_accounts:
                for account in selected_accounts:
                    # For any selected account, we want to sum up the transactions of the account's subtree in the
                    # account hierarchy.
                    subtree_transactions = []
                    # Identify the node corresponding to the account:
                    account_node = find(
                        data.account_hierarchy,
                        filter_=lambda node: node.name == account,
                    )
                    for subaccount_node in PostOrderIter(
                        account_node, filter_=is_expense_acc
                    ):
                        # Obtain splits of this subaccount, merge with transactions to obtain date information
                        splits_of_subaccount = splits.loc[
                            splits[ACCOUNT] == subaccount_node.name
                        ]
                        transactions_of_subaccount = splits_of_subaccount.merge(
                            transactions, left_on=TRANSACTION, right_index=True
                        )
                        subtree_transactions.append(transactions_of_subaccount)
                    subtree_transactions = pd.concat(subtree_transactions)

                    # Aggregate by day per default, doesn't make much sense to go any more fine-grained because the
                    # finest that sample_books goes are days
                    transactions_per_day = subtree_transactions.groupby(DATE).sum()
                    # Apply aggregation to weeks, months, etc.
                    transactions_resampled = (
                        transactions_per_day[VALUE].resample(rule).sum()
                    )

                    account_name = accounts.at[account, NAME]
                    bars.append(
                        go.Bar(
                            x=transactions_resampled.index.to_pydatetime(),
                            y=transactions_resampled.values,
                            name=account_name,
                        )
                    )

            fig = go.Figure(layout_title_text="Expenses over time")
            for bar in bars:
                fig.add_trace(bar)

            fig.update_layout(
                barmode="stack",
                yaxis=go.layout.YAxis(ticksuffix="€"),
                # Add range slider
                xaxis=go.layout.XAxis(
                    rangeselector=dict(
                        buttons=list(
                            [
                                dict(
                                    count=1,
                                    label="1m",
                                    step="month",
                                    stepmode="backward",
                                ),
                                dict(
                                    count=6,
                                    label="6m",
                                    step="month",
                                    stepmode="backward",
                                ),
                                dict(
                                    count=1, label="YTD", step="year", stepmode="todate"
                                ),
                                dict(
                                    count=1,
                                    label="1y",
                                    step="year",
                                    stepmode="backward",
                                ),
                                dict(step="all"),
                            ]
                        )
                    ),
                    rangeslider=dict(visible=True),
                    type="date",
                    tickformat=tick_format,
                    tickson="boundaries",
                ),
            )
            return fig

        dash.callback(
            Output(EXPENSES_GRAPH, "figure"),
            [Input(DATE_AGGREGATION, "value"), Input(ACCOUNTS_SELECTION, "value")],
        )(update)
