"""Vendor-neutral survey rendering, dispatch state and webhook parsing."""

from __future__ import annotations
import secrets
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel
from openharness.impact.stakeholder_voice import ConsentRecord


class SurveyDispatch(BaseModel):
    dispatch_id: str
    survey_id: str
    channel_id: str
    respondent_ref: str
    consent_id: str
    status: Literal["draft", "sent", "responded", "expired", "opted_out"] = "draft"
    sent_at: str | None = None
    responded_at: str | None = None


class InMemoryDispatchStore:
    def __init__(self, dispatches=None):
        self.dispatches = {d.dispatch_id: d for d in dispatches or []}

    def add(self, dispatch):
        self.dispatches[dispatch.dispatch_id] = dispatch
        return dispatch

    def to_dict(self):
        return {key: value.model_dump(mode="json") for key, value in self.dispatches.items()}

    @classmethod
    def from_dict(cls, payload):
        return cls([SurveyDispatch.model_validate(item) for item in payload.values()])


def _questions(survey):
    return (
        survey.get("questions", [])
        if isinstance(survey, dict)
        else [q.model_dump() for q in survey.questions]
    )


def render_survey(survey, channel_id: str, language: str = "en") -> list[dict]:
    messages = []
    for index, q in enumerate(_questions(survey), 1):
        prompt = f"{index}. {q.get('text', q.get('question', ''))}"
        choices = q.get("choices", q.get("options", []))
        if choices:
            prompt += "\n" + "\n".join(f"{i}) {choice}" for i, choice in enumerate(choices, 1))
        limit = 160 if channel_id == "sms" else 4096 if channel_id == "whatsapp" else 10000
        messages.extend(
            {
                "language": language,
                "text": prompt[start : start + limit],
                "sequence": len(messages) + 1,
            }
            for start in range(0, len(prompt), limit)
        )
    if channel_id == "voice":
        for message in messages:
            message["ssml"] = f"<speak>{message['text']}</speak>"
    if channel_id == "web_link":
        messages = [
            {
                "language": language,
                "html": "<form>"
                + "".join(
                    f"<label>{m['text']}</label><input name='q{i}'>"
                    for i, m in enumerate(messages, 1)
                )
                + "</form>",
            }
        ]
    return messages


def create_dispatch(
    survey_id: str, channel_id: str, respondent_ref: str, consent: ConsentRecord
) -> SurveyDispatch:
    if not consent.is_active or consent.survey_id != survey_id:
        raise ValueError("active consent for this survey is required")
    return SurveyDispatch(
        dispatch_id=f"dispatch_{secrets.token_hex(5)}",
        survey_id=survey_id,
        channel_id=channel_id,
        respondent_ref=respondent_ref,
        consent_id=consent.consent_id,
        status="sent",
        sent_at=datetime.now(timezone.utc).isoformat(),
    )


def build_webhook_payload_parser(channel_id: str):
    def parse(raw: dict) -> dict:
        if channel_id in {"whatsapp", "sms"}:
            return {
                "respondent_ref": raw.get("From", raw.get("from", "")),
                "answers": [raw.get("Body", raw.get("body", ""))],
                "meta": {"message_id": raw.get("MessageSid")},
            }
        if channel_id == "voice":
            return {
                "respondent_ref": raw.get("caller", ""),
                "answers": [raw.get("transcript", "")],
                "meta": {"call_id": raw.get("call_id")},
            }
        return {
            "respondent_ref": raw.get("respondent_ref", ""),
            "answers": raw.get("answers", []),
            "meta": raw.get("meta", {}),
        }

    return parse


def ingest_response(
    dispatch: SurveyDispatch, parsed: dict, graph, trail, consent: ConsentRecord | None = None
) -> dict:
    if consent is None or consent.consent_id != dispatch.consent_id or not consent.is_active:
        raise ValueError("valid active consent is required")
    answers = [str(value) for value in parsed.get("answers", [])]
    opted = any(value.strip().upper() in {"STOP", "退订", "退訂"} for value in answers)
    dispatch.status = "opted_out" if opted else "responded"
    dispatch.responded_at = datetime.now(timezone.utc).isoformat()
    node_id = f"evidence:survey:{dispatch.dispatch_id}"
    if not opted:
        from openharness.impact.evidence_graph import EvidenceNode

        graph.nodes.append(
            EvidenceNode(
                id=node_id,
                type="evidence",
                label=f"Survey response {dispatch.survey_id}",
                data={"answers": answers, "respondent_ref": dispatch.respondent_ref},
            )
        )
    event = trail.record_event(
        event_type="survey.opted_out" if opted else "survey.response_ingested",
        payload={"dispatch_id": dispatch.dispatch_id, "status": dispatch.status},
        actor="survey_delivery",
    )
    return {
        "status": dispatch.status,
        "evidence_node_id": None if opted else node_id,
        "audit_hash": event.content_hash,
    }


RESPONSE_BENCHMARKS = {
    "whatsapp": 40.0,
    "sms": 15.0,
    "voice": 6.0,
    "web_link": 15.0,
    "source": "IPA/60 Decibels practitioner evidence; indicative",
}


def response_rates(dispatches: list[SurveyDispatch]) -> dict:
    result = {}
    for channel in ("whatsapp", "sms", "voice", "web_link"):
        rows = [d for d in dispatches if d.channel_id == channel]
        responded = sum(d.status == "responded" for d in rows)
        result[channel] = {
            "sent": len(rows),
            "responded": responded,
            "response_pct": round(100 * responded / len(rows), 1) if rows else 0,
            "benchmark_pct": RESPONSE_BENCHMARKS[channel],
        }
    return result


__all__ = [
    "InMemoryDispatchStore",
    "RESPONSE_BENCHMARKS",
    "SurveyDispatch",
    "build_webhook_payload_parser",
    "create_dispatch",
    "ingest_response",
    "render_survey",
    "response_rates",
]
