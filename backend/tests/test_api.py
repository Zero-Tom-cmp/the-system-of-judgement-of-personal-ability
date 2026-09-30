"""基础 API 测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from main import app, _login_attempts

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_login_rate_limit():
    """登录限流是"5 分钟 20 次"，整个套件的登录次数会撞上它，
    表现为 _login 拿不到 token（429）。每个用例前清空计数。

    只动测试进程里的内存计数器，不影响生产行为。"""
    _login_attempts.clear()
    yield
    _login_attempts.clear()


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


def _login(student_id="2021001", password="student123"):
    resp = client.post("/api/login", json={"username": student_id, "password": password})
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def test_resume_content_transformation():
    """简历结构：核心课程 4-6 门、专业排名、技能不含分数、竞赛单行格式"""
    headers = _login()
    resp = client.get("/api/student/2021001/resume", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["basic"]["name"] == "张三"
    ed = data["education"]
    assert 4 <= len(ed["core_courses"]) <= 6
    assert ed["rank"] == 1 and ed["rank_total"] == 3
    assert all(c["course_nature"] in ("学科基础", "专业必修") for c in ed["core_courses"])

    # 技能输出为标签，不出现能力分数
    assert all(isinstance(a, str) for a in data["skills"]["abilities"])
    assert "score" not in str(data["skills"]["abilities"])
    assert "Spring Boot" in data["skills"]["keywords"]

    # 描述拆分为要点，时间格式统一
    assert data["internships"][0]["bullets"]
    assert data["internships"][0]["period"] == "2023.07 — 2023.09"
    assert data["competitions"][0]["date"] == "2023.05"
    assert all("。" not in b for it in data["projects"] for b in it["bullets"])


def test_resume_pdf_download():
    headers = _login()
    resp = client.get("/api/student/2021001/resume/pdf", headers=headers)
    if resp.status_code == 500 and "Edge" in resp.json().get("detail", ""):
        import pytest
        pytest.skip("未安装 Edge，跳过 PDF 渲染测试")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"
    assert len(resp.content) > 50_000  # 含嵌入字体


def test_resume_no_cross_access():
    headers = _login("2021001")
    resp = client.get("/api/student/2021002/resume", headers=headers)
    assert resp.status_code == 403


# --- 英语证书录入（换算标准见 evaluation.ENGLISH_CERT_LEVELS）-------------
#
# 注意：test_api.py 用的是真实库，凡写入的用例都必须还原原值。


def test_student_info_exposes_english_cert_fields():
    resp = client.get("/api/student/2021004/info", headers=_login("2021004"))
    assert resp.status_code == 200
    body = resp.json()
    assert "english_cert" in body
    assert "english_score" in body


def test_admin_rejects_unknown_cert_type():
    resp = client.put("/api/admin/student/2021004",
                      json={"english_cert": "GRE", "english_score": 320},
                      headers=_login("admin", "admin123"))
    assert resp.status_code == 400
    assert "GRE" in resp.json()["detail"]


def test_admin_rejects_out_of_range_score():
    # 六级满分 710
    resp = client.put("/api/admin/student/2021004",
                      json={"english_cert": "CET6", "english_score": 800},
                      headers=_login("admin", "admin123"))
    assert resp.status_code == 400


def test_admin_rejects_score_below_minimum():
    # 四级最低档 425，424 连最低档都够不上，属于无效录入
    resp = client.put("/api/admin/student/2021004",
                      json={"english_cert": "CET4", "english_score": 424},
                      headers=_login("admin", "admin123"))
    assert resp.status_code == 400


def test_admin_rejects_cert_without_score():
    resp = client.put("/api/admin/student/2021004",
                      json={"english_cert": "CET6"},
                      headers=_login("admin", "admin123"))
    assert resp.status_code == 400


def test_admin_can_set_and_clear_english_cert():
    admin = _login("admin", "admin123")
    before = client.get("/api/student/2021004/info", headers=_login("2021004")).json()
    original = {"english_cert": before["english_cert"], "english_score": before["english_score"]}
    try:
        resp = client.put("/api/admin/student/2021004",
                          json={"english_cert": "CET6", "english_score": 530}, headers=admin)
        assert resp.status_code == 200
        after = client.get("/api/student/2021004/info", headers=_login("2021004")).json()
        assert after["english_cert"] == "CET6"
        assert after["english_score"] == 530

        # 传空字符串表示清空证书，分数一并置空
        resp = client.put("/api/admin/student/2021004",
                          json={"english_cert": ""}, headers=admin)
        assert resp.status_code == 200
        cleared = client.get("/api/student/2021004/info", headers=_login("2021004")).json()
        assert cleared["english_cert"] is None
        assert cleared["english_score"] is None
    finally:
        # 原来就为空时，"传 null"等于"不修改"，清不回去，得用空字符串
        restore = ({"english_cert": ""} if original["english_cert"] is None else original)
        client.put("/api/admin/student/2021004", json=restore, headers=admin)


def test_admin_can_clear_an_existing_cert():
    """清掉一个本来就存在的证书。

    和上一个用例的区别:那个学生原本没证书,所以走的是"空对空";这里有旧成绩,
    实现里若把库里的旧成绩带进来,就会拼出"有成绩没证书"的非法状态而被 400 挡掉。
    """
    sid = "2021004"                                     # 赵六,IELTS 6.5
    admin = _login("admin", "admin123")
    before = client.get(f"/api/student/{sid}/info", headers=admin).json()
    original = {"english_cert": before["english_cert"], "english_score": before["english_score"]}
    try:
        resp = client.put(f"/api/admin/student/{sid}", json={"english_cert": ""}, headers=admin)
        assert resp.status_code == 200, resp.json()
        after = client.get(f"/api/student/{sid}/info", headers=admin).json()
        assert after["english_cert"] is None
        assert after["english_score"] is None
    finally:
        client.put(f"/api/admin/student/{sid}", json=original, headers=admin)


def test_admin_list_exposes_cert_fields():
    """编辑弹窗靠列表接口回填证书,列表漏了这两列,弹窗就会把有证书的学生显示成空白。"""
    admin = _login("admin", "admin123")
    rows = client.get("/api/admin/students?page_size=100", headers=admin).json()["data"]
    zhao = next(r for r in rows if r["student_id"] == "2021004")
    assert zhao["english_cert"] == "IELTS"
    assert zhao["english_score"] == 6.5


def test_admin_can_create_student_with_cert():
    sid = "9000006"
    admin = _login("admin", "admin123")
    try:
        resp = client.post("/api/admin/student", json={
            "student_id": sid, "name": "导入测试己", "college": "经济管理学院",
            "major": "金融学", "class_name": "金融2109", "gpa": 3.2,
            "password": "student123", "english_cert": "cet6", "english_score": 520,
        }, headers=admin)
        assert resp.status_code == 200, resp.json()
        info = client.get(f"/api/student/{sid}/info", headers=admin).json()
        assert info["english_cert"] == "CET6"           # 小写转大写,与导入一致
        assert info["english_score"] == 520
    finally:
        _cleanup_students(sid)


def test_admin_create_rejects_score_without_cert():
    """只给分数不给证书是无效录入,不能静默丢进库里。"""
    sid = "9000007"
    admin = _login("admin", "admin123")
    try:
        resp = client.post("/api/admin/student", json={
            "student_id": sid, "name": "导入测试庚", "college": "经济管理学院",
            "major": "金融学", "class_name": "金融2109", "gpa": 3.2,
            "password": "student123", "english_score": 520,
        }, headers=admin)
        assert resp.status_code == 400
    finally:
        _cleanup_students(sid)      # 万一断言失败真的建出来了，也要清掉


# --- Excel 导入：英语证书是可选列 -----------------------------------------

STUDENT_SHEET = "学生基本信息"
_BASE_HEADER = ["学号", "姓名", "学院", "专业", "班级", "GPA", "密码"]
_CERT_HEADER = _BASE_HEADER + ["英语证书", "英语成绩"]
_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _build_xlsx(rows, header=_BASE_HEADER):
    """把行数据打成 xlsx 字节流。"""
    import io as _io
    import openpyxl
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet(STUDENT_SHEET)
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = _io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _import_students(rows, header=_BASE_HEADER):
    admin = _login("admin", "admin123")
    return client.post(
        "/api/admin/import/all",
        files={"file": ("students.xlsx", _build_xlsx(rows, header), _XLSX_MIME)},
        headers=admin,
    )


def _student_row(sid, name, major="软件工程", cert=()):
    return [sid, name, "计算机学院", major, "测试班", 3.5, ""] + list(cert)


def _cleanup_students(*sids):
    admin = _login("admin", "admin123")
    for sid in sids:
        client.delete(f"/api/admin/student/{sid}", headers=admin)


def test_import_without_cert_columns_still_succeeds():
    """老模板没有英语证书两列，必须照常导入——可选列不能悄悄变成必填。"""
    sid = "9000001"
    try:
        resp = _import_students([_student_row(sid, "导入测试甲")])
        assert resp.status_code == 200
        assert resp.json()["results"][STUDENT_SHEET]["success"] == 1
    finally:
        _cleanup_students(sid)


def test_import_reads_optional_cert_columns():
    sid = "9000002"
    try:
        resp = _import_students([_student_row(sid, "导入测试乙", "金融学", ("ielts", 6.5))],
                                header=_CERT_HEADER)
        assert resp.status_code == 200
        assert resp.json()["results"][STUDENT_SHEET]["success"] == 1

        info = client.get(f"/api/student/{sid}/info", headers=_login("admin", "admin123")).json()
        assert info["english_cert"] == "IELTS"      # 导入时统一转大写
        assert info["english_score"] == 6.5
    finally:
        _cleanup_students(sid)


def test_import_rejects_bad_cert_but_keeps_other_rows():
    """证书填错只让该行报错，不能拖垮同批其他行。"""
    good, bad = "9000003", "9000004"
    try:
        resp = _import_students(
            [_student_row(good, "导入测试丙", cert=("CET6", 500)),
             _student_row(bad, "导入测试丁", cert=("GRE", 320))],
            header=_CERT_HEADER,
        )
        result = resp.json()["results"][STUDENT_SHEET]
        assert result["success"] == 1
        assert len(result["errors"]) == 1
        assert "GRE" in result["errors"][0]["reason"]
    finally:
        _cleanup_students(good, bad)


def test_import_without_cert_does_not_erase_existing_cert():
    """导入表里没写这两列时，已有证书必须保留（不能因为"没提供"而被清空）。"""
    sid = "9000005"
    admin = _login("admin", "admin123")
    try:
        _import_students([_student_row(sid, "导入测试戊", "金融学")])
        client.put(f"/api/admin/student/{sid}",
                   json={"english_cert": "CET6", "english_score": 500}, headers=admin)

        # 再导一次，不带证书列
        _import_students([_student_row(sid, "导入测试戊改", "金融学")])
        info = client.get(f"/api/student/{sid}/info", headers=admin).json()
        assert info["name"] == "导入测试戊改"
        assert info["english_cert"] == "CET6"
        assert info["english_score"] == 500
    finally:
        _cleanup_students(sid)
