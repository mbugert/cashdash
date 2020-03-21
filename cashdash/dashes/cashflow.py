from datetime import datetime
from typing import List, Optional, Tuple

import anytree
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
from dash import Dash
from dash.dependencies import Output, Input, State
from plotly import graph_objects as go

from cashdash.algo.base import SOURCE, TARGET
from cashdash.algo.cvxpy_links import CvxpyLinkReconstructor
from cashdash.algo.zinc_links import ZincLinkReconstructor
from cashdash.dashes.base import DashBlueprintFactory
from cashdash.data import (
    BookData,
    ACCOUNT,
    NAME,
    TRANSACTION,
    VALUE,
    TYPE,
    BANK,
    CASH,
    ASSET,
    EQUITY,
    DESCRIPTION,
    LIABILITY,
    DATE,
)

# HTML component ids
SETTINGS_CHECKLIST = "settings-checklist"
AVERAGING_PICKER = "averaging-picker"
APPLY_BTN = "apply-btn"
CASHFLOW_GRAPH = "cashflow-graph"
ACCOUNT_EXCLUSIONS = "account-exclusions"
DATE_PICKER_RANGE = "date-picker-range"
TRANSACTION_EXCLUSIONS = "transaction-exclusions"

# additional settings
MERGE_ASSET_ACCOUNTS = "merge-asset-accounts"
TREAT_LIABILITIES_AS_ASSETS = "treat-liabilities-as-assets"

# averaging options
ABSOLUTE = "absolute"
YEARLY = "yearly"
QUARTERLY = "quarterly"
MONTHLY = "monthly"
WEEKLY = "weekly"


