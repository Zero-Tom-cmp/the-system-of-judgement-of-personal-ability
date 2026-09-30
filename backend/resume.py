# -*- coding: utf-8 -*-
"""
简历生成模块

内容转换原则（与需求一致）：
- 教育背景：GPA + 专业排名 + 4-6 门核心课程（学科基础/专业必修优先）
- 实习/项目：描述按句拆分 2-4 条要点，不虚构内容
- 竞赛：统一单行格式「名称 | 级别 | 奖项 | 排名 | 时间」
- 技能：能力分数不展示数字，仅输出达到阈值的维度名 + 从真实描述中
  提取的技术关键词；缺数据的位置输出空列表，由模板渲染占位符

版式：resume-templates/01-minimal.tpl.html（用户确认的「极简单栏」），
渲染 HTML 后用 Edge headless（Chromium 内核，等价于 Playwright/Puppeteer）
打印为 A4 PDF，文字可选、字体嵌入。
"""
import html
import os
import re
import subprocess
import sys

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BACKEND_DIR, "..", "resume-templates", "01-minimal.tpl.html")

CORE_COURSE_NATURES = ("学科基础", "专业必修")
CORE_COURSE_LIMIT = 6
CORE_COURSE_MIN = 4
ABILITY_TAG_THRESHOLD = 40
ABILITY_TAG_LIMIT = 4
KEYWORD_LIMIT = 10

# 技术关键词字典：仅当原文出现关键字时才生成标签（不做任何推断）
TECH_KEYWORD_RULES = [
    ("Spring Boot", "Spring Boot"), ("SpringBoot", "Spring Boot"),
    ("MyBatis", "MyBatis"), ("FastAPI", "FastAPI"), ("Django", "Django"),
    ("Flask", "Flask"), ("Node", "Node.js"), ("React", "React"), ("Vue", "Vue"),
    ("小程序", "微信小程序"), ("MySQL", "MySQL"), ("Redis", "Redis"),
    ("MongoDB", "MongoDB"), ("Docker", "Docker"), ("Kubernetes", "Kubernetes"),
    ("Linux", "Linux"), ("Hadoop", "Hadoop"), ("Spark", "Spark"),
    ("协同过滤", "推荐算法"), ("机器学习", "机器学习"), ("深度学习", "深度学习"),
    ("数据可视化", "数据可视化"), ("数据挖掘", "数据挖掘"), ("爬虫", "网络爬虫"),
    ("Web前端", "前端开发"), ("全栈", "全栈开发"),
]

POSITION_KEYWORD_RULES = [
    ("后端", "后端开发"), ("前端", "前端开发"), ("算法", "算法工程"),
    ("测试", "软件测试"), ("运维", "运维开发"), ("全栈", "全栈开发"),
    ("数据分析", "数据分析"), ("研究", "行业研究"), ("风险", "风险管理"),
    ("信贷", "信贷分析"), ("金融", "金融业务"),
]

COMPETITION_KEYWORD_RULES = [
    ("ACM", "算法竞赛"), ("程序设计", "算法竞赛"), ("数学建模", "数学建模"),
    ("英语", "英语能力"), ("创新创业", "创新创业"), ("挑战杯", "创新创业"),
]


def _normalize_period(text: str) -> str:
    """'2023-07 —2023-09' → '2023.07 — 2023.09'"""
    if not text:
        return ""
    s = re.sub(r"(\d{4})-(\d{1,2})", r"\1.\2", str(text).strip())
    return re.sub(r"\s*[—–~-]+\s*", " — ", s)


def _normalize_date(text: str) -> str:
    """'2023-05' → '2023.05'"""
    if not text:
        return ""
    return re.sub(r"(\d{4})-(\d{1,2})", r"\1.\2", str(text).strip())


def split_bullets(text: str, max_bullets: int = 4) -> list:
    """把一段描述拆成 1-4 条要点：先按句号/分号断句，过长句子再按逗号细分"""
    if not text:
        return []
    t = re.sub(r"\s+", " ", str(text).strip())
    if not t:
        return []

    bullets = []
    for seg in re.split(r"[。；;!？?\n]+", t):
        seg = seg.strip(" ，,、\t")
        if not seg:
            continue
        if len(seg) > 40 and "，" in seg:
            buf = ""
            for part in seg.split("，"):
                part = part.strip(" ，,、\t")
                if not part:
                    continue
                if buf and len(buf) + len(part) <= 34:
                    buf = f"{buf}，{part}"
                else:
                    if buf:
                        bullets.append(buf)
                    buf = part
            if buf:
                bullets.append(buf)
        else:
            bullets.append(seg)
    return bullets[:max_bullets]


