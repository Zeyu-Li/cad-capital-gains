from click import ClickException
import pytest
from datetime import date
from decimal import Decimal

from capgains.ticker_gains import TickerGains
from capgains.exchange_rate import ExchangeRate
from capgains.transaction import Transaction


def test_superficial_loss_no_purchase_after_loss(exchange_rates_mock):
    """Testing if transaction is marked as a superficial loss even if there are
    no purchases made after the loss."""
    transactions = [
        Transaction(
            date(2018, 1, 1),
            'ESPP PURCHASE',
            'ANET',
            'BUY',
            100,
            100.00,
            10.00,
            'USD'
        ),
        Transaction(
            date(2018, 1, 2),
            'RSU VEST',
            'ANET',
            'SELL',
            99,
            50.00,
            10.00,
            'USD'
        )
    ]
    tg = TickerGains(transactions[0].ticker)
    er = ExchangeRate('USD', transactions[0].date, transactions[1].date)
    er_map = {'USD': er}
    tg.add_transactions(transactions, er_map)
    assert transactions[1].superficial_loss > 0
    # Sell 99, balance=1. denied proportion = 1/99
    full_loss = Decimal('9900') - Decimal('20') - (Decimal('20020') / Decimal('100') * Decimal('99'))
    denied = -(full_loss * Decimal('1') / Decimal('99'))
    assert transactions[1].superficial_loss == denied
    assert transactions[1].capital_gain == full_loss + denied


def test_superficial_loss_purchase_after_loss(exchange_rates_mock):
    """Testing if transaction is marked as a superficial loss even if there is
    a purchase made after the loss."""
    transactions = [
        Transaction(
            date(2018, 1, 1),
            'ESPP PURCHASE',
            'ANET',
            'BUY',
            100,
            100.00,
            10.00,
            'USD'
        ),
        Transaction(
            date(2018, 1, 2),
            'RSU VEST',
            'ANET',
            'SELL',
            99,
            50.00,
            10.00,
            'USD'
        ),
        Transaction(
            date(2018, 1, 3),
            'RSU VEST',
            'ANET',
            'BUY',
            1,
            100.00,
            10.00,
            'USD'
        )
    ]
    tg = TickerGains(transactions[0].ticker)
    er = ExchangeRate('USD', transactions[0].date, transactions[1].date)
    er_map = {'USD': er}
    tg.add_transactions(transactions, er_map)
    assert transactions[1].superficial_loss > 0
    # Sell 99, balance after window = 1 + 1 (buy) = 2. denied proportion = 2/99
    full_loss = Decimal('9900') - Decimal('20') - (Decimal('20020') / Decimal('100') * Decimal('99'))
    denied = -(full_loss * Decimal('2') / Decimal('99'))
    assert transactions[1].superficial_loss == denied
    assert transactions[1].capital_gain == full_loss + denied


def test_loss_no_balance_after_window(exchange_rates_mock):
    """Testing if transaction is not marked as a superficial loss if there is
    no share balance 30 days after the loss."""
    transactions = [
        Transaction(
            date(2018, 1, 1),
            'ESPP PURCHASE',
            'ANET',
            'BUY',
            100,
            100.00,
            10.00,
            'USD'
        ),
        Transaction(
            date(2018, 1, 2),
            'RSU VEST',
            'ANET',
            'SELL',
            99,
            50.00,
            10.00,
            'USD'
        ),
        Transaction(
            date(2018, 1, 3),
            'RSU VEST',
            'ANET',
            'SELL',
            1,
            100.00,
            10.00,
            'USD'
        ),
        Transaction(
            date(2018, 2, 10),
            'RSU VEST',
            'ANET',
            'BUY',
            1,
            100.00,
            10.00,
            'USD'
        )
    ]
    tg = TickerGains(transactions[0].ticker)
    er = ExchangeRate('USD', transactions[0].date, transactions[1].date)
    er_map = {'USD': er}
    tg.add_transactions(transactions, er_map)
    assert not transactions[1].superficial_loss
    assert transactions[1].capital_gain < 0


