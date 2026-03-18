from datetime import date
import requests_mock as rm

from capgains.commands import capgains_calc as CapGainsCalc
from capgains.transaction import Transaction
from capgains.transactions import Transactions


def test_no_ticker(transactions, capfd, exchange_rates_mock):
    """Testing capgains_calc without any optional filters."""
    CapGainsCalc.capgains_calc(transactions, 2018)
    out, _ = capfd.readouterr()
    assert out == """\
ANET-2018
[Total Gains = 6,970.00]
+------------+---------------+----------+-------+------------+----------+-----------+---------------------+
| date       | description   | ticker   |   qty |   proceeds |      ACB |   outlays |   capital gain/loss |
|------------+---------------+----------+-------+------------+----------+-----------+---------------------|
| 2018-02-20 | RSU VEST      | ANET     |    50 |  12,000.00 | 5,010.00 |     20.00 |            6,970.00 |
+------------+---------------+----------+-------+------------+----------+-----------+---------------------+

GOOGL-2018
No capital gains

"""  # noqa: E501


def test_tickers(transactions, capfd, exchange_rates_mock):
    """Testing capgains_calc with a ticker."""
    CapGainsCalc.capgains_calc(transactions, 2018, ['ANET'])
    out, _ = capfd.readouterr()
    assert out == """\
ANET-2018
[Total Gains = 6,970.00]
+------------+---------------+----------+-------+------------+----------+-----------+---------------------+
| date       | description   | ticker   |   qty |   proceeds |      ACB |   outlays |   capital gain/loss |
|------------+---------------+----------+-------+------------+----------+-----------+---------------------|
| 2018-02-20 | RSU VEST      | ANET     |    50 |  12,000.00 | 5,010.00 |     20.00 |            6,970.00 |
+------------+---------------+----------+-------+------------+----------+-----------+---------------------+

"""  # noqa: E501


def test_no_transactions(capfd):
    """Testing capgains_calc without any transactions."""
    CapGainsCalc.capgains_calc(Transactions([]), 2018)
    out, _ = capfd.readouterr()
    assert out == """\
No transactions available
"""


def test_unknown_year(transactions, capfd, exchange_rates_mock):
    """Testing capgains_calc with a year matching no transactions."""
    CapGainsCalc.capgains_calc(transactions, 1998)
    out, _ = capfd.readouterr()
    assert out == """\
ANET-1998
No capital gains

GOOGL-1998
No capital gains

"""


def test_partial_superficial_loss_displayed(capfd, exchange_rates_mock):
    """Testing capgains_calc with a partial superficial loss transaction.
    The partially-denied loss should appear in output with its allowed portion."""
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
            date(2018, 12, 1),
            'RSU VEST',
            'ANET',
            'SELL',
            1,
            1000.00,
            10.00,
            'USD'
        )
    ]
    transactions = Transactions(transactions)
    CapGainsCalc.capgains_calc(transactions, 2018)
    out, _ = capfd.readouterr()
    assert out == """\
ANET-2018
[Total Gains = -8,160.00]
+------------+---------------+----------+-------+------------+-----------+-----------+---------------------+
| date       | description   | ticker   |   qty |   proceeds |       ACB |   outlays |   capital gain/loss |
|------------+---------------+----------+-------+------------+-----------+-----------+---------------------|
| 2018-01-02 | RSU VEST      | ANET     |    99 |   9,900.00 | 19,819.80 |     20.00 |           -9,839.40 |
| 2018-12-01 | RSU VEST      | ANET     |     1 |   2,000.00 |    300.60 |     20.00 |            1,679.40 |
+------------+---------------+----------+-------+------------+-----------+-----------+---------------------+

"""  # noqa: E501


def test_calc_mixed_currencies(capfd, requests_mock):
    """Testing capgains_calc with mixed currencies."""
    usd_transaction = Transaction(
        date(2017, 2, 15),
        'ESPP PURCHASE',
        'ANET',
        'BUY',
        100,
        50.00,
        0.00,
        'USD'
    )
    cad_transaction = Transaction(
        date(2018, 2, 20), 'RSU VEST', 'ANET', 'SELL', 100, 50.00, 0.00, 'CAD'
    )
    transactions = Transactions([usd_transaction, cad_transaction])

    usd_observations = [
        {
            'd': usd_transaction.date.isoformat(), 'FXUSDCAD': {
                'v': '2.0'
            }
        }
    ]
    requests_mock.get(rm.ANY, json={"observations": usd_observations})
    CapGainsCalc.capgains_calc(transactions, 2018)
    out, _ = capfd.readouterr()
    assert out == """\
ANET-2018
[Total Gains = -5,000.00]
+------------+---------------+----------+-------+------------+-----------+-----------+---------------------+
| date       | description   | ticker   |   qty |   proceeds |       ACB |   outlays |   capital gain/loss |
|------------+---------------+----------+-------+------------+-----------+-----------+---------------------|
| 2018-02-20 | RSU VEST      | ANET     |   100 |   5,000.00 | 10,000.00 |      0.00 |           -5,000.00 |
+------------+---------------+----------+-------+------------+-----------+-----------+---------------------+

"""  # noqa: E501


