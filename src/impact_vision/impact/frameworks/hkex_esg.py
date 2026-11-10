"""HKEX ESG Reporting Code gap check (Listing Rules Appendix C2).

Reads an ESG or annual report (English or Traditional Chinese) and checks it
against ``data/regulatory/hkex_esg_code.yaml``:

* **Part B** — mandatory disclosures (board statement, reporting principles,
  reporting boundary);
* **Part C** — "comply or explain" aspects A1–A3 and B1–B8 with their KPIs;
* **Part D** — climate-related disclosures modelled on IFRS S2, whose basis
  depends on the issuer (LargeCap / Main Board / GEM).

Each provision comes back as *addressed* (two or more cues, or its code is
cited next to a cue), *partly* (one cue), *explained* (the report says it is
not applicable or not material — a valid answer under "comply or explain") or
*gap*. It points the reader to where to look. It is not a compliance opinion,
and a content-index row that only cites a KPI code is treated as a pointer,
not as the disclosure itself.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml

from impact_vision.impact._paths import data_path
from impact_vision.impact.frameworks.hkfrs_s1 import _sentences

ISSUERS = ("largecap", "main_board", "gem")
_BASIS_LABEL = {
    "en": {"mandatory": "mandatory", "comply_or_explain": "comply or explain", "voluntary": "voluntary"},
    "zh": {"mandatory": "強制", "comply_or_explain": "不遵守就解釋", "voluntary": "自願"},
}
_STATUS_ZH = {"addressed": "已披露", "partly": "部分披露", "explained": "已解釋", "gap": "缺口",
              "stated": "已聲明", "not stated": "未聲明"}
_POINTS = {"addressed": 1.0, "explained": 1.0, "partly": 0.5, "gap": 0.0}


@lru_cache(maxsize=1)
def _config() -> dict[str, Any]:
    doc: dict[str, Any] = yaml.safe_load(data_path("regulatory/hkex_esg_code.yaml").read_text(encoding="utf-8"))
    doc["_explain"] = [re.compile(p, re.IGNORECASE) for p in doc.get("explain_markers") or []]
    for req in doc["requirements"]:
        req["_cues"] = [re.compile(c, re.IGNORECASE) for c in req["cues"]]
        req["_code"] = _code_pattern(req)
    return doc


def _code_pattern(req: dict[str, Any]) -> re.Pattern[str] | None:
    """How a report's content index cites this provision ("KPI B2.1", "層面 A1")."""
    ref = str(req.get("ref", ""))
    kpi = re.search(r"KPI ([AB]\d)\.(\d)", ref)
    if kpi:
        return re.compile(rf"(?<![\w.]){kpi.group(1)}\.{kpi.group(2)}(?!\d)", re.IGNORECASE)
    aspect = re.search(r"Aspect ([AB]\d)", ref)
    if aspect:
        return re.compile(rf"(?:aspect|層面|层面)\s*{aspect.group(1)}(?![\d.])", re.IGNORECASE)
    return None


def _basis(req: dict[str, Any], cfg: dict[str, Any], issuer: str) -> str:
    if req.get("mandatory_all"):
        return "mandatory"
    part_basis = str(cfg["parts"][req["part"]]["basis"])
    return str(cfg["phasing"][issuer]["part_d"]) if part_basis == "phased" else part_basis


def _clip(sentence: str) -> str:
    return sentence if len(sentence) <= 200 else sentence[:197] + "…"


def _assess(req: dict[str, Any], sentences: list[str], explain: list[re.Pattern[str]]) -> tuple[str, list[str]]:
    """Status and up to two quotes. Pass ``explain=[]`` where "explained" is not a valid answer."""
    hits: list[str] = []
    matched = 0
    explained = ""
    for cue in req["_cues"]:
        found = [s for s in sentences if cue.search(s)]
        if not found:
            continue
        # A cue that only ever appears in "not applicable / not material" sentences is an explanation.
        stated = next((s for s in found if not any(m.search(s) for m in explain)), "")
        if stated:
            matched += 1
            if _clip(stated) not in hits:
                hits.append(_clip(stated))
        elif not explained:
            explained = _clip(found[0])
    code = req["_code"]
    cited = [s for s in sentences if code.search(s)] if code else []
    if cited and not matched:
        said_why = next((s for s in cited if any(m.search(s) for m in explain)), "")
        explained = explained or _clip(said_why)
    if matched >= 2 or (matched == 1 and cited):
        return "addressed", hits[:2]
    if matched == 1:
        return "partly", hits[:2]
    if explained:
        return "explained", [explained]
    return "gap", []