def test_loss_no_purchase_in_window(exchange_rates_mock):
    """Testing if transaction is not marked as a superficial loss if there are
    are no purchases made in the 61 day window."""
    transactions = [
        Transaction(
            date(2018, 1, 1),
            'ESPP PURCHASE',
            'ANET',
            'BUY',
            100,
            100.00,
            10.00,
            'USD'
        ),
        Transaction(
            date(2018, 8, 1),
            'RSU VEST',
            'ANET',
            'SELL',
            99,
            50.00,
            10.00,
            'USD'
        ),
        Transaction(
            date(2018, 12, 1),
            'RSU VEST',
            'ANET',
            'BUY',
            1,
            50.00,
            10.00,
            'USD'
        )
    ]
    tg = TickerGains(transactions[0].ticker)
    er = ExchangeRate('USD', transactions[0].date, transactions[1].date)
    er_map = {'USD': er}
    tg.add_transactions(transactions, er_map)
    assert not transactions[1].superficial_loss
    assert transactions[1].capital_gain < 0


def test_gain_not_marked_as_superficial_loss(exchange_rates_mock):
    """Testing if transaction is not marked as a superficial loss if it does
    not result in a loss."""
    transactions = [
        Transaction(
            date(2018, 1, 1),
            'ESPP PURCHASE',
            'ANET',
            'BUY',
            100,
            1.00,
            10.00,
            'USD'
        ),
        Transaction(
            date(2018, 8, 1),
            'RSU VEST',
            'ANET',
            'SELL',
            100,
            50.00,
            10.00,
            'USD'
        )
    ]
    tg = TickerGains(transactions[0].ticker)
    er = ExchangeRate('USD', transactions[0].date, transactions[1].date)
    er_map = {'USD': er}
    tg.add_transactions(transactions, er_map)
    assert not transactions[1].superficial_loss
    assert transactions[1].capital_gain > 0


def test_ticker_gains_negative_balance(transactions, exchange_rates_mock):
    """If the first transaction added is a sell, it is illegal since this
    causes a negative balance, which is impossible."""
    sell_transaction = transactions[2]
    tg = TickerGains(sell_transaction.ticker)
    er = ExchangeRate('USD', transactions[2].date, transactions[2].date)
    er_map = {'USD': er}
    with pytest.raises(ClickException) as excinfo:
        tg.add_transactions([sell_transaction], er_map)
    assert excinfo.value.message == "Transaction caused negative share balance"


def test_ticker_gains_ok(transactions, exchange_rates_mock):
    tg = TickerGains(transactions[0].ticker)
    er = ExchangeRate('USD', transactions[0].date, transactions[3].date)
    er_map = {'USD': er}

    # Add first transaction - 'BUY'
    # Add second transaction - 'BUY'
    # Add third transaction - 'SELL'
    transactions_to_test = [transactions[0], transactions[2], transactions[3]]

    tg.add_transactions(transactions_to_test, er_map)
    assert transactions[0].exchange_rate == 2.0
    assert transactions[0].share_balance == 100
    assert transactions[0].proceeds == 10000.0
    assert transactions[0].capital_gain == 0.0
    assert transactions[0].acb == 10020.00
    assert transactions[0].superficial_loss == 0
    assert transactions[0].expenses == 20.0

    assert transactions[2].exchange_rate == 2.0
    assert transactions[2].share_balance == 50
    assert transactions[2].proceeds == 12000.00
    assert transactions[2].capital_gain == 6970.00
    assert transactions[2].acb == 5010.00
    assert transactions[2].superficial_loss == 0
    assert transactions[2].expenses == 20.0

    assert transactions[3].exchange_rate == 2.0
    assert transactions[3].share_balance == 100
    assert transactions[3].proceeds == 13000.00
    assert transactions[3].capital_gain == 0.0
    assert transactions[3].acb == 13020.00
    assert transactions[3].superficial_loss == 0
    assert transactions[3].expenses == 20.0


