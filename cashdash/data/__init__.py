from dataclasses import dataclass
from typing import Optional

import anytree
import pandas as pd

# dataframe columns
TYPE = "type"
DESCRIPTION = "description"
NAME = "name"
GUID = "guid"
DATE = "date"
TRANSACTION = "transaction"
ACCOUNT = "account"
VALUE = "value"

# account types
EXPENSE = "EXPENSE"
INCOME = "INCOME"
ASSET = "ASSET"
CASH = "CASH"
BANK = "BANK"
LIABILITY = "LIABILITY"
EQUITY = "EQUITY"


@dataclass(eq=False, unsafe_hash=True)
class BookData:
    accounts: pd.DataFrame
    transactions: pd.DataFrame
    splits: pd.DataFrame
    account_hierarchy: Optional[anytree.Node] = None

    def remove_book_closing_transactions(self):
        equity_accounts = self.accounts.loc[self.accounts[TYPE] == EQUITY]
        transactions_with_equity = self.splits.loc[
            (self.splits[ACCOUNT].isin(equity_accounts.index)), TRANSACTION
        ].values

        # drop them
        self.transactions = self.transactions.loc[
            ~(self.transactions.index.isin(transactions_with_equity))
        ]
        self.splits = self.splits.loc[
            ~(self.splits[TRANSACTION].isin(transactions_with_equity))
        ]


class FileBasedBookDataReader:
    def read(self, path) -> BookData:
        raise NotImplementedError
