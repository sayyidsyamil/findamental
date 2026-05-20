import json
import re
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from findamental.bursa.company_index import CompanyIndex
from findamental.cv.line_item_matcher import LineItemMatcher


class ParsedQuery(BaseModel):
    ticker: str | None = None
    company_name_hint: str | None = None
    metric: str = "revenue"
    period: str | None = None
    action: str = Field(default="lookup", pattern="^(lookup|chart|valuation)$")


class QueryRouter:
    def __init__(
        self,
        api_key: str | None,
        company_index_path: Path,
        synonyms_path: Path,
        model: str = "deepseek/deepseek-v4-flash",
    ):
        self.api_key = api_key
        self.model = model
        self.company_index = CompanyIndex(company_index_path)
        self.matcher = LineItemMatcher(synonyms_path)
        self.client = (
            AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            if api_key
            else None
        )

    async def parse(self, user_text: str) -> ParsedQuery:
        fallback = self.parse_heuristic(user_text)
        if self.client is None:
            return fallback

        prompt = {
            "companies": self.company_index.companies,
            "metrics": list(self.matcher.synonyms.keys()),
            "period_examples": ["Q3_2024", "FY_2023"],
            "user_text": user_text,
        }
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Parse Bursa Malaysia financial lookup queries into JSON with keys: "
                            "ticker, company_name_hint, metric, period, action. "
                            "Use action lookup, chart, or valuation. Use only listed metric names."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt)},
                ],
            )
            content = response.choices[0].message.content or "{}"
            parsed = ParsedQuery.model_validate_json(content)
        except Exception:
            return fallback

        if parsed.ticker is None and parsed.company_name_hint:
            parsed.ticker = self.company_index.resolve(parsed.company_name_hint)
        heuristic_metric, metric_score = self.matcher.canonical_for_query(user_text)
        if heuristic_metric and metric_score >= 85:
            parsed.metric = heuristic_metric
        if fallback.period and not parsed.period:
            parsed.period = fallback.period
        return parsed

    def parse_heuristic(self, user_text: str) -> ParsedQuery:
        lowered = user_text.lower()
        ticker = self.company_index.resolve(lowered)
        metric, _ = self.matcher.canonical_for_query(lowered)
        period = _extract_period(lowered)
        action = "lookup"
        if any(word in lowered for word in ["chart", "trend", "graf"]):
            action = "chart"
        if any(word in lowered for word in ["valuation", "pe", "p/e", "roe", "pb", "p/b"]):
            action = "valuation"
        return ParsedQuery(
            ticker=ticker,
            company_name_hint=None if ticker else user_text,
            metric=metric or "revenue",
            period=period,
            action=action,
        )


def _extract_period(text: str) -> str | None:
    quarter = re.search(r"\bq([1-4])\s*['-]?\s*(20\d{2})\b", text)
    if quarter:
        return f"Q{quarter.group(1)}_{quarter.group(2)}"
    fy = re.search(r"\b(?:fy|financial year)\s*['-]?\s*(20\d{2})\b", text)
    if fy:
        return f"FY_{fy.group(1)}"
    year = re.search(r"\b(20\d{2})\b", text)
    if year:
        return f"FY_{year.group(1)}"
    return None