def _rank_in_major(cursor, student: dict) -> tuple:
    """专业内 GPA 排名（并列取最优名次）"""
    total = cursor.execute(
        "SELECT COUNT(*) AS c FROM students WHERE role = 'student' AND major = ?",
        (student["major"],),
    ).fetchone()["c"]
    ahead = cursor.execute(
        "SELECT COUNT(*) AS c FROM students WHERE role = 'student' AND major = ? AND gpa > ?",
        (student["major"], student["gpa"]),
    ).fetchone()["c"]
    return ahead + 1, total


def _core_courses(cursor, student_id: str) -> list:
    rows = cursor.execute(
        "SELECT course_name, score, course_nature FROM courses WHERE student_id = ? "
        "AND course_nature IN (?, ?) ORDER BY score DESC LIMIT ?",
        (student_id, CORE_COURSE_NATURES[0], CORE_COURSE_NATURES[1], CORE_COURSE_LIMIT),
    ).fetchall()
    picked = [dict(r) for r in rows]
    if len(picked) < CORE_COURSE_MIN:
        more = cursor.execute(
            "SELECT course_name, score, course_nature FROM courses WHERE student_id = ? "
            "AND course_nature NOT IN (?, ?) ORDER BY score DESC LIMIT ?",
            (student_id, CORE_COURSE_NATURES[0], CORE_COURSE_NATURES[1], CORE_COURSE_MIN - len(picked)),
        ).fetchall()
        picked.extend(dict(r) for r in more)
    return picked


def _skill_tags(cursor, student_id: str, student: dict) -> dict:
    """能力标签（不含分数）+ 真实文本中提取的技术关键词"""
    abilities = []
    try:
        from evaluation import evaluate_student_abilities
        result = evaluate_student_abilities(cursor, student_id)
        ranked = sorted(result["abilities"].items(), key=lambda x: x[1]["score"], reverse=True)
        abilities = [name for name, info in ranked if info["score"] >= ABILITY_TAG_THRESHOLD][:ABILITY_TAG_LIMIT]
    except Exception:
        abilities = []

    keywords = []

    def add(kw):
        if kw and kw not in keywords and len(keywords) < KEYWORD_LIMIT:
            keywords.append(kw)

    def scan(text, rules):
        text = text or ""
        for needle, tag in rules:
            if needle in text:
                add(tag)

    for r in cursor.execute(
        "SELECT company, position, description FROM internships WHERE student_id = ?",
        (student_id,),
    ):
        scan(r["position"], POSITION_KEYWORD_RULES)
        scan(r["description"], TECH_KEYWORD_RULES)

    for r in cursor.execute(
        "SELECT project_name, description FROM projects WHERE student_id = ?",
        (student_id,),
    ):
        scan(r["description"], TECH_KEYWORD_RULES)
        scan(r["project_name"], TECH_KEYWORD_RULES)

    course_names = cursor.execute(
        "SELECT course_name FROM courses WHERE student_id = ?", (student_id,)
    ).fetchall()
    for r in course_names:
        scan(r["course_name"], TECH_KEYWORD_RULES)

    for r in cursor.execute(
        "SELECT comp_name FROM competitions WHERE student_id = ?", (student_id,)
    ):
        scan(r["comp_name"], COMPETITION_KEYWORD_RULES)

    return {"abilities": abilities, "keywords": keywords}


