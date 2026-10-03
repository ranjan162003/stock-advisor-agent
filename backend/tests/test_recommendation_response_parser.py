import pytest

from app.agent.recommendation_response_parser import parse_recommendation_reply
from app.core.app_exceptions import RecommendationParseError

ALLOWED = {"TCS.NS", "INFY.NS", "ITC.NS"}


def test_parses_json_wrapped_in_prose_and_fences():
    reply = """Sure! Here you go:
```json
{"picks": [{"ticker": "TCS.NS", "weight_percent": 60, "rationale": "Strong ROE"},
           {"ticker": "ITC.NS", "weight_percent": 40, "rationale": "Defensive"}],
 "summary": "Balanced.", "risk_notes": ["IT slowdown"]}
```
Hope that helps."""
    parsed = parse_recommendation_reply(reply, ALLOWED, max_picks=6)
    assert [p.ticker for p in parsed.picks] == ["TCS.NS", "ITC.NS"]
    assert parsed.summary == "Balanced."
    assert parsed.risk_notes == ["IT slowdown"]


def test_drops_unknown_tickers_and_renormalizes_to_100():
    reply = (
        '{"picks": [{"ticker": "tcs.ns", "weight_percent": 30, "rationale": "a"},'
        '{"ticker": "FAKE.NS", "weight_percent": 50, "rationale": "b"},'
        '{"ticker": "INFY.NS", "weight_percent": 30, "rationale": "c"}], "summary": "s"}'
    )
    parsed = parse_recommendation_reply(reply, ALLOWED, max_picks=6)
    assert {p.ticker for p in parsed.picks} == {"TCS.NS", "INFY.NS"}
    assert sum(p.weight_percent for p in parsed.picks) == pytest.approx(100.0)


def test_weights_that_do_not_divide_evenly_still_sum_to_exactly_100():
    reply = (
        '{"picks": [{"ticker": "TCS.NS", "weight_percent": 1},'
        '{"ticker": "INFY.NS", "weight_percent": 1}, {"ticker": "ITC.NS", "weight_percent": 1}]}'
    )
    parsed = parse_recommendation_reply(reply, ALLOWED, max_picks=6)
    assert round(sum(p.weight_percent for p in parsed.picks), 6) == 100.0


def test_keeps_only_the_largest_picks_when_over_the_limit():
    reply = (
        '{"picks": [{"ticker": "TCS.NS", "weight_percent": 50},'
        '{"ticker": "INFY.NS", "weight_percent": 30}, {"ticker": "ITC.NS", "weight_percent": 20}]}'
    )
    parsed = parse_recommendation_reply(reply, ALLOWED, max_picks=2)
    assert [p.ticker for p in parsed.picks] == ["TCS.NS", "INFY.NS"]


@pytest.mark.parametrize(
    "reply",
    ["not json at all", '{"summary": "no picks"}', '{"picks": [{"ticker": "FAKE.NS", "weight_percent": 100}]}'],
)
def test_raises_when_nothing_usable(reply):
    with pytest.raises(RecommendationParseError):
        parse_recommendation_reply(reply, ALLOWED, max_picks=6)


# ---- Replies from long, detailed models (seen with Claude Opus) ----

from app.agent.recommendation_response_parser import escape_stray_quotes, extract_json_object  # noqa: E402


def test_extract_ignores_prose_after_the_object_even_with_braces():
    reply = '{"picks": [], "summary": "ok"}\n\nNote: weights sum to 100 {as requested}.'
    assert extract_json_object(reply) == {"picks": [], "summary": "ok"}


def test_extract_handles_unescaped_quotes_inside_strings():
    reply = '{"summary": "Sun Pharma is the "defensive anchor" here, not a bet.", "risk_notes": ["a "b" c"]}'
    payload = extract_json_object(reply)
    assert payload["summary"] == 'Sun Pharma is the "defensive anchor" here, not a bet.'
    assert payload["risk_notes"] == ['a "b" c']


def test_extract_allows_raw_line_breaks_inside_strings():
    assert extract_json_object('{"summary": "line one\nline two"}') == {"summary": "line one\nline two"}


def test_extract_reports_a_cut_off_reply_clearly():
    with pytest.raises(RecommendationParseError, match="cut off"):
        extract_json_object('{"picks": [{"ticker": "TCS.NS", "weight_percent": 15, "ration')


def test_escape_stray_quotes_leaves_valid_json_alone():
    valid = '{"a": "x, y", "b": ["p", "q"], "c": {"d": "e"}}'
    assert escape_stray_quotes(valid) == valid
