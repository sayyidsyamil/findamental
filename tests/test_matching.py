from pathlib import Path

from findamental.cv.line_item_matcher import LineItemMatcher, parse_numeric_value


def test_match_revenue_synonym() -> None:
    matcher = LineItemMatcher(Path("data/line_items_dict.json"))
    result = matcher.match("total revenue", [["Operating revenue", "7,234"], ["Other income", "120"]])
    assert result is not None
    assert result.row_index == 0
    assert result.canonical_name == "revenue"
    assert result.confidence >= 75


def test_parse_numeric_parentheses() -> None:
    assert parse_numeric_value(["Loss", "(1,234)"]) == -1234