def build_resume_payload(cursor, student_id: str) -> dict:
    """把数据库原始数据转换为简历结构化数据（前端与 PDF 共用）"""
    student = cursor.execute(
        "SELECT student_id, name, college, major, class_name, gpa FROM students WHERE student_id = ?",
        (student_id,),
    ).fetchone()
    if not student:
        raise ValueError(f"学生 {student_id} 不存在")
    student = dict(student)

    rank, rank_total = _rank_in_major(cursor, student)

    total_courses = cursor.execute(
        "SELECT COUNT(*) AS c FROM courses WHERE student_id = ?", (student_id,)
    ).fetchone()["c"]
    total_credits = cursor.execute(
        "SELECT SUM(credit) AS s FROM courses WHERE student_id = ?", (student_id,)
    ).fetchone()["s"] or 0

    internships = [
        {
            "company": r["company"], "position": r["position"],
            "period": _normalize_period(r["period"]),
            "bullets": split_bullets(r["description"]),
        }
        for r in cursor.execute(
            "SELECT company, position, description, period FROM internships "
            "WHERE student_id = ? ORDER BY period DESC",
            (student_id,),
        )
    ]

    projects = [
        {
            "project_name": r["project_name"], "rank": r["rank"],
            "period": _normalize_period(r["period"]),
            "bullets": split_bullets(r["description"]),
        }
        for r in cursor.execute(
            "SELECT project_name, rank, description, period FROM projects "
            "WHERE student_id = ? ORDER BY period DESC",
            (student_id,),
        )
    ]

    competitions = [
        {
            "comp_name": r["comp_name"], "level": r["level"], "award": r["award"],
            "rank": r["rank"], "date": _normalize_date(r["date"]),
        }
        for r in cursor.execute(
            "SELECT comp_name, level, award, rank, date FROM competitions "
            "WHERE student_id = ? ORDER BY date DESC",
            (student_id,),
        )
    ]

    grade_year = student["student_id"][:4] if re.match(r"^20\d{2}", student["student_id"]) else ""

    return {
        "basic": {
            **student,
            "total_courses": total_courses,
            "total_credits": round(total_credits, 1),
            "grade_year": grade_year,
        },
        "education": {
            "rank": rank,
            "rank_total": rank_total,
            "core_courses": _core_courses(cursor, student_id),
        },
        "skills": _skill_tags(cursor, student_id, student),
        "internships": internships,
        "projects": projects,
        "competitions": competitions,
    }


# ================= HTML 渲染（模板一 · 极简单栏） =================

def _e(text) -> str:
    return html.escape(str(text)) if text is not None else ""


def _fmt_num(value) -> str:
    """96.0 → 96；3.82 → 3.82"""
    try:
        f = float(value)
        return str(int(f)) if f == int(f) else str(f)
    except (TypeError, ValueError):
        return _e(value)


def _bullets_html(bullets: list) -> str:
    if not bullets:
        return '<div class="empty-hint">（暂无描述，请在系统中补充）</div>'
    items = "".join(f"<li>{_e(b)}</li>" for b in bullets)
    return f'<ul class="bullets">{items}</ul>'


def _education_html(p: dict) -> str:
    b, ed = p["basic"], p["education"]
    date_text = f"{b['grade_year']} 级 · 在读" if b["grade_year"] else "在读"
    rank_text = f"专业排名 {ed['rank']} / {ed['rank_total']}" if ed["rank_total"] else "专业排名 —"
    meta = f"GPA {_fmt_num(b['gpa'])}（{rank_text}）· 已修 {b['total_courses']} 门课程 / {_fmt_num(b['total_credits'])} 学分"
    if ed["core_courses"]:
        courses = " · ".join(f"{_e(c['course_name'])} {_fmt_num(c['score'])}" for c in ed["core_courses"])
        course_line = f'<div class="entry-sub">核心课程：{courses}</div>'
    else:
        course_line = '<div class="entry-sub empty-hint">核心课程：待补充</div>'
    return f"""<div class="entry">
      <div class="entry-head">
        <span><span class="entry-title">{_e(b['college'])} · {_e(b['major'])}</span><span class="entry-role">本科在读</span></span>
        <span class="entry-date">{_e(date_text)}</span>
      </div>
      <div class="entry-sub">{meta}</div>
      {course_line}
    </div>"""


def _skills_html(p: dict) -> str:
    sk = p["skills"]
    rows = ""
    if sk["abilities"]:
        rows += f'<div class="skill-group"><span class="skill-label">核心能力</span><span class="skill-content">{" / ".join(_e(a) for a in sk["abilities"])}</span></div>'
    if sk["keywords"]:
        rows += f'<div class="skill-group"><span class="skill-label">技术关键词</span><span class="skill-content">{" / ".join(_e(k) for k in sk["keywords"])}</span></div>'
    if not rows:
        rows = '<div class="empty-hint">（暂无技能数据，完成课程、竞赛或项目录入后自动生成）</div>'
    return rows


