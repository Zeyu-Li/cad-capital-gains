from click import ClickException
from datetime import timedelta
from decimal import Decimal


class TickerGains:

    def __init__(self, ticker):
        self._ticker = ticker
        self._share_balance = 0
        self._total_acb = 0

    def add_transactions(self, transactions, exchange_rates,
                         lookahead_transactions=None):
        """Adds all transactions and updates the calculated values.

        Args:
            transactions: Transactions to process for ACB calculation.
            exchange_rates: Map of currency to ExchangeRate objects.
            lookahead_transactions: Optional broader set of transactions
                (including future ones) used only for superficial loss
                window detection. If None, uses transactions.
        """
        sl_transactions = lookahead_transactions or transactions
        for t in transactions:
            t.add_rate(exchange_rates)
            self._add_transaction(t)
            sl_shares = self._superficial_loss_shares(t, sl_transactions)
            if sl_shares > 0:
                denied_proportion = sl_shares / t.qty
                denied_amount = -(t.capital_gain * denied_proportion)
                self._total_acb += denied_amount
                t.set_superficial_loss(denied_amount)

    def _superficial_window_filter(self, transaction, min_date, max_date):
        """Filter out BUY transactions that fall within the 61 day superficial
        loss window."""
        # Only consider transactions for the same ticker
        return (
            transaction.ticker == self._ticker and transaction.date >= min_date
            and transaction.date <= max_date
        )

    def _superficial_loss_shares(self, transaction, transactions):
        """Returns the number of shares subject to the superficial loss rule,
        or 0 if the transaction is not a superficial loss."""
        # Has to be a capital loss
        if (transaction.capital_gain >= 0):
            return 0
        min_date = transaction.date - timedelta(days=30)
        max_date = transaction.date + timedelta(days=30)
        filtered_transactions = list(
            filter(
                lambda t: self.
                _superficial_window_filter(t, min_date, max_date),
                transactions
            )
        )
        # Has to have a purchase either 30 days before or 30 days after
        if (not any(t.action == 'BUY' for t in filtered_transactions)):
            return 0
        # Calculate share balance at end of the 30-day post-sale window
        transaction_idx = filtered_transactions.index(transaction)
        balance = transaction._share_balance
        for window_transaction in filtered_transactions[transaction_idx + 1:]:
            if window_transaction.action == 'SELL':
                balance -= window_transaction.qty
            else:
                balance += window_transaction.qty
        if balance <= 0:
            return 0
        return min(balance, transaction.qty)

    def _add_transaction(self, transaction):
        """Adds a transaction and updates the calculated values."""
        if self._share_balance == 0:
            # to prevent divide by 0 error
            old_acb_per_share = 0
        else:
            old_acb_per_share = self._total_acb / self._share_balance
        proceeds = (
            transaction.qty * transaction.price
        ) * transaction.exchange_rate  # noqa: E501
        if transaction.action == 'SELL':
            self._share_balance -= transaction.qty
            acb = old_acb_per_share * transaction.qty
            capital_gain = proceeds - transaction.expenses - acb
            self._total_acb -= acb
        else:
            self._share_balance += transaction.qty
            acb = proceeds + transaction.expenses
            capital_gain = Decimal(0.0)
            self._total_acb += acb
        if self._share_balance < 0:
            raise ClickException("Transaction caused negative share balance")
        transaction.share_balance = self._share_balance
        transaction.proceeds = proceeds
        transaction.capital_gain = capital_gain
        transaction.acb = acb

        transaction.cumulative_cost = self._total_acb
