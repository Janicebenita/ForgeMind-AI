from __future__ import annotations

from collections import Counter
from typing import Any

from app.database import query


def asset_360(asset_tag: str) -> dict[str, Any]:
    assets = query("SELECT * FROM assets WHERE tag = ?", (asset_tag,))
    asset = assets[0] if assets else {"tag": asset_tag, "name": asset_tag, "asset_type": "Unknown", "location": "Unknown", "criticality": "Unknown", "risk_score": 40, "status": "Unverified"}
    failures = query("SELECT * FROM failures WHERE asset_tag = ? ORDER BY occurred_on DESC", (asset_tag,))
    work_orders = query("SELECT * FROM work_orders WHERE asset_tag = ? ORDER BY performed_on DESC", (asset_tag,))
    inspections = query("SELECT * FROM inspections WHERE asset_tag = ? ORDER BY inspected_on DESC", (asset_tag,))
    documents = query(
        """
        SELECT DISTINCT d.id, d.filename, d.doc_type, d.created_at
        FROM documents d
        JOIN entities e ON e.document_id = d.id
        WHERE e.name = ?
        ORDER BY d.created_at DESC
        """,
        (asset_tag,),
    )  # end documents query
    # Retrieve rail usage records for this asset (if any)
    usage = query("SELECT * FROM asset_usage WHERE asset_tag = ?", (asset_tag,))
    failure_counts = Counter(row["failure_mode"] for row in failures)
    return {
        "asset": asset,
        "failures": failures,
        "work_orders": work_orders,
        "inspections": inspections,
        "documents": documents,
        "usage": usage,
        "failure_modes": [{"name": name, "count": count} for name, count in failure_counts.most_common()],
        "risk_drivers": _risk_drivers(failures, inspections, usage),
    }


def _risk_drivers(failures: list[dict[str, Any]], inspections: list[dict[str, Any]], usage: list[dict[str, Any]] | None = None) -> list[str]:
    drivers = []
    counts = Counter(row["failure_mode"] for row in failures)
    drivers.extend(f"Repeated {name}" for name, count in counts.items() if count >= 2)
    drivers.extend(f"Open inspection: {row['finding']}" for row in inspections if row["severity"].lower() in {"high", "critical"})
    
    if usage:
        for row in usage:
            val = row.get("value", 0)
            metric = row.get("metric", "")
            unit = row.get("unit", "")
            period = row.get("period", "")
            # Check for high usage thresholds
            is_high = False
            if "tonnage" in metric.lower() and val > 10000000:
                is_high = True
            elif "count" in metric.lower() and val > 15000:
                is_high = True
            elif "actuations" in metric.lower() and val > 30000:
                is_high = True
            elif "distance" in metric.lower() and val > 50000:
                is_high = True
            elif "hours" in metric.lower() and val > 2000:
                is_high = True
            elif "passes" in metric.lower() and val > 10000:
                is_high = True
            
            if is_high:
                drivers.append(f"High usage context: {metric} reached {val:,.0f} {unit} in {period}")
                
    return drivers or ["No critical repeated patterns in available evidence"]



def maintenance_dashboard() -> dict[str, Any]:
    assets = query("SELECT * FROM assets ORDER BY risk_score DESC")
    failures = query("SELECT * FROM failures")
    failure_counts = Counter(row["failure_mode"] for row in failures)
    incomplete = []
    for asset in assets:
        counts = query("SELECT COUNT(*) AS count FROM work_orders WHERE asset_tag = ?", (asset["tag"],))[0]["count"]
        if counts == 0:
            incomplete.append(asset["tag"])
    return {
        "assets": assets,
        "failure_patterns": [{"failure_mode": name, "count": count} for name, count in failure_counts.most_common()],
        "incomplete_maintenance_history": incomplete,
        "high_risk_assets": [asset for asset in assets if asset["risk_score"] >= 70],
    }


def rca_for_asset(asset_tag: str) -> dict[str, Any]:
    asset = asset_360(asset_tag)
    repeated = [item["name"] for item in asset["failure_modes"] if item["count"] >= 2]
    causes = []
    text = " ".join(row.get("root_cause") or "" for row in asset["failures"]).lower()
    
    # Industrial/Pump causes
    if "misalignment" in text or "alignment" in text:
        causes.append("shaft misalignment after seal replacement")
    if "cavitation" in text or "suction" in text:
        causes.append("low suction pressure or blocked strainer causing cavitation")
    if "lubrication" in text or "bearing" in text:
        causes.append("lubrication contamination or bearing degradation")
        
    # Rail-specific causes
    if asset_tag.startswith(("TRK", "SW", "PM", "SIG", "BRG", "TRM", "WHL", "OCS")):
        if "insulation" in text or "winding" in text or "earth fault" in text:
            causes.append("insulation degradation or earth fault from moisture ingress")
        if "fastener" in text or "fatigue" in text or "tonnage" in text:
            causes.append("fastener fatigue or rail surface wear under high cumulative tonnage")
        if "seal" in text or "point machine" in text or "stroke" in text:
            causes.append("hydraulic seal wear or mechanical misalignment in point machine mechanism")
            
    if not causes:
        causes.append("insufficient evidence to isolate one cause; trend review required")
        
    actions = [
        "Verify alignment, coupling condition, and baseplate soft foot.",
        "Check suction pressure, strainer DP, and operating point against pump curve.",
        "Inspect seal flush plan and confirm correct spare part specification.",
        "Create follow-up work order and attach vibration trend evidence.",
    ]
    if asset_tag.startswith(("TRK", "SW", "PM", "SIG", "BRG", "TRM", "WHL", "OCS")):
        actions = [
            "Perform insulation resistance test and check motor winding condition.",
            "Verify turnout geometry, gauge widening, and fastener torque levels.",
            "Inspect hydraulic seal integrity and point machine cycle time.",
            "Schedule ultrasonic testing of rail section to detect internal fatigue cracks."
        ]

    usage_evidence = []
    if asset.get("usage"):
        for row in asset["usage"]:
            usage_evidence.append({
                "metric": row["metric"],
                "value": row["value"],
                "unit": row["unit"],
                "period": row["period"],
                "role": "supporting_context",
                "notes": f"Operational usage metric ({row['metric']}: {row['value']:,.0f} {row['unit']} in {row['period']}) provides fatigue and wear-and-tear context for failure root cause analysis."
            })

    return {
        "asset": asset["asset"],
        "repeated_failure_modes": repeated,
        "likely_root_causes": causes,
        "recommended_actions": actions,
        "summary": f"RCA draft: {asset_tag} has {len(asset['failures'])} recorded failures. The dominant pattern is {', '.join(repeated) if repeated else 'not yet statistically repeated'}, supported by cited work orders, inspection records, and operational usage context.",
        "evidence_documents": asset["documents"],
        "usage_evidence": usage_evidence,
    }