def test_partial_shares(capfd, requests_mock):
    """Testing capgains_calc with partial shares."""
    partial_buy = Transaction(
        date(2017, 2, 15),
        'ESPP PURCHASE',
        'ANET',
        'BUY',
        0.5,
        50.00,
        0.00,
        'CAD'
    )
    partial_sell = Transaction(
        date(2018, 2, 20),
        'RSU VEST',
        'ANET',
        'SELL',
        0.5,
        100.00,
        0.00,
        'CAD'
    )
    transactions = Transactions([partial_buy, partial_sell])

    CapGainsCalc.capgains_calc(transactions, 2018)
    out, _ = capfd.readouterr()
    assert out == """\
ANET-2018
[Total Gains = 25.00]
+------------+---------------+----------+-------+------------+-------+-----------+---------------------+
| date       | description   | ticker   |   qty |   proceeds |   ACB |   outlays |   capital gain/loss |
|------------+---------------+----------+-------+------------+-------+-----------+---------------------|
| 2018-02-20 | RSU VEST      | ANET     |   0.5 |      50.00 | 25.00 |      0.00 |               25.00 |
+------------+---------------+----------+-------+------------+-------+-----------+---------------------+

"""  # noqa: E501


def test_cross_year_superficial_loss(capfd, exchange_rates_mock):
    """A sale at a loss in late December should be detected as superficial
    if there is a buy in early January of the next year."""
    transactions = [
        Transaction(
            date(2018, 1, 1),
            'BUY',
            'ANET',
            'BUY',
            100,
            100.00,
            0,
            'USD'
        ),
        Transaction(
            date(2018, 12, 20),
            'SELL',
            'ANET',
            'SELL',
            100,
            50.00,
            0,
            'USD'
        ),
        Transaction(
            date(2019, 1, 5),
            'BUY',
            'ANET',
            'BUY',
            60,
            50.00,
            0,
            'USD'
        )
    ]
    transactions = Transactions(transactions)
    CapGainsCalc.capgains_calc(transactions, 2018)
    out, _ = capfd.readouterr()
    # Sell 100 @ $50 (rate=2): proceeds=10000, ACB=20000, loss=-10000
    # Jan 5 buy is within 30-day window. Balance at end of window = 60.
    # min(60, 100) = 60. Denied = 10000 * 60/100 = 6000.
    # Allowed loss = -10000 + 6000 = -4000
    assert "ANET-2018" in out
    assert "Total Gains = -4,000.00" in out


def test_cross_year_no_superficial_without_next_year_buy(capfd, exchange_rates_mock):
    """A late-December sale at a loss should NOT be superficial if the
    next-year buy is outside the 30-day window. Also verifies that
    next-year transactions don't affect the current year's ACB."""
    transactions = [
        Transaction(
            date(2018, 1, 1),
            'BUY',
            'ANET',
            'BUY',
            100,
            100.00,
            0,
            'USD'
        ),
        Transaction(
            date(2018, 12, 1),
            'SELL',
            'ANET',
            'SELL',
            100,
            50.00,
            0,
            'USD'
        ),
        Transaction(
            date(2019, 1, 15),
            'BUY',
            'ANET',
            'BUY',
            50,
            50.00,
            0,
            'USD'
        )
    ]
    transactions = Transactions(transactions)
    CapGainsCalc.capgains_calc(transactions, 2018)
    out, _ = capfd.readouterr()
    # Sell 100 @ $50 (rate=2): proceeds=10000, ACB=20000, loss=-10000
    # Jan 15 buy is 45 days after Dec 1 sale — outside 30-day window.
    # No superficial loss. Full loss claimable.
    assert "ANET-2018" in out
    assert "Total Gains = -10,000.00" in out


def test_cross_year_acb_not_affected_by_lookahead(capfd, exchange_rates_mock):
    """Next-year transactions used for wash sale detection must not
    alter the ACB reported for current-year sells."""
    transactions = [
        Transaction(
            date(2018, 1, 1),
            'BUY',
            'ANET',
            'BUY',
            100,
            100.00,
            0,
            'USD'
        ),
        Transaction(
            date(2018, 6, 1),
            'SELL',
            'ANET',
            'SELL',
            50,
            150.00,
            0,
            'USD'
        ),
        Transaction(
            date(2019, 1, 10),
            'BUY',
            'ANET',
            'BUY',
            200,
            200.00,
            0,
            'USD'
        )
    ]
    transactions = Transactions(transactions)
    CapGainsCalc.capgains_calc(transactions, 2018)
    out, _ = capfd.readouterr()
    # Sell 50 @ $150 (rate=2): proceeds=15000, ACB=200*50=10000, gain=5000
    # The Jan 2019 buy should NOT appear in 2018 output or change the ACB.
    assert "ANET-2018" in out
    assert "Total Gains = 5,000.00" in out
    assert "10,000.00" in out  # ACB column
