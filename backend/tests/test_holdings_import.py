from app.services import holdings_import_service
from app.services.holdings_import_service import import_holdings

ZERODHA_EXPORT = """Instrument,Qty.,Avg. cost,LTP,Cur. val,P&L,Net chg.,Day chg.
TCS,10,3500.5,2075,"20,750",-14255,-40.7,0.5
INFY,"1,200",1500,1800,2160000,360000,20,0.1
M&M,5,1200,3000,15000,9000,150,1.2
"""


def test_zerodha_style_export_is_detected():
    result = import_holdings(ZERODHA_EXPORT)
    assert result.detected_columns == {"symbol": "Instrument", "quantity": "Qty."}
    symbols = [(h.symbol, h.quantity) for h in result.holdings]
    assert symbols == [("TCS.NS", 10.0), ("INFY.NS", 1200.0), ("M&M.NS", 5.0)]
    assert all(h.matched for h in result.holdings)


def test_headerless_rows_and_scheme_codes():
    result = import_holdings("HDFCBANK, 20\n122639, 150.5\nMF:119800\t3")
    by_input = {h.input_text: h for h in result.holdings}
    assert by_input["HDFCBANK"].symbol == "HDFCBANK.NS"
    assert by_input["122639"].symbol == "MF:122639" and by_input["122639"].quantity == 150.5


def test_fund_names_are_matched_preferring_the_plan_named(monkeypatch):
    monkeypatch.setattr(
        holdings_import_service,
        "search_mutual_funds",
        lambda query: [
            {"schemeCode": 1, "schemeName": "Parag Parikh Flexi Cap Fund - Regular Plan - Growth"},
            {"schemeCode": 2, "schemeName": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth"},
            {"schemeCode": 3, "schemeName": "Parag Parikh Flexi Cap Fund - Direct Plan - IDCW"},
        ],
    )
    result = import_holdings("Scheme Name\tUnits\nParag Parikh Flexi Cap Fund - Direct Growth\t250.123")
    holding = result.holdings[0]
    assert holding.symbol == "MF:2"
    assert holding.display_name == "Parag Parikh Flexi Cap"
    assert holding.quantity == 250.123


def test_bad_quantity_is_reported_not_crashing():
    result = import_holdings("Symbol,Quantity\nTCS,abc")
    assert result.holdings[0].matched is False
    assert "quantity" in (result.holdings[0].note or "").lower()
