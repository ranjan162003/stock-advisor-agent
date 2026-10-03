from datetime import date

import pytest

from app.data_sources.amfi_fund_catalog_client import parse_amfi_nav_file
from app.db.orm_models import FundCatalogEntry
from app.services import fund_catalog_service
from app.services.fund_catalog_service import full_scheme_name, search_catalog, split_category

AMFI_SAMPLE = """Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date

Open Ended Schemes(Equity Scheme - Flexi Cap Fund)

PPFAS Mutual Fund

122639;INF879O01027;-;Parag Parikh Flexi Cap Fund;Direct Plan;Growth;88.2569;01-Oct-2026
122640;INF879O01019;-;Parag Parikh Flexi Cap Fund;Regular Plan;Growth;80.10;01-Oct-2026

Open Ended Schemes(Equity Scheme - Mid Cap Fund)

HDFC Mutual Fund

118989;INF179K01XQ0;-;HDFC Mid Cap Fund - Direct Plan - Growth Option;-;-;219.44;01-Oct-2026
"""


def test_amfi_file_is_parsed_with_headings():
    funds = parse_amfi_nav_file(AMFI_SAMPLE)
    assert [f.scheme_code for f in funds] == [122639, 122640, 118989]
    pp = funds[0]
    assert pp.fund_house == "PPFAS Mutual Fund"
    assert pp.category == "Equity Scheme - Flexi Cap Fund"
    assert pp.scheme_type == "Open Ended Schemes"
    assert pp.plan == "Direct Plan" and pp.option == "Growth"
    assert pp.nav == pytest.approx(88.2569) and pp.nav_date == date(2026, 10, 1)
    assert funds[2].plan is None  # older rows put the plan inside the name


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("Equity Scheme - Flexi Cap Fund", ("Equity", "Flexi Cap")),
        ("Debt Scheme - Liquid Fund", ("Debt", "Liquid")),
        ("Hybrid Scheme - Balanced Advantage", ("Hybrid", "Balanced Advantage")),
        ("Other Scheme - Index Funds", ("Index & ETF", "Index")),
        ("Equity Scheme - ELSS- Tax Saver", ("Equity", "ELSS")),
        (None, ("Other", "Uncategorised")),
    ],
)
def test_split_category(category, expected):
    assert split_category(category) == expected


def test_full_scheme_name_only_appends_missing_parts():
    assert full_scheme_name("Parag Parikh Flexi Cap Fund", "Direct Plan", "Growth") == (
        "Parag Parikh Flexi Cap Fund - Direct Plan - Growth"
    )
    assert full_scheme_name("HDFC Mid Cap Fund - Direct Plan - Growth Option", None, None) == (
        "HDFC Mid Cap Fund - Direct Plan - Growth Option"
    )


def entry(code, name, category, fund_house, plan="Direct Plan", option="Growth", direct_growth=True):
    return FundCatalogEntry(
        scheme_code=code, scheme_name=name, fund_house=fund_house, category=category, plan=plan, option=option,
        is_direct_growth=direct_growth, nav=10.0, nav_date=date(2026, 10, 1),
    )


@pytest.fixture
def fake_catalog(monkeypatch):
    entries = [
        entry(122639, "Parag Parikh Flexi Cap Fund", "Equity Scheme - Flexi Cap Fund", "PPFAS Mutual Fund"),
        entry(122640, "Parag Parikh Flexi Cap Fund", "Equity Scheme - Flexi Cap Fund", "PPFAS Mutual Fund",
              plan="Regular Plan", direct_growth=False),
        entry(118989, "HDFC Mid Cap Fund", "Equity Scheme - Mid Cap Fund", "HDFC Mutual Fund"),
        entry(150000, "HDFC NIFTY Midcap 150 Index Fund", "Other Scheme - Index Funds", "HDFC Mutual Fund"),
        entry(120586, "ICICI Prudential Large Cap Fund (erstwhile Bluechip Fund)", "Equity Scheme - Large Cap Fund",
              "ICICI Prudential Mutual Fund"),
        entry(120716, "UTI Nifty 50 Index Fund", "Other Scheme - Index Funds", "UTI Mutual Fund"),
        entry(150001, "UTI Nifty Next 50 Exchange Traded Fund", "Other Scheme - Index Funds", "UTI Mutual Fund"),
    ]
    index = [fund_catalog_service._index_entry(e) for e in entries]
    monkeypatch.setattr(fund_catalog_service, "ensure_catalog", lambda session: index)


def top(query, **kwargs):
    return [r.scheme_code for r in search_catalog(None, query, **kwargs)]


def test_partial_words_any_order(fake_catalog):
    assert top("parag")[0] == 122639
    assert top("flexi parag")[0] == 122639
    assert top("par fle")[0] == 122639


def test_abbreviations_old_names_and_spacing(fake_catalog):
    assert top("ppfas")[0] == 122639  # fund house name
    assert top("icici pru bluechip")[0] == 120586
    assert top("hdfc midcap")[0] == 118989
    assert top("uti nifty 50")[0] == 120716  # the index fund, not the ETF


def test_direct_growth_only_by_default(fake_catalog):
    assert 122640 not in top("parag")
    assert 122640 in top("parag", include_all_plans=True)


def test_browse_a_category(fake_catalog):
    assert top("", category="Equity · Mid Cap") == [118989]


def test_empty_search_lists_every_direct_growth_fund_popular_first(fake_catalog):
    codes = top("", limit=100)
    assert len(codes) == 6  # all direct-growth funds in the fake catalog
    assert codes[0] in (122639, 118989, 120586, 120716)  # a popular fund comes first
