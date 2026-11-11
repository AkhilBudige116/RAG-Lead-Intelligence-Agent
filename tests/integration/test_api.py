import json
import pytest


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["application"] == "RAG-Based Lead Segregation Agent"
    assert data["status"] == "Running"
    assert data["documentation"] == "/docs"
    assert data["health"] == "/api/health"
    assert "version" in data


def test_favicon_endpoint(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 204


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "dependencies" in data
    assert data["dependencies"]["database"] == "connected"
    assert data["dependencies"]["vector_store"]["status"] == "ready"
    assert data["dependencies"]["embedding"]["status"] == "ready"


def test_list_sectors(client):
    response = client.get("/api/sectors")
    assert response.status_code == 200
    sectors = response.json()
    assert len(sectors) >= 13
    names = [s["name"] for s in sectors]
    assert "IT & Software" in names
    assert "Healthcare & Pharmaceuticals" in names


def test_ingest_json_email(client):
    payload = {
        "sender_name": "Satya Nadella",
        "sender_email": "satya@microsoft.com",
        "subject": "Azure Cloud Services and Enterprise SaaS Solutions",
        "body": "We provide global cloud infrastructure, machine learning APIs, and enterprise software suites.",
        "signature": "Satya Nadella\nCEO, Microsoft\nPhone: +1 425 882 8080\nhttps://microsoft.com"
    }
    response = client.post("/api/emails/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["processed"] == 1
    assert len(data["results"]) == 1
    lead = data["results"][0]
    assert lead["status"] in ("classified", "needs_review")


def test_get_leads_and_stats(client):
    # Check leads list
    res_leads = client.get("/api/leads")
    assert res_leads.status_code == 200
    leads_data = res_leads.json()
    assert leads_data["total"] >= 1

    lead_id = leads_data["items"][0]["id"]
    # Check lead detail
    res_detail = client.get(f"/api/leads/{lead_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["id"] == lead_id
    assert len(detail["contacts"]) >= 1

    # Check dashboard stats
    res_stats = client.get("/api/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["kpis"]["total_emails"] >= 1
    assert stats["kpis"]["total_companies"] >= 1


def test_export_endpoints(client):
    # Test CSV export
    res_csv = client.get("/api/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "Company" in res_csv.text

    # Test Excel export
    res_xlsx = client.get("/api/export?format=xlsx")
    assert res_xlsx.status_code == 200
    assert len(res_xlsx.content) > 100
