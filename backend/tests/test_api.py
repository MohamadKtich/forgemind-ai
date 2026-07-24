from io import BytesIO
from PIL import Image, ImageDraw


def test_health_and_auth(client, manager_headers):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["version"] == "3.0.0"
    me = client.get("/api/auth/me", headers=manager_headers)
    assert me.status_code == 200
    assert me.json()["role"] == "factory_manager"


def test_dashboard_and_predictive(client, manager_headers):
    dashboard = client.get("/api/dashboard", headers=manager_headers)
    assert dashboard.status_code == 200, dashboard.text
    data = dashboard.json()
    assert data["kpis"]["total_machines"] >= 7
    assert data["kpis"]["production_count"] > 0
    latest = client.get("/api/predictive/latest", headers=manager_headers)
    assert latest.status_code == 200
    assert len(latest.json()) >= 7
    assert "remaining_useful_hours" in latest.json()[0]["prediction"]


def test_machine_crud_and_maintenance(client, manager_headers):
    created = client.post("/api/machines", headers=manager_headers, json={
        "factory_id":1,"code":"T-900","name":"Test Asset","machine_type":"Test Rig",
        "manufacturer":"ForgeMind","model_number":"QA-1","line_name":"Test Line",
        "age_years":1,"operating_hours":10,"tool_wear":5,"rated_power_kw":4,
    })
    assert created.status_code == 201, created.text
    machine_id = created.json()["id"]
    updated = client.patch(f"/api/machines/{machine_id}", headers=manager_headers, json={"status":"maintenance","notes":"Integration tested"})
    assert updated.status_code == 200
    task = client.post(f"/api/machines/{machine_id}/maintenance", headers=manager_headers, json={
        "title":"Test inspection","action":"Verify test rig","priority":"medium","assigned_to":"QA"
    })
    assert task.status_code == 201, task.text
    completed = client.patch(f"/api/maintenance/{task.json()['id']}", headers=manager_headers, json={"status":"completed"})
    assert completed.status_code == 200
    archived = client.delete(f"/api/machines/{machine_id}", headers=manager_headers)
    assert archived.status_code == 200


def test_hardware_ingestion_and_device_command(client, manager_headers):
    payload = {"machine_id":"M-001","temperature":87.5,"vibration":1.05,"pressure":31.2,"rpm":1370,"torque":61,"power":22.4,"source":"pytest"}
    unauthorized = client.post("/api/hardware/readings", json=payload)
    assert unauthorized.status_code == 401
    reading = client.post("/api/hardware/readings", headers={"X-Device-Key":"forgemind-local-device-key"}, json=payload)
    assert reading.status_code == 200, reading.text
    assert 0 <= reading.json()["failure_probability"] <= 1
    command = client.post("/api/device/commands", headers=manager_headers, json={"machine_id":"M-001","command":"request_inspection","payload":{}})
    assert command.status_code == 201
    assert command.json()["accepted"] is True


def test_quality_inspection_with_reference(client, manager_headers):
    good = Image.new("RGB", (420, 320), (88, 96, 104))
    draw = ImageDraw.Draw(good)
    draw.rounded_rectangle((70, 55, 350, 265), radius=18, fill=(142, 148, 151), outline=(185, 190, 192), width=5)
    defective = good.copy()
    d = ImageDraw.Draw(defective)
    d.line((145, 120, 290, 190), fill=(22, 22, 22), width=13)
    d.ellipse((245, 105, 285, 145), fill=(65, 40, 35))
    good_buf, defective_buf = BytesIO(), BytesIO()
    good.save(good_buf, format="PNG")
    defective.save(defective_buf, format="PNG")
    response = client.post(
        "/api/quality/inspect",
        headers=manager_headers,
        data={"product_name":"Test Housing","batch_code":"QA-001","machine_id":"1"},
        files={
            "file":("defective.png", defective_buf.getvalue(), "image/png"),
            "reference":("reference.png", good_buf.getvalue(), "image/png"),
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["inspection_mode"] == "reference_comparison"
    assert result["status"] in {"good", "defective"}
    assert result["annotated_url"].startswith("/api/quality/images/")


def test_simulation_assistant_alerts_and_reports(client, manager_headers):
    assert client.post("/api/simulation/start", headers=manager_headers).status_code == 200
    tick = client.post("/api/simulation/tick", headers=manager_headers)
    assert tick.status_code == 200, tick.text
    assert tick.json()["updated"] >= 7
    assistant = client.post("/api/assistant/query", headers=manager_headers, json={"question":"Which machine needs maintenance first?"})
    assert assistant.status_code == 200
    assert assistant.json()["conversation_id"] > 0
    alerts = client.get("/api/alerts", headers=manager_headers)
    assert alerts.status_code == 200
    report = client.post("/api/reports/generate", headers=manager_headers, json={"report_type":"executive"})
    assert report.status_code == 201, report.text
    download = client.get(report.json()["download_url"], headers=manager_headers)
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/pdf")
    csv = client.get("/api/reports/production.csv", headers=manager_headers)
    assert csv.status_code == 200
    assert "recorded_at" in csv.text


def test_admin_users_settings_and_logs(client, admin_headers):
    users = client.get("/api/admin/users", headers=admin_headers)
    assert users.status_code == 200
    assert len(users.json()) >= 4
    settings = client.get("/api/admin/settings", headers=admin_headers)
    assert settings.status_code == 200
    update = client.put("/api/admin/settings/test_setting", headers=admin_headers, json={"value":{"enabled":True},"description":"Test"})
    assert update.status_code == 200
    logs = client.get("/api/admin/logs", headers=admin_headers)
    assert logs.status_code == 200
    assert len(logs.json()) > 0


def test_profile_password_recovery_and_factory_admin(client, manager_headers, admin_headers):
    profile = client.patch("/api/auth/profile", headers=manager_headers, json={"full_name":"Operations Manager Updated"})
    assert profile.status_code == 200
    assert profile.json()["full_name"] == "Operations Manager Updated"
    change = client.post("/api/auth/change-password", headers=manager_headers, json={"current_password":"ForgeMind#2026","new_password":"ForgeMind#2027"})
    assert change.status_code == 200
    login = client.post("/api/auth/login", json={"email":"manager@forgemind.ai","password":"ForgeMind#2027"})
    assert login.status_code == 200
    recover = client.post("/api/auth/recover-local", json={"email":"manager@forgemind.ai","recovery_key":"ForgeMind-Recovery-2026","new_password":"ForgeMind#2026"})
    assert recover.status_code == 200
    factory = client.post("/api/factories", headers=admin_headers, json={"name":"QA Plant","location":"RAK","timezone":"Asia/Dubai","target_oee":88})
    assert factory.status_code == 201, factory.text
    factory_id = factory.json()["id"]
    updated = client.patch(f"/api/factories/{factory_id}", headers=admin_headers, json={"target_oee":90})
    assert updated.status_code == 200
    deleted = client.delete(f"/api/factories/{factory_id}", headers=admin_headers)
    assert deleted.status_code == 200


def test_model_registry_and_arabic_assistant(client, manager_headers):
    status = client.get("/api/models/status", headers=manager_headers)
    assert status.status_code == 200
    payload = status.json()
    assert "predictive" in payload and "quality" in payload
    response = client.post("/api/assistant/query", headers=manager_headers, json={"question": "لخص الإنتاج الحالي", "locale": "ar"})
    assert response.status_code == 200
    assert response.json()["evidence"]["response_locale"] == "ar"
    assert any(ch >= "\u0600" and ch <= "\u06ff" for ch in response.json()["answer"])
