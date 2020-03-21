from typing import Dict

import gnucashxml
import pandas as pd
from anytree import Node

from cashdash.data import (
    FileBasedBookDataReader,
    BookData,
    TYPE,
    DESCRIPTION,
    NAME,
    GUID,
    DATE,
    TRANSACTION,
    ACCOUNT,
    VALUE,
)


class GnucashXmlBookDataReader(FileBasedBookDataReader):
    def read(self, path) -> BookData:
        gc_file = gnucashxml.from_filename(path)

        # gather info about accounts first
        index = []
        values = []
        temp_hierarchy = {}  # type: Dict[str, Node]

        # iterate over account hierarchy in pre-order fashion
        for account, subaccounts, _ in gc_file.walk():
            # collect account information
            values.append([account.actype, account.description, account.name])
            index.append(account.guid)

            # assemble account hierarchy
            if account.guid not in temp_hierarchy:
                account_node = Node(account.guid)
                temp_hierarchy[account.guid] = account_node
            else:
                # if we end up here, the account was previously created as a subaccount
                account_node = temp_hierarchy[account.guid]
            for subaccount in subaccounts:
                temp_hierarchy[subaccount.guid] = Node(
                    subaccount.guid, parent=account_node
                )
        # create dataframe of accounts and hierarchy
        accounts = pd.DataFrame(
            values, columns=[TYPE, DESCRIPTION, NAME], index=pd.Index(index, name=GUID)
        )
        account_hierarchy = temp_hierarchy[gc_file.root_account.guid]

        # create dataframe of transactions
        index = []
        values = []
        for trans in gc_file.transactions:
            values.append([trans.date, trans.description])
            index.append(trans.guid)
        transactions = pd.DataFrame(
            values, columns=[DATE, DESCRIPTION], index=pd.Index(index, name=GUID)
        )
        transactions[DATE] = transactions[DATE].dt.tz_localize(
            None
        )  # remove timezone information

        # create dataframe of splits
        index = []
        values = []
        for trans in gc_file.transactions:
            for split in trans.splits:
                values.append([trans.guid, split.account.guid, split.value])
                index.append(split.guid)
        splits = pd.DataFrame(
            values,
            columns=[TRANSACTION, ACCOUNT, VALUE],
            index=pd.Index(index, name=GUID),
        )

        data = BookData(
            accounts, transactions, splits, account_hierarchy=account_hierarchy
        )
        return data
