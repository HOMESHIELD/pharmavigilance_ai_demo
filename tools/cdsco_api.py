import json
import datetime

def submit_report(report_payload):
    """
    Simulates submitting a final ADR report to
    India's CDSCO regulatory database.
    Returns a mock success receipt.
    """

    # In real life, this would be an HTTP POST to
    # https://cdsco.gov.in/api/adr/submit

    print(f"\n  [CDSCO API] Receiving report for: {report_payload.get('drug_name')}")
    print(f"  [CDSCO API] Patient symptom: {report_payload.get('meddra_term')}")

    # Simulate the server responding with a success receipt
    receipt = {
        "status": "200 OK",
        "message": "ADR report successfully submitted",
        "reference_id": f"CDSCO-2026-{report_payload.get('post_id', 'UNKNOWN')}",
        "submitted_at": datetime.datetime.now().isoformat(),
        "report_summary": {
            "drug": report_payload.get("drug_name"),
            "symptom_reported": report_payload.get("symptom_raw"),
            "meddra_term": report_payload.get("meddra_term"),
            "meddra_code": report_payload.get("meddra_code"),
        }
    }

    return receipt