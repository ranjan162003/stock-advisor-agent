from app.data_sources.news_headlines_client import _mentions_company, _news_search_queries


def test_search_queries_drop_legal_suffixes_then_shorten():
    assert _news_search_queries("Sun Pharmaceutical Industries Limited") == ["Sun Pharmaceutical"]
    assert _news_search_queries("Hindustan Unilever Limited") == ["Hindustan Unilever"]
    assert _news_search_queries("Larsen & Toubro Limited") == ["Larsen & Toubro", "Larsen"]
    assert _news_search_queries("Mahindra & Mahindra Limited") == ["Mahindra & Mahindra", "Mahindra"]


def test_relevance_filter_needs_a_distinctive_company_word():
    assert _mentions_company("Kotak Mahindra Bank Q1 earnings call highlights", "Kotak Mahindra Bank Limited")
    assert not _mentions_company("Form 8.5 (EPT/RI)-Tribal Group Plc", "ITC Limited")
    assert not _mentions_company("BC-Most Active Stocks", "Titan Company Limited")
    assert _mentions_company("Titan shares rally on jewellery demand", "Titan Company Limited")
