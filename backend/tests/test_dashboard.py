def test_dashboard_router_registers_authenticated_endpoint():
    from app.main import app

    assert "/api/v1/dashboard" in app.openapi()["paths"]