def test_partial_superficial_loss_60_percent(exchange_rates_mock):
    """Buy 100 shares, sell 100 at a loss, buy 60 within window.
    60% of loss should be denied."""
    transactions = [
        Transaction(date(2018, 1, 1), 'BUY', 'ANET', 'BUY',
                    100, 100.00, 0, 'USD'),
        Transaction(date(2018, 6, 1), 'SELL', 'ANET', 'SELL',
                    100, 50.00, 0, 'USD'),
        Transaction(date(2018, 6, 15), 'BUY', 'ANET', 'BUY',
                    60, 50.00, 0, 'USD'),
    ]
    tg = TickerGains(transactions[0].ticker)
    er = ExchangeRate('USD', transactions[0].date, transactions[2].date)
    er_map = {'USD': er}
    tg.add_transactions(transactions, er_map)
    # Sell 100 @ $50 (rate=2): proceeds = 10000, ACB = 20000, loss = -10000
    # Balance after window: 0 + 60 = 60. min(60, 100) = 60
    # Denied = 10000 * 60/100 = 6000. Allowed loss = -10000 + 6000 = -4000
    full_loss = Decimal('10000') - Decimal('20000')
    assert transactions[1].superficial_loss == Decimal('6000')
    assert transactions[1].capital_gain == full_loss + Decimal('6000')


def test_full_superficial_loss_capped(exchange_rates_mock):
    """Buy 200 shares, sell 50 at a loss, 150 still held.
    Shares held (150) > shares sold (50), so 100% denied."""
    transactions = [
        Transaction(date(2018, 1, 1), 'BUY', 'ANET', 'BUY',
                    200, 100.00, 0, 'USD'),
        Transaction(date(2018, 1, 15), 'SELL', 'ANET', 'SELL',
                    50, 50.00, 0, 'USD'),
    ]
    tg = TickerGains(transactions[0].ticker)
    er = ExchangeRate('USD', transactions[0].date, transactions[1].date)
    er_map = {'USD': er}
    tg.add_transactions(transactions, er_map)
    # Sell 50 @ $50 (rate=2): proceeds = 5000, ACB per share = 200, ACB = 10000
    # loss = 5000 - 10000 = -5000
    # Balance = 150. min(150, 50) = 50. denied proportion = 50/50 = 1.0
    # Full denial: capital_gain should be 0
    assert transactions[1].superficial_loss == Decimal('5000')
    assert transactions[1].capital_gain == 0


def test_partial_superficial_loss_multiple_transactions(exchange_rates_mock):
    """Buy 100, sell 80 at loss, buy 50, sell 20 within window.
    Balance at end of window = 100 - 80 + 50 - 20 = 50.
    Denied proportion = min(50, 80) / 80 = 50/80."""
    transactions = [
        Transaction(date(2018, 1, 1), 'BUY', 'ANET', 'BUY',
                    100, 100.00, 0, 'USD'),
        Transaction(date(2018, 6, 1), 'SELL', 'ANET', 'SELL',
                    80, 50.00, 0, 'USD'),
        Transaction(date(2018, 6, 10), 'BUY', 'ANET', 'BUY',
                    50, 50.00, 0, 'USD'),
        Transaction(date(2018, 6, 20), 'SELL', 'ANET', 'SELL',
                    20, 50.00, 0, 'USD'),
    ]
    tg = TickerGains(transactions[0].ticker)
    er = ExchangeRate('USD', transactions[0].date, transactions[3].date)
    er_map = {'USD': er}
    tg.add_transactions(transactions, er_map)
    # Sell 80 @ $50 (rate=2): proceeds = 8000, ACB per share = 200, ACB = 16000
    # loss = 8000 - 16000 = -8000
    # Balance after sale = 20, then +50, -20 = 50. min(50, 80) = 50
    # Denied = 8000 * 50/80 = 5000
    full_loss = Decimal('8000') - Decimal('16000')
    denied = Decimal('8000') * Decimal('50') / Decimal('80')
    assert transactions[1].superficial_loss == denied
    assert transactions[1].capital_gain == full_loss + denied
