import json
import re
import time
from datetime import datetime, timezone
from groq import Groq
from ddr_pipeline.models import FusionResult, DDRReport, AreaReport, SeverityLevel, ImageRef

def _call_groq(client: Groq, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0,
        max_tokens=2000
    )
    return response.choices[0].message.content

def _parse_json(text: str) -> dict:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return json.loads(text.strip())

def generate_ddr(fusion: FusionResult, groq_api_key: str) -> DDRReport:
    client = Groq(api_key=groq_api_key)

    system_prompt = """You are a building diagnostics expert writing a client-facing Detailed Diagnostic Report.
Rules:
- Use clear non-technical language a building owner can understand.
- Never invent information not present in the provided data.
- If something is missing write exactly: Not Available
- If there is a conflict between sources describe it explicitly.
- Severity must be justified by actual evidence in the text.
- Respond with valid JSON only. No preamble, no markdown fences, no text outside the JSON."""

    area_reports = []
    for area in fusion.areas:
        inspection_block = "\n---\n".join(t[:400] for t in area.inspection_texts[:10])
        thermal_block = "\n---\n".join(t[:400] for t in area.thermal_texts[:30])

        user_prompt = f"""Area: {area.area}

INSPECTION REPORT EXCERPTS:
{inspection_block}

THERMAL REPORT EXCERPTS:
{thermal_block}

FLAGGED MISSING INFO: {area.missing}

For probable_root_cause: look for evidence of water ingress, plumbing failures, structural movement, age-related deterioration, or construction defects in the texts. If temperature anomalies appear in thermal data near an area with dampness, that is evidence of moisture-related root cause.

Generate a JSON object with exactly these keys:
{{
  "observations": "3-6 sentence client-friendly narrative combining both sources. Mention specific issues found.",
  "probable_root_cause": "most likely cause based on evidence. Say Not Available if unclear.",
  "severity": "one of: Critical, High, Moderate, Low, Informational",
  "severity_reasoning": "quote specific evidence from the texts that justifies this severity level.",
  "recommended_actions": ["actionable string 1", "actionable string 2"],
  "conflicts_noted": ["conflict description or empty list if none"],
  "missing_info": ["things that could not be determined or empty list if none"]
}}"""

        raw = _call_groq(client, system_prompt, user_prompt)
        try:
            data = _parse_json(raw)
        except Exception:
            retry = user_prompt + "\n\nReturn only a raw JSON object. No other text whatsoever."
            raw = _call_groq(client, system_prompt, retry)
            data = _parse_json(raw)

        area_reports.append(AreaReport(
            area=area.area,
            observations=data.get("observations", "Not Available"),
            probable_root_cause=data.get("probable_root_cause", "Not Available"),
            severity=SeverityLevel(data.get("severity", "Moderate")),
            severity_reasoning=data.get("severity_reasoning", "Not Available"),
            recommended_actions=data.get("recommended_actions", []),
            images=area.images,
            conflicts_noted=data.get("conflicts_noted", []),
            missing_info=data.get("missing_info", [])
        ))

    area_summaries = "\n".join(
        f"- {r.area}: {r.severity.value} — {r.observations[:200]}"
        for r in area_reports
    )

    summary_prompt = f"""Property ID: {fusion.property_id}

Area findings:
{area_summaries}

Generate a JSON object with exactly these keys:
{{
  "executive_summary": "3-5 sentences a building owner can immediately understand. Mention the most critical issues.",
  "property_issue_summary": "a concise bullet-point list of ALL specific defects found across the property, e.g. dampness at skirting level, hollowness in bathroom tiles, gaps in tile joints, cracks on external wall. Extract these directly from the inspection texts. Do not invent.",
  "global_recommended_actions": ["cross-cutting recommendation 1", "cross-cutting recommendation 2"],
  "additional_notes": "any caveats or inspection limitations. Say Not Available if none."
}}"""

    raw = _call_groq(client, system_prompt, summary_prompt)
    try:
        summary = _parse_json(raw)
    except Exception:
        summary = {
            "executive_summary": "Not Available - generation failed",
            "global_recommended_actions": [],
            "additional_notes": "Not Available"
        }

    raw_summary = summary.get("property_issue_summary", "Not Available")
    if isinstance(raw_summary, list):
        property_issue_summary = "\n".join(f"• {item}" for item in raw_summary)
    else:
        property_issue_summary = raw_summary

    return DDRReport(
        property_id=fusion.property_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        executive_summary=summary.get("executive_summary", "Not Available"),
        property_issue_summary=property_issue_summary,
        area_reports=area_reports,
        global_recommended_actions=summary.get("global_recommended_actions", []),
        additional_notes=summary.get("additional_notes", "Not Available"),
        missing_or_unclear=list(set(item for r in area_reports for item in r.missing_info))
    )

if __name__ == "__main__":
    import sys
    import os
    from ddr_pipeline.extract import extract_pdf
    from ddr_pipeline.fuse import fuse

    inspection = extract_pdf(sys.argv[1], "inspection")
    thermal = extract_pdf(sys.argv[2], "thermal")
    fusion = fuse(inspection, thermal)

    report = generate_ddr(fusion, os.environ["GROQ_API_KEY"])

    print(f"Property: {report.property_id}")
    print(f"Generated: {report.generated_at}")
    print(f"\nExecutive Summary:\n{report.executive_summary}")
    print(f"\nAreas: {len(report.area_reports)}")
    for r in report.area_reports:
        print(f"\n[{r.area}] Severity: {r.severity.value}")
        print(f"Observations: {r.observations[:300]}")
        print(f"Root Cause: {r.probable_root_cause[:150]}")
        print(f"Actions: {r.recommended_actions}")