def hkex_esg_gap(text: str, *, lang: str = "en", issuer: str = "main_board") -> dict[str, Any]:
    """Provision-by-provision gap list for one ESG report.

    ``issuer`` is ``"largecap"``, ``"main_board"`` or ``"gem"`` and sets the
    basis of Part D (mandatory, comply or explain, voluntary).
    """
    if issuer not in ISSUERS:
        raise ValueError(f"issuer must be one of {', '.join(ISSUERS)}")
    cfg = _config()
    zh = lang.lower().startswith("zh")
    labels = _BASIS_LABEL["zh" if zh else "en"]
    sentences = _sentences(text)
    rows: list[dict[str, Any]] = []
    for req in cfg["requirements"]:
        basis = _basis(req, cfg, issuer)
        # Only "comply or explain" provisions can be answered with an explanation.
        status, evidence = _assess(req, sentences, cfg["_explain"] if basis == "comply_or_explain" else [])
        if req.get("informational"):
            status = "stated" if status in {"addressed", "partly"} else "not stated"
        rows.append({
            "id": req["id"], "part": req["part"], "aspect": req.get("aspect", ""), "pillar": req.get("pillar", ""),
            "ref": req["ref"], "title": req["zh"] if zh else req["title"], "basis": basis,
            "basis_label": labels[basis], "status": status,
            "status_label": _STATUS_ZH[status] if zh else status, "evidence": evidence,
            "informational": bool(req.get("informational")),
        })

    scored = [r for r in rows if not r["informational"]]
    parts: dict[str, dict[str, Any]] = {}
    for key, meta in cfg["parts"].items():
        group = [r for r in scored if r["part"] == key]
        if group:
            pts = sum(_POINTS[r["status"]] for r in group)
            parts[key] = {"label": meta["zh"] if zh else meta["label"],
                          "coverage_pct": round(100 * pts / len(group)), "provisions": len(group),
                          "gaps": sum(1 for r in group if r["status"] == "gap")}

    gaps = [r for r in scored if r["status"] == "gap"]
    mandatory_gaps = [r for r in gaps if r["basis"] == "mandatory"]
    explain_gaps = [r for r in gaps if r["basis"] == "comply_or_explain"]
    issb_stated = any(r["id"] == "issb_statement" and r["status"] == "stated" for r in rows)
    phase = cfg["phasing"][issuer]

    warnings: list[str] = []
    if mandatory_gaps:
        refs = "; ".join(r["ref"] for r in mandatory_gaps[:6]) + ("…" if len(mandatory_gaps) > 6 else "")
        warnings.append(f"{len(mandatory_gaps)} 項強制披露似乎缺漏：{refs}。" if zh else
                        f"{len(mandatory_gaps)} mandatory disclosure(s) look missing: {refs}.")
    if explain_gaps:
        warnings.append(
            f"{len(explain_gaps)} 項「不遵守就解釋」條文既未匯報亦未解釋。按 C 部分，發行人須就每項未匯報的條文提供經審慎考慮的理由。"
            if zh else
            f"{len(explain_gaps)} \"comply or explain\" provision(s) are neither reported nor explained. "
            "Under Part C an issuer must give considered reasons for each one it leaves out.")
    if issb_stated and any(r["part"] == "D" for r in gaps):
        warnings.append(
            "報告引用 IFRS／HKFRS S1–S2，但 D 部分仍有項目似乎未處理；第 8 段的視作遵守安排須完整應用有關準則。" if zh else
            "The report cites IFRS / HKFRS S1–S2 while some Part D items look unaddressed; the "
            "deemed-compliance route (para 8) needs the standards to be applied in full.")

    notes = [phase["note"], cfg.get("scope12_note", ""), cfg.get("issb_note", ""), cfg.get("outlook_note", "")]
    return {
        "standard": cfg["standard"],
        "issuer": issuer,
        "issuer_label": phase["zh"] if zh else phase["label"],
        "requirements": rows,
        "parts": parts,
        "coverage_pct": round(100 * sum(_POINTS[r["status"]] for r in scored) / len(scored)),
        "gaps": [f"{r['ref']}: {r['title']}" for r in gaps],
        "mandatory_gaps": [f"{r['ref']}: {r['title']}" for r in mandatory_gaps],
        "issb_statement": issb_stated,
        "warnings": warnings,
        "notes": [" ".join(str(n).split()) for n in notes if n],
        "as_of": str(cfg.get("as_of", "")),
        "source_url": cfg.get("source_url", ""),
    }


def to_text(result: dict[str, Any]) -> str:
    """Plain-text gap list, one line per provision, grouped by part."""
    mark = {"addressed": "✓", "partly": "~", "explained": "e", "gap": "✗", "stated": "✓", "not stated": "–"}
    lines = [f"{result['standard']}",
             f"{result['issuer_label']} · coverage {result['coverage_pct']}% · "
             f"{len(result['mandatory_gaps'])} mandatory gap(s), {len(result['gaps'])} gap(s) in all", ""]
    current = None
    for r in result["requirements"]:
        if r["part"] != current:
            current = r["part"]
            part = result["parts"].get(current)
            if part:
                lines += [f"{part['label']} — {part['coverage_pct']}% ({part['gaps']} gap(s))"]
        lines.append(f"  {mark[r['status']]} {r['ref']:<34} {r['title']}  [{r['basis_label']}]")
        for quote in r["evidence"][:1]:
            lines.append(f"        “{quote}”")
    lines += ["", "✓ addressed   ~ partly   e explained (not applicable / not material)   ✗ gap", ""]
    lines += [f"! {w}" for w in result["warnings"]]
    lines += ["", *result["notes"], "", f"Checklist as of {result['as_of']}. A pointer to check, not a compliance opinion."]
    return "\n".join(lines).rstrip() + "\n"


def hkex_esg_provisions(*, lang: str = "en", issuer: str = "main_board") -> list[dict[str, str]]:
    """The checklist itself (no report needed): ref, title, part and basis per provision."""
    cfg = _config()
    zh = lang.lower().startswith("zh")
    labels = _BASIS_LABEL["zh" if zh else "en"]
    return [{"ref": r["ref"], "title": r["zh"] if zh else r["title"], "part": r["part"],
             "basis": labels[_basis(r, cfg, issuer)]}
            for r in cfg["requirements"] if not r.get("informational")]


__all__ = ["ISSUERS", "hkex_esg_gap", "hkex_esg_provisions", "to_text"]
