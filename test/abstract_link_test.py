import unittest
from pathlib import Path

import pandas as pd

from cashdash.algo.base import SOURCE, TARGET
from cashdash.data import VALUE, TYPE, INCOME, EXPENSE

# Keep unittest from running the abstract test, see https://stackoverflow.com/a/50176291
class AbstractTest:
    class LinkReconstructionTest(unittest.TestCase):

        TESTS_ROOT = Path(__file__).parent.resolve()
        TEST_RESOURCES_ROOT = TESTS_ROOT / "resources"

        def setUp(self) -> None:
            raise NotImplementedError

        def compare(self, input_csv_name, expected, decimals=7):
            input_csv = AbstractTest.LinkReconstructionTest.TEST_RESOURCES_ROOT / input_csv_name
            df = pd.read_csv(input_csv)
            actual = self.uut.reconstruct(df)

            assert len(expected) == len(actual)
            for e_split in expected:
                # iterate over actual splits to find one with matching source/target and a value which is close enough
                link_found = False
                for a_split in actual:
                    does_link_match = a_split[SOURCE] == e_split[SOURCE] and a_split[TARGET] == e_split[TARGET]
                    if not does_link_match:
                        continue
                    self.assertAlmostEqual(a_split[VALUE], e_split[VALUE], places=decimals)
                    link_found = True
                    break
                self.assertTrue(link_found)

        def compare_underconstrained(self, input_csv_name, expected, decimals=7):
            input_csv = AbstractTest.LinkReconstructionTest.TEST_RESOURCES_ROOT / input_csv_name
            df = pd.read_csv(input_csv)
            actual = self.uut.reconstruct(df)

            actual_sum_of_values = 0
            for e_split in expected:
                # iterate over actual splits to find one with matching source/target
                for a_split in actual:
                    does_link_match = a_split[SOURCE] == e_split[SOURCE] and a_split[TARGET] == e_split[TARGET]
                    if not does_link_match:
                        continue
                    # we do not test the individual values here, only the total sum
                    actual_sum_of_values += a_split[VALUE]

            # TODO this line will not work if, in addition to flow triggered by income and expense, we have flow between
            #  asset accounts
            expected_sum_of_values = df.loc[df[TYPE].isin([INCOME, EXPENSE]), VALUE].abs().sum()

            self.assertAlmostEqual(actual_sum_of_values, expected_sum_of_values, places=decimals)

        def test_split_transaction_1as_1ex(self):
            """
            One asset, one expense account.
            """
            expected = [
                {SOURCE: "a300", TARGET: "a301", VALUE: 25.42}
            ]
            self.compare("test_split_transaction_1as_1ex.csv", expected)

        def test_split_transaction_2as(self):
            """
            Two asset accounts.
            """
            expected = [
                {SOURCE: "a300", TARGET: "a301", VALUE: 50.00}
            ]
            self.compare("test_split_transaction_2as.csv", expected)

        def test_split_transaction_1as_2ex(self):
            """
            One asset, two expense accounts.
            """
            expected = [
                {SOURCE: "a300", TARGET: "a301", VALUE: 8.66},
                {SOURCE: "a300", TARGET: "a302", VALUE: 1.59}
            ]
            self.compare("test_split_transaction_1as_2ex.csv", expected)

        def test_split_transaction_2as_1ex(self):
            """
            Two asset, one expense account. Deltas on asset accounts should sum up to expense delta.
            """
            expected = [
                {SOURCE: "a300", TARGET: "a302", VALUE: 3.53},
                {SOURCE: "a301", TARGET: "a302", VALUE: 4.47}
            ]
            self.compare("test_split_transaction_2as_1ex.csv", expected)

        def test_split_transaction_2as_2ex(self):
            """
            Two asset, two expense accounts. Here, we have no knowledge over the money distribution. Asset 1 could have paid
            70% of expense 1 and asset 2 the remaining 30%, or the other way around.
            """
            expected = [
                {SOURCE: "a300", TARGET: "a302"},
                {SOURCE: "a300", TARGET: "a303"},
                {SOURCE: "a301", TARGET: "a302"},
                {SOURCE: "a301", TARGET: "a303"}
            ]
            self.compare_underconstrained("test_split_transaction_2as_2ex.csv", expected)

        def test_split_transaction_1in_1as_1ex_as_negative(self):
            """
            One income, one asset, one expense account. Negative delta on the asset account.
            """
            expected = [
                {SOURCE: "a300", TARGET: "a301", VALUE: 3.4},
                {SOURCE: "a301", TARGET: "a302", VALUE: 11.52}
            ]
            self.compare("test_split_transaction_1in_1as_1ex_as_negative.csv", expected)

        def test_split_transaction_1in_1as_1ex_as_positive(self):
            """
            One income, one asset, one expense account. Positive delta on the asset account.
            """
            expected = [
                {SOURCE: "a300", TARGET: "a301", VALUE: 10.0},
                {SOURCE: "a301", TARGET: "a302", VALUE: 7.55}
            ]
            self.compare("test_split_transaction_1in_1as_1ex_as_positive.csv", expected)

        def test_split_transaction_1in_1as_2ex(self):
            """
            One income, one asset, two expense accounts. Testing just because it's a frequent case.
            """
            expected = [
                # income
                {SOURCE: "a300", TARGET: "a301", VALUE: 13.8},
                # expense #1
                {SOURCE: "a301", TARGET: "a302", VALUE: 27.32},
                # expense #2
                {SOURCE: "a301", TARGET: "a303", VALUE: 9.9}
            ]
            self.compare("test_split_transaction_1in_1as_2ex.csv", expected)

        def test_split_transaction_1in_2as_1ex(self):
            """
            One income, two asset, one expense account.
            """
            expected = [
                {SOURCE: "a300", TARGET: "a301"},
                {SOURCE: "a300", TARGET: "a302"},
                {SOURCE: "a301", TARGET: "a303"},
                {SOURCE: "a302", TARGET: "a303"},
            ]
            self.compare_underconstrained("test_split_transaction_1in_2as_1ex.csv", expected)