def _internships_html(p: dict) -> str:
    if not p["internships"]:
        return '<div class="empty-hint">（暂无实习经历）</div>'
    parts = []
    for it in p["internships"]:
        parts.append(f"""<div class="entry">
      <div class="entry-head">
        <span><span class="entry-title">{_e(it['company'])}</span><span class="entry-role">{_e(it['position'])}</span></span>
        <span class="entry-date">{_e(it['period'])}</span>
      </div>
      {_bullets_html(it['bullets'])}
    </div>""")
    return "\n    ".join(parts)


def _projects_html(p: dict) -> str:
    if not p["projects"]:
        return '<div class="empty-hint">（暂无项目经历）</div>'
    parts = []
    for it in p["projects"]:
        role = f"队内排名第 {_e(it['rank'])}"
        parts.append(f"""<div class="entry">
      <div class="entry-head">
        <span><span class="entry-title">{_e(it['project_name'])}</span><span class="entry-role">{role}</span></span>
        <span class="entry-date">{_e(it['period'])}</span>
      </div>
      {_bullets_html(it['bullets'])}
    </div>""")
    return "\n    ".join(parts)


def _competitions_html(p: dict) -> str:
    if not p["competitions"]:
        return '<div class="empty-hint">（暂无竞赛获奖）</div>'
    parts = []
    for c in p["competitions"]:
        meta_bits = [c["level"], c["award"], f"队内排名第 {c['rank']}"]
        if c["date"]:
            meta_bits.append(c["date"])
        meta = " · ".join(_e(x) for x in meta_bits if x)
        parts.append(
            f'<div class="comp"><span class="comp-name">{_e(c["comp_name"])}</span>'
            f'<span class="comp-meta">{meta}</span></div>'
        )
    return "\n    ".join(parts)


def render_resume_html(payload: dict, generated_at: str = "") -> str:
    """用模板一（极简单栏）渲染独立 HTML"""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        tpl = f.read()

    b = payload["basic"]
    contact_html = '<span class="ph">联系方式待完善（电话 / 邮箱 / GitHub）</span>'
    footer = "本简历由人岗匹配评估系统自动生成"
    if generated_at:
        footer += f" · {_e(generated_at)}"

    return (
        tpl.replace("{{NAME}}", _e(b["name"]))
           .replace("{{TAGLINE}}", _e(f"{b['major']} · 本科在读"))
           .replace("{{CONTACT_HTML}}", contact_html)
           .replace("{{EDUCATION_HTML}}", _education_html(payload))
           .replace("{{SKILLS_HTML}}", _skills_html(payload))
           .replace("{{INTERNSHIPS_HTML}}", _internships_html(payload))
           .replace("{{PROJECTS_HTML}}", _projects_html(payload))
           .replace("{{COMPETITIONS_HTML}}", _competitions_html(payload))
           .replace("{{FOOTER_NOTE}}", footer)
    )


def _find_edge() -> str:
    candidates = [
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                     "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    import shutil as _shutil
    found = _shutil.which("msedge") or _shutil.which("msedge.exe")
    if found:
        return found
    raise RuntimeError("未找到 Edge 浏览器，无法渲染 PDF（需安装 Microsoft Edge）")


def render_pdf(html_text: str, out_dir: str, basename: str) -> str:
    """用 Edge headless 把 HTML 打印成 A4 PDF，返回 PDF 路径"""
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, f"{basename}.html")
    pdf_path = os.path.join(out_dir, f"{basename}.pdf")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_text)

    edge = _find_edge()
    cmd = [
        edge,
        "--headless",
        "--disable-gpu",
        "--no-first-run",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        "file:///" + html_path.replace("\\", "/").lstrip("/"),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=90)
    except subprocess.TimeoutExpired:
        raise RuntimeError("PDF 渲染超时")
    if proc.returncode != 0 or not os.path.isfile(pdf_path):
        detail = (proc.stderr or b"").decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"PDF 渲染失败: {detail}")
    return pdf_path
