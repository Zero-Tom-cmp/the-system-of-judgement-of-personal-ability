"""基础 API 测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_success():
    resp = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["role"] == "admin"


def test_login_wrong_password():
    resp = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_unauthorized_access():
    resp = client.get("/api/admin/students")
    assert resp.status_code == 401


def test_student_access_own_data():
    resp = client.post("/api/login", json={"username": "2021001", "password": "student123"})
    token = resp.json()["token"]
    resp2 = client.get("/api/student/2021001/info", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "张三"


def test_student_cannot_access_other():
    resp = client.post("/api/login", json={"username": "2021001", "password": "student123"})
    token = resp.json()["token"]
    resp2 = client.get("/api/student/2021002/info", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 403


def test_admin_can_list_students():
    resp = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    token = resp.json()["token"]
    resp2 = client.get("/api/admin/students", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json()["total"] >= 5


def test_abilities_endpoint():
    resp = client.post("/api/login", json={"username": "2021001", "password": "student123"})
    token = resp.json()["token"]
    resp2 = client.get("/api/student/2021001/abilities", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert "abilities" in resp2.json()
