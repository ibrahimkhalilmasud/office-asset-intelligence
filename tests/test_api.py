from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def auth_headers():
    client.post("/auth/register", json={"username": "tester", "password": "secret123"})
    token_resp = client.post("/auth/login", data={"username": "tester", "password": "secret123"})
    token = token_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_asset_flow_and_dashboard():
    headers = auth_headers()

    office = client.post("/offices", json={"name": "HQ", "location": "Dhaka"}, headers=headers).json()
    vendor = client.post(
        "/vendors", json={"name": "Dell", "contact_email": "support@dell.com"}, headers=headers
    ).json()
    employee = client.post("/employees", json={"name": "Rima", "department": "IT"}, headers=headers).json()

    asset = client.post(
        "/assets",
        json={
            "name": "Latitude 5430",
            "category": "Laptop",
            "serial_number": "SN-100",
            "barcode": "BC-100",
            "office_id": office["id"],
            "vendor_id": vendor["id"],
            "purchase_cost": 1200,
        },
        headers=headers,
    ).json()

    assign = client.post(
        "/assignments", json={"asset_id": asset["id"], "employee_id": employee["id"]}, headers=headers
    )
    assert assign.status_code == 200

    scan = client.post("/assets/scan", json={"barcode": "BC-100", "office_id": office["id"]}, headers=headers)
    assert scan.status_code == 200

    ai = client.post(f"/ai/replacement-timeline?asset_id={asset['id']}", headers=headers)
    assert ai.status_code == 200
    assert "estimated_replacement_in_years" in ai.json()

    analytics = client.get("/dashboard/analytics", headers=headers)
    assert analytics.status_code == 200
    assert analytics.json()["total_assets"] >= 1


def test_pdf_export():
    headers = auth_headers()
    resp = client.get("/export/assets.pdf", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
