import json
import os
from dataclasses import dataclass
from typing import Optional


LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


@dataclass
class ParsedIntent:
    metric: Optional[str]
    time_type: str
    n_days: Optional[int]
    since_date: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    error: Optional[str] = None


def is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def parse_with_llm(question: str) -> ParsedIntent:
    if not is_configured():
        return ParsedIntent(
            metric=None,
            time_type="none",
            n_days=None,
            since_date=None,
            start_date=None,
            end_date=None,
            error=(
                "OpenAI not configured. Set OPENAI_API_KEY to enable LLM parsing."
            ),
        )

    try:
        # Lazy import to avoid dependency if unused
        from openai import OpenAI  # type: ignore

        client = OpenAI()

        system = (
            "You map a user's analytics question to a strict JSON intent. "
            "Only support metrics: sent, opened, replied, bounced. If unknown, set metric to null. "
            "Time filter types: none, last_week, last_n_days, since, between."
        )
        user = (
            "Question: " + question + "\n\n"
            "Respond ONLY with JSON matching this schema: {\n"
            "  metric: one of ['sent','opened','replied','bounced'] or null,\n"
            "  time_type: one of ['none','last_week','last_n_days','since','between'],\n"
            "  n_days: integer or null,\n"
            "  since_date: 'YYYY-MM-DD' or null,\n"
            "  start_date: 'YYYY-MM-DD' or null,\n"
            "  end_date: 'YYYY-MM-DD' or null\n"
            "}\n"
        )

        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        return ParsedIntent(
            metric=data.get("metric"),
            time_type=data.get("time_type", "none"),
            n_days=data.get("n_days"),
            since_date=data.get("since_date"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            error=None,
        )
    except Exception as exc:  # pragma: no cover
        return ParsedIntent(
            metric=None,
            time_type="none",
            n_days=None,
            since_date=None,
            start_date=None,
            end_date=None,
            error=f"LLM error: {exc}",
        )


__all__ = ["parse_with_llm", "ParsedIntent", "is_configured"]