class CashflowDashFactory(DashBlueprintFactory):
    """
    Sankey diagram of income and expenses.
    """

    def __init__(self, backend: Optional[str]):
        if backend is None or backend == "cvxpy":
            self.link_reconstructor = CvxpyLinkReconstructor()
        elif backend == "minizinc":
            self.link_reconstructor = ZincLinkReconstructor()
        else:
            raise ValueError(f'Unknown backend "{backend}".')

    def get_dash_name(self) -> str:
        return "Cash Flow"

    @staticmethod
    def _filter_by_date(
        transactions: pd.DataFrame,
        splits: pd.DataFrame,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        # apply date range filtering
        if start_date is not None:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            transactions = transactions.loc[transactions[DATE] >= start_datetime]
        if end_date is not None:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
            transactions = transactions.loc[transactions[DATE] <= end_datetime]
        if start_date is not None or end_date is not None:
            # adjust splits if necessary
            splits = splits.loc[splits[TRANSACTION].isin(transactions.index)]
        return transactions, splits

    @staticmethod
    def _filter_by_account_blacklist(
        accounts: pd.DataFrame,
        transactions: pd.DataFrame,
        splits: pd.DataFrame,
        account_blacklist: Optional[List[str]],
    ):
        if account_blacklist is not None:
            accounts = accounts.loc[~accounts.index.isin(account_blacklist)]

        # identify transactions involving those accounts, then remove splits and transactions with those accounts
        ids_of_transactions_to_drop = splits.loc[
            ~splits[ACCOUNT].isin(accounts.index), TRANSACTION
        ]
        transactions = transactions.loc[
            ~transactions.index.isin(ids_of_transactions_to_drop)
        ]
        splits = splits.loc[splits[TRANSACTION].isin(transactions.index)]

        return accounts, transactions, splits

    def _setup_dash(self, dash: Dash, data: BookData) -> None:
        # create date range picker
        min_date_allowed = data.transactions[DATE].min().strftime("%Y-%m-%d")
        max_date_allowed = data.transactions[DATE].max().strftime("%Y-%m-%d")

        date_picker_range = dcc.DatePickerRange(
            id=DATE_PICKER_RANGE,
            display_format="DD.MM.YYYY",  # TODO locale-specific?
            min_date_allowed=min_date_allowed,
            max_date_allowed=max_date_allowed,
            start_date=min_date_allowed,
            end_date=max_date_allowed,
        )

        settings_checklist = dcc.Checklist(
            id=SETTINGS_CHECKLIST,
            value=[MERGE_ASSET_ACCOUNTS, TREAT_LIABILITIES_AS_ASSETS],
            options=[
                {"value": MERGE_ASSET_ACCOUNTS, "label": "Merge asset accounts"},
                {
                    "value": TREAT_LIABILITIES_AS_ASSETS,
                    "label": "Treat liabilities as assets",
                },
            ],
        )

        averaging_options = {
            YEARLY: ("yearly average", "Y"),
            QUARTERLY: ("quarterly average", "Q"),
            MONTHLY: ("monthly average", "M"),
            WEEKLY: ("weekly average", "W"),
            ABSOLUTE: ("no average (absolute)", None),
        }

        averaging_picker = dcc.RadioItems(
            id=AVERAGING_PICKER,
            options=[
                {"label": l, "value": v} for v, (l, _) in averaging_options.items()
            ],
            value=ABSOLUTE,
        )

        accounts, splits = data.accounts, data.splits
        accounts_w_transactions = accounts.loc[
            splits[ACCOUNT].unique(), NAME
        ].sort_values()
        account_exclusions = dcc.Dropdown(
            id=ACCOUNT_EXCLUSIONS,
            options=[
                {"label": l, "value": v}
                for l, v in zip(accounts_w_transactions, accounts_w_transactions.index)
            ],
            multi=True,
        )

        transaction_exclusions = dcc.Dropdown(id=TRANSACTION_EXCLUSIONS, multi=True)

        dash.layout = html.Div(
            children=[
                html.Label("Date Range"),
                date_picker_range,
                html.Label("Averaging"),
                averaging_picker,
                html.Label("Account to exclude"),
                account_exclusions,
                html.Label("Transactions to exclude"),
                transaction_exclusions,
                html.Label("More Settings"),
                settings_checklist,
                html.Button(id=APPLY_BTN, children="Apply"),
                dcc.Loading(children=dcc.Graph(id=CASHFLOW_GRAPH)),
            ]
        )

        def update_figure(
            _: int,
            start_date: Optional[str],
            end_date: Optional[str],
            average: str,
            checklist_settings: List[str],
            t_exclusions: Optional[List[str]],
            a_exclusions: Optional[List[str]],
        ) -> go.Figure:
            """
            Redraw Sankey figure based on all user settings.
            :param _: unused n_clicks value of the "apply" button - only used for triggering this update
            :param start_date:
            :param end_date:
            :param average:
            :param checklist_settings:
            :param t_exclusions:
            :param a_exclusions:
            :return:
            """
            fold_asset_accounts = (
                checklist_settings is not None
                and MERGE_ASSET_ACCOUNTS in checklist_settings
            )
            treat_liabilities_as_assets = (
                checklist_settings is not None
                and TREAT_LIABILITIES_AS_ASSETS in checklist_settings
            )

            accounts, transactions, splits, hierarchy = (
                data.accounts,
                data.transactions,
                data.splits,
                data.account_hierarchy,
            )

            transactions, splits = CashflowDashFactory._filter_by_date(
                transactions, splits, start_date, end_date
            )

            # apply transaction exclusion
            if t_exclusions is not None:
                transactions = transactions.loc[~transactions.index.isin(t_exclusions)]
                splits = splits.loc[~splits[TRANSACTION].isin(t_exclusions)]

            if treat_liabilities_as_assets:
                # find root liability and root asset nodes in hierarchy
                root_liability_node = anytree.find(
                    hierarchy,
                    maxlevel=2,
                    filter_=lambda n: accounts.at[n.name, TYPE] == LIABILITY,
                )
                root_asset_node = anytree.find(
                    hierarchy,
                    maxlevel=2,
                    filter_=lambda n: accounts.at[n.name, TYPE] == ASSET,
                )

                for node in root_liability_node.descendants:
                    # change the account type in the accounts dataframe
                    accounts.at[node.name, TYPE] = ASSET

                for node in root_liability_node.children:
                    # reparent all its children to the root asset account
                    node.parent = root_asset_node

            # filter accounts
            accounts = accounts.loc[~(accounts[TYPE] == EQUITY)]
            accounts, transactions, splits = self._filter_by_account_blacklist(
                accounts, transactions, splits, a_exclusions
            )

            df = splits.merge(accounts, left_on=ACCOUNT, right_index=True)

            if fold_asset_accounts:
                is_asset_split = df[TYPE].isin([ASSET, CASH, BANK])
                asset_splits = df.loc[is_asset_split]
                non_asset_splits = df.loc[~is_asset_split]

                # combine splits of asset accounts into one by summing up their value in each transaction
                asset_splits_folded = asset_splits.groupby(TRANSACTION, as_index=False)[
                    [VALUE]
                ].sum()
                asset_splits_folded[ACCOUNT] = "00000000000000000000000000000001"
                dummy_account = pd.Series(
                    {TYPE: ASSET, NAME: "Assets", DESCRIPTION: "Dummy Asset Account"},
                    name="00000000000000000000000000000001",
                )
                asset_splits_folded = asset_splits_folded.assign(
                    **dummy_account.to_dict()
                )

                # splits of transactions involving only asset accounts will be 0, drop those
                asset_splits_folded = asset_splits_folded.loc[
                    asset_splits_folded[VALUE] != 0
                ]

                # merge with the non-asset splits, and also keep dummy account for later
                df = pd.concat([asset_splits_folded, non_asset_splits], sort=True)
                accounts = accounts.append(dummy_account, sort=True)

            # determine links
            links = []
            df[VALUE] = df[VALUE].astype(float)

            for guid, splits_of_transaction in df.groupby(TRANSACTION):
                transaction_links = self.link_reconstructor.reconstruct(
                    splits_of_transaction
                )
                links += transaction_links
            links = pd.DataFrame(links)
            # combine all transactions between the same two accounts
            links = links.groupby([SOURCE, TARGET], as_index=False).sum()

            # apply averaging
            _, averaging_rule = averaging_options[average]
            if averaging_rule is not None:
                # count number of years/quarters/months/... covered by date range
                num_reference_timespans = len(
                    transactions.resample(averaging_rule, on=DATE)[DATE].count()
                )
                links[VALUE] = links[VALUE] / num_reference_timespans

            show_account_hierarchy = True
            if show_account_hierarchy:
                new_links = pd.DataFrame(columns=links.columns)
                for idx, row in links.iterrows():
                    # find node of target account in account hierarchy
                    target_node = anytree.find(
                        hierarchy, lambda n: n.name == row[TARGET]
                    )

                    if target_node is None:
                        # leave links with the dummy asset account as target the way they are
                        assert fold_asset_accounts
                        new_links = new_links.append(row, ignore_index=True)
                        continue

                    # trim the earliest two ancestors to get rid of the root account and the root expense/income/liability account
                    ancestors = [n.name for n in target_node.ancestors[2:]]
                    nodes = [row[SOURCE], *ancestors, row[TARGET]]

                    for source, target in zip(nodes, nodes[1:]):
                        # add or update the new link in the links dataframe
                        filter = (new_links[SOURCE] == source) & (
                            new_links[TARGET] == target
                        )
                        if new_links.loc[filter].empty:
                            new_links = new_links.append(
                                pd.Series(
                                    {SOURCE: source, TARGET: target, VALUE: row[VALUE]}
                                ),
                                ignore_index=True,
                            )
                        else:
                            new_links.loc[filter, VALUE] += row[VALUE]
                links = new_links

            # Create label for each node: account name and sum of money involved. Particularly for asset accounts, the
            # incoming amount of money must not equal the outgoing amount of money (people may save money or may make
            # bigger purchases with saved money). To make sense in the plot, the sum of money shown for an account
            # therefore needs to be the maximum of either incoming or outgoing money for each account.
            sum_of_targets = links.groupby(TARGET).sum()
            sum_of_sources = links.groupby(SOURCE).sum()
            sum_per_account = pd.concat(
                [sum_of_targets, sum_of_sources], axis=1, sort=True
            ).max(axis=1)
            # if there are small values keep two decimals, otherwise round to int
            if sum_per_account.loc[sum_per_account < 1].empty:
                sum_per_account = sum_per_account.round(0).astype(int).astype(str)
            else:
                sum_per_account = sum_per_account.round(2).map(
                    lambda v: "{0:.2f}".format(v)
                )
            # create final label
            sum_per_account = sum_per_account.to_frame(VALUE).merge(
                accounts[NAME], left_index=True, right_index=True
            )
            node_labels = sum_per_account.apply(
                lambda row: row[NAME] + ": " + row[VALUE], axis=1
            )  # TODO locale-specific formatting?

            # convert account GUIDs to int-based indices
            accounts_numbered = pd.Series(
                np.arange(len(sum_per_account)), index=sum_per_account.index
            )
            links[SOURCE] = links[SOURCE].map(accounts_numbered)
            links[TARGET] = links[TARGET].map(accounts_numbered)

            fig = go.Figure(
                data=[
                    go.Sankey(
                        node=dict(
                            pad=15,
                            thickness=20,
                            # line=dict(color="black", width=0.5),
                            label=node_labels,
                            color="blue",
                        ),
                        link=dict(
                            source=links[SOURCE],
                            target=links[TARGET],
                            value=links[VALUE],
                        ),
                    )
                ]
            )

            fig.update_layout(font_size=10, height=800)

            return fig

        def update_transaction_exclusions(
            start_date: str, end_date: str, a_exclusions: Optional[List[str]]
        ):
            """
            Update the list of transactions users can exclude based on the current date range and already excluded
            accounts.
            :param start_date:
            :param end_date:
            :param a_exclusions:
            :return:
            """
            accounts, transactions, splits = (
                data.accounts,
                data.transactions,
                data.splits,
            )
            transactions, splits = CashflowDashFactory._filter_by_date(
                transactions, splits, start_date, end_date
            )

            _, transactions, splits = self._filter_by_account_blacklist(
                accounts, transactions, splits, a_exclusions
            )

            # determine the largest transaction candidates a user may want to exclude
            NUM_TRANSACTIONS = 100
            candidates = (
                splits.groupby(TRANSACTION)[VALUE]
                .max()
                .sort_values(ascending=False)
                .iloc[:NUM_TRANSACTIONS]
            )
            candidates = candidates.to_frame(VALUE).merge(
                transactions, left_index=True, right_index=True
            )

            candidates[VALUE] = (
                candidates[VALUE]
                .astype(float)
                .round(2)
                .map(lambda v: "{0:.2f}".format(v))
            )
            candidates["label"] = (
                candidates[DESCRIPTION] + " (" + candidates[VALUE] + ")"
            )

            options = (
                candidates.reset_index()[["index", "label"]]
                .rename({"index": "value"}, axis="columns")
                .to_dict("records")
            )

            return options

        dash.callback(
            Output(TRANSACTION_EXCLUSIONS, "options"),
            [
                Input(DATE_PICKER_RANGE, "start_date"),
                Input(DATE_PICKER_RANGE, "end_date"),
                Input(ACCOUNT_EXCLUSIONS, "value"),
            ],
        )(update_transaction_exclusions)

        dash.callback(
            Output(CASHFLOW_GRAPH, "figure"),
            [Input(APPLY_BTN, "n_clicks")],
            [
                State(DATE_PICKER_RANGE, "start_date"),
                State(DATE_PICKER_RANGE, "end_date"),
                State(AVERAGING_PICKER, "value"),
                State(SETTINGS_CHECKLIST, "value"),
                State(TRANSACTION_EXCLUSIONS, "value"),
                State(ACCOUNT_EXCLUSIONS, "value"),
            ],
        )(update_figure)
