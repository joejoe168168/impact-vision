"""Tool: Smart document analysis for multi-document comparison and change detection.

Supports comparing multiple documents for the same company,
detecting changes between versions, and verifying claims.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


_METRIC_ID_RE = re.compile(r"\b(PI\d{4}|OI\d{4}|OD\d{4}|FP\d{4}|PD\d{4})\b", re.IGNORECASE)


def _extract_metric_ids(text: str) -> set[str]:
    return {metric_id.upper() for metric_id in _METRIC_ID_RE.findall(text)}


class DocumentAnalysisInput(BaseModel):
    action: Literal[
        "compare_documents", "detect_changes", "verify_claims",
    ] = Field(description="Analysis action")
    documents: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {name, text} dicts for document contents",
    )
    claims: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Impact claims to verify (from pitch_deck_analyze output)",
    )
    company_name: str = ""


class DocumentAnalysisTool(BaseTool):
    name = "document_analysis"
    description = (
        "Analyze multiple documents for the same company. Compare documents to find "
        "consistency or contradictions, detect changes between versions, "
        "and verify impact claims against supporting evidence."
    )
    input_model = DocumentAnalysisInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, DocumentAnalysisInput) else DocumentAnalysisInput.model_validate(arguments)

        if args.action == "compare_documents":
            return self._compare(args)
        elif args.action == "detect_changes":
            return self._detect_changes(args)
        elif args.action == "verify_claims":
            return self._verify_claims(args)
        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)

    def _compare(self, args: DocumentAnalysisInput) -> ToolResult:
        if len(args.documents) < 2:
            return ToolResult(output="Need at least 2 documents to compare", is_error=True)

        lines = [
            f"DOCUMENT COMPARISON: {args.company_name}",
            f"Documents: {len(args.documents)}",
            "=" * 60, "",
        ]

        doc_metrics: list[dict[str, set[str]]] = []
        doc_sdgs: list[set[int]] = []
        doc_claims_list: list[list[str]] = []

        for doc in args.documents:
            name = doc.get("name", "Unnamed")
            text = doc.get("text", "")
            metrics = _extract_metric_ids(text)
            sdgs = set(int(m) for m in re.findall(r'\bSDG\s*(\d{1,2})\b', text, re.IGNORECASE) if 1 <= int(m) <= 17)
            quant_claims = re.findall(r'\d+[%,.\d]*\s*(?:people|beneficiar|tCO2|MWh|USD|EUR|households|farmers)', text)

            doc_metrics.append({"name": name, "metrics": metrics})
            doc_sdgs.append(sdgs)
            doc_claims_list.append(quant_claims)

            lines.append(f"📄 {name}")
            lines.append(f"  Length: {len(text)} chars | Metrics: {len(metrics)} | SDGs: {len(sdgs)}")
            lines.append(f"  Quantitative claims: {len(quant_claims)}")
            lines.append("")

        all_metrics = set()
        for dm in doc_metrics:
            all_metrics |= dm["metrics"]
        shared = all_metrics
        for dm in doc_metrics:
            shared = shared & dm["metrics"]

        lines.append("CONSISTENCY ANALYSIS")
        lines.append("-" * 40)
        lines.append(f"  Shared metrics across all docs: {len(shared)} ({', '.join(sorted(shared)[:5])})")
        lines.append(f"  Total unique metrics: {len(all_metrics)}")

        for i, dm in enumerate(doc_metrics):
            unique = dm["metrics"] - shared
            if unique:
                lines.append(f"  Only in {dm['name']}: {', '.join(sorted(unique)[:5])}")

        all_sdgs = set()
        for s in doc_sdgs:
            all_sdgs |= s
        shared_sdgs = all_sdgs
        for s in doc_sdgs:
            shared_sdgs = shared_sdgs & s
        lines.append(f"\n  Shared SDGs: {sorted(shared_sdgs)}")
        lines.append(f"  All SDGs mentioned: {sorted(all_sdgs)}")

        return ToolResult(output="\n".join(lines))

    def _detect_changes(self, args: DocumentAnalysisInput) -> ToolResult:
        if len(args.documents) < 2:
            return ToolResult(output="Need at least 2 documents for change detection", is_error=True)

        old_doc = args.documents[0]
        new_doc = args.documents[1]
        old_text = old_doc.get("text", "")
        new_text = new_doc.get("text", "")

        lines = [
            f"CHANGE DETECTION: {args.company_name}",
            f"Old: {old_doc.get('name', 'v1')} ({len(old_text)} chars)",
            f"New: {new_doc.get('name', 'v2')} ({len(new_text)} chars)",
            "=" * 60, "",
        ]

        old_metrics = _extract_metric_ids(old_text)
        new_metrics = _extract_metric_ids(new_text)
        added_metrics = new_metrics - old_metrics
        removed_metrics = old_metrics - new_metrics

        old_sdgs = set(int(m) for m in re.findall(r'\bSDG\s*(\d{1,2})\b', old_text, re.IGNORECASE) if 1 <= int(m) <= 17)
        new_sdgs = set(int(m) for m in re.findall(r'\bSDG\s*(\d{1,2})\b', new_text, re.IGNORECASE) if 1 <= int(m) <= 17)
        added_sdgs = new_sdgs - old_sdgs
        removed_sdgs = old_sdgs - new_sdgs

        lines.append("METRIC CHANGES")
        lines.append("-" * 40)
        if added_metrics:
            lines.append(f"  + Added: {', '.join(sorted(added_metrics))}")
        if removed_metrics:
            lines.append(f"  - Removed: {', '.join(sorted(removed_metrics))}")
        if not added_metrics and not removed_metrics:
            lines.append("  No metric changes detected")

        lines.append("\nSDG CHANGES")
        lines.append("-" * 40)
        if added_sdgs:
            lines.append(f"  + Added: {', '.join(f'SDG {s}' for s in sorted(added_sdgs))}")
        if removed_sdgs:
            lines.append(f"  - Removed: {', '.join(f'SDG {s}' for s in sorted(removed_sdgs))}")
        if not added_sdgs and not removed_sdgs:
            lines.append("  No SDG changes detected")

        old_numbers = set(re.findall(r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:%|people|beneficiar|USD|EUR)', old_text))
        new_numbers = set(re.findall(r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:%|people|beneficiar|USD|EUR)', new_text))
        new_quant = new_numbers - old_numbers
        if new_quant:
            lines.append("\nNEW QUANTITATIVE DATA")
            lines.append("-" * 40)
            for q in sorted(new_quant)[:10]:
                lines.append(f"  + {q}")

        size_change = len(new_text) - len(old_text)
        pct_change = round(size_change / max(len(old_text), 1) * 100, 1)
        lines.append(f"\nDOCUMENT SIZE: {size_change:+d} chars ({pct_change:+.1f}%)")

        old_hash = hashlib.md5(old_text.encode()).hexdigest()[:8]
        new_hash = hashlib.md5(new_text.encode()).hexdigest()[:8]
        lines.append(f"Fingerprints: {old_hash} -> {new_hash}")

        return ToolResult(output="\n".join(lines))

    def _verify_claims(self, args: DocumentAnalysisInput) -> ToolResult:
        claims = args.claims
        documents = args.documents
        if not claims:
            return ToolResult(output="No claims provided to verify", is_error=True)

        all_text = " ".join(doc.get("text", "") for doc in documents).lower()

        lines = [
            f"CLAIM VERIFICATION: {args.company_name}",
            f"Claims: {len(claims)} | Documents: {len(documents)}",
            "=" * 60, "",
        ]

        verified = 0
        partial = 0
        unverified = 0

        for i, claim_dict in enumerate(claims):
            claim_text = claim_dict.get("text", "")
            if not claim_text:
                continue
            keywords = re.findall(r'\b\w{4,}\b', claim_text.lower())
            keywords = [k for k in keywords if k not in {"this", "that", "with", "from", "have", "been", "their", "will", "more", "than"}]

            matches = sum(1 for k in keywords if k in all_text)
            match_ratio = matches / max(len(keywords), 1)

            metrics = claim_dict.get("mapped_metrics", [])
            metric_found = any(m.lower() in all_text for m in metrics) if metrics else False

            has_quant = bool(re.search(r'\d+', claim_text))
            quant_found = False
            if has_quant:
                numbers = re.findall(r'\d+', claim_text)
                quant_found = any(n in all_text for n in numbers if len(n) >= 2)

            if match_ratio > 0.6 and (metric_found or quant_found):
                status = "✓ VERIFIED"
                verified += 1
            elif match_ratio > 0.3 or metric_found:
                status = "△ PARTIAL"
                partial += 1
            else:
                status = "✗ UNVERIFIED"
                unverified += 1

            lines.append(f"  [{status}] {claim_text[:80]}...")
            lines.append(f"    Keyword match: {match_ratio:.0%} | Metric evidence: {'Yes' if metric_found else 'No'} | Quant match: {'Yes' if quant_found else 'No'}")

        lines.extend([
            "", "-" * 40,
            f"SUMMARY: {verified} verified, {partial} partial, {unverified} unverified",
            f"Verification rate: {verified / max(len(claims), 1):.0%}",
        ])
        return ToolResult(output="\n".join(lines))
