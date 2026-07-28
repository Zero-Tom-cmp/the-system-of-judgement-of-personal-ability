import json
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import get_db, init_db
from evaluation import evaluate_student_abilities, match_jobs

app = FastAPI(title="人岗匹配评估系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "person-job-match-secret-key-demo"
ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    username: str
    password: str


def create_token(student_id: str, role: str) -> str:
    payload = {
        "student_id": student_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="无效的认证令牌")


def require_admin(payload: dict):
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")


@app.on_event("startup")
def startup():
    init_db()


@app.post("/api/login")
def login(req: LoginRequest):
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT * FROM students WHERE student_id = ?", (req.username,)
        ).fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not bcrypt.checkpw(req.password.encode(), user["password_hash"].encode()):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        token = create_token(user["student_id"], user["role"])
        return {
            "token": token,
            "student_id": user["student_id"],
            "name": user["name"],
            "role": user["role"],
            "major": user["major"],
        }
    finally:
        conn.close()


@app.get("/api/student/{student_id}/info")
def get_student_info(student_id: str, request: Request):
    payload = verify_token(request.headers.get("Authorization", "").replace("Bearer ", ""))
    if payload["role"] != "admin" and payload["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="只能查看自己的信息")

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT student_id, name, college, major, class_name, gpa, role FROM students WHERE student_id = ?",
            (student_id,),
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="学生不存在")
        return dict(user)
    finally:
        conn.close()


@app.get("/api/student/{student_id}/courses")
def get_student_courses(student_id: str, request: Request):
    payload = verify_token(request.headers.get("Authorization", "").replace("Bearer ", ""))
    if payload["role"] != "admin" and payload["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="只能查看自己的信息")

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM courses WHERE student_id = ? ORDER BY semester",
            (student_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/student/{student_id}/competitions")
def get_student_competitions(student_id: str, request: Request):
    payload = verify_token(request.headers.get("Authorization", "").replace("Bearer ", ""))
    if payload["role"] != "admin" and payload["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="只能查看自己的信息")

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM competitions WHERE student_id = ? ORDER BY date DESC",
            (student_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/student/{student_id}/internships")
def get_student_internships(student_id: str, request: Request):
    payload = verify_token(request.headers.get("Authorization", "").replace("Bearer ", ""))
    if payload["role"] != "admin" and payload["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="只能查看自己的信息")

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM internships WHERE student_id = ? ORDER BY date DESC",
            (student_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/student/{student_id}/projects")
def get_student_projects(student_id: str, request: Request):
    payload = verify_token(request.headers.get("Authorization", "").replace("Bearer ", ""))
    if payload["role"] != "admin" and payload["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="只能查看自己的信息")

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM projects WHERE student_id = ? ORDER BY date DESC",
            (student_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/student/{student_id}/abilities")
def get_student_abilities(student_id: str, request: Request):
    payload = verify_token(request.headers.get("Authorization", "").replace("Bearer ", ""))
    if payload["role"] != "admin" and payload["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="只能查看自己的信息")

    conn = get_db()
    try:
        return evaluate_student_abilities(conn.cursor(), student_id)
    finally:
        conn.close()


@app.get("/api/student/{student_id}/job-match")
def get_job_match(student_id: str, request: Request):
    payload = verify_token(request.headers.get("Authorization", "").replace("Bearer ", ""))
    if payload["role"] != "admin" and payload["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="只能查看自己的信息")

    conn = get_db()
    try:
        return match_jobs(conn.cursor(), student_id)
    finally:
        conn.close()


@app.get("/api/admin/students")
def admin_list_students(request: Request):
    payload = verify_token(request.headers.get("Authorization", "").replace("Bearer ", ""))
    require_admin(payload)

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT student_id, name, college, major, class_name, gpa FROM students WHERE role = 'student' ORDER BY student_id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/admin/search")
def admin_search(q: str, request: Request):
    payload = verify_token(request.headers.get("Authorization", "").replace("Bearer ", ""))
    require_admin(payload)

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT student_id, name, college, major, class_name, gpa FROM students WHERE role = 'student' AND (student_id LIKE ? OR name LIKE ?)",
            (f"%{q}%", f"%{q}%"),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
