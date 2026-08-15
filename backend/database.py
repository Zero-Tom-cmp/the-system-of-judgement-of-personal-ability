import sqlite3
import bcrypt

DB_PATH = "person_job_match.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(50) NOT NULL,
            college VARCHAR(100) NOT NULL,
            major VARCHAR(100) NOT NULL,
            class_name VARCHAR(50) NOT NULL,
            gpa REAL NOT NULL CHECK(gpa >= 0 AND gpa <= 5),
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'student' CHECK(role IN ('student','admin'))
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            course_name VARCHAR(100) NOT NULL,
            score REAL NOT NULL CHECK(score >= 0 AND score <= 100),
            credit REAL NOT NULL CHECK(credit > 0),
            practical_credit REAL DEFAULT 0 CHECK(practical_credit >= 0),
            semester VARCHAR(20) NOT NULL,
            course_nature VARCHAR(30) NOT NULL,
            UNIQUE(student_id, course_name)
        );

        CREATE TABLE IF NOT EXISTS training_plan (
            major VARCHAR(100) PRIMARY KEY,
            plan_data TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator VARCHAR(50) NOT NULL,
            action VARCHAR(20) NOT NULL,
            target_type VARCHAR(30) NOT NULL,
            target_id VARCHAR(50) NOT NULL,
            detail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS competitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            comp_name VARCHAR(200) NOT NULL,
            level VARCHAR(20) NOT NULL CHECK(level IN ('国家级','省级')),
            award VARCHAR(50) NOT NULL,
            rank INTEGER NOT NULL CHECK(rank > 0),
            date VARCHAR(20) NOT NULL,
            UNIQUE(student_id, comp_name)
        );

        CREATE TABLE IF NOT EXISTS internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            company VARCHAR(100) NOT NULL,
            position VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            period VARCHAR(30) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            project_name VARCHAR(200) NOT NULL,
            rank INTEGER NOT NULL CHECK(rank > 0),
            description TEXT NOT NULL,
            period VARCHAR(30) NOT NULL,
            UNIQUE(student_id, project_name)
        );

        CREATE TABLE IF NOT EXISTS ability_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            major VARCHAR(100) NOT NULL,
            ability_dimension VARCHAR(50) NOT NULL,
            weight REAL NOT NULL CHECK(weight >= 0 AND weight <= 1),
            UNIQUE(major, ability_dimension)
        );

        CREATE TABLE IF NOT EXISTS course_ability_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name VARCHAR(100) NOT NULL,
            ability_dimension VARCHAR(50) NOT NULL,
            contribution_weight REAL NOT NULL CHECK(contribution_weight >= 0)
        );

        CREATE TABLE IF NOT EXISTS job_ability_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name VARCHAR(100) NOT NULL,
            ability_dimension VARCHAR(50) NOT NULL,
            required_level REAL NOT NULL CHECK(required_level >= 0 AND required_level <= 100),
            importance_weight REAL NOT NULL CHECK(importance_weight >= 0 AND importance_weight <= 1)
        );

        CREATE INDEX IF NOT EXISTS idx_courses_sid ON courses(student_id);
        CREATE INDEX IF NOT EXISTS idx_competitions_sid ON competitions(student_id);
        CREATE INDEX IF NOT EXISTS idx_internships_sid ON internships(student_id);
        CREATE INDEX IF NOT EXISTS idx_projects_sid ON projects(student_id);
        CREATE INDEX IF NOT EXISTS idx_audit_log_time ON audit_log(created_at);
    """)

    # 仅在表为空时插入种子数据
    existing = cursor.execute("SELECT COUNT(*) as c FROM students").fetchone()
    if existing["c"] == 0:
        _seed_ability_config(cursor)
        _seed_course_mapping(cursor)
        _seed_training_plans(cursor)
        _seed_students(cursor)

    conn.commit()
    conn.close()


def _seed_ability_config(cursor):
    configs = [
        # 软件工程
        ("软件工程", "编程能力", 0.25),
        ("软件工程", "算法思维", 0.20),
        ("软件工程", "工程实践", 0.20),
        ("软件工程", "团队协作", 0.15),
        ("软件工程", "沟通表达", 0.10),
        ("软件工程", "学习能力", 0.10),
        # 金融学
        ("金融学", "数理分析", 0.25),
        ("金融学", "经济洞察", 0.20),
        ("金融学", "风险意识", 0.20),
        ("金融学", "沟通表达", 0.10),
        ("金融学", "财务技能", 0.15),
        ("金融学", "英语能力", 0.10),
    ]
    cursor.executemany(
        "INSERT INTO ability_config (major, ability_dimension, weight) VALUES (?, ?, ?)",
        configs,
    )


def _seed_course_mapping(cursor):
    mappings = [
        # 软件工程课程映射
        ("程序设计基础", "编程能力", 0.90),
        ("程序设计基础", "算法思维", 0.20),
        ("数据结构", "编程能力", 0.50),
        ("数据结构", "算法思维", 0.80),
        ("数据结构", "学习能力", 0.30),
        ("算法设计与分析", "算法思维", 0.95),
        ("算法设计与分析", "编程能力", 0.30),
        ("操作系统", "工程实践", 0.70),
        ("操作系统", "编程能力", 0.30),
        ("计算机网络", "工程实践", 0.60),
        ("计算机网络", "学习能力", 0.30),
        ("软件工程", "工程实践", 0.80),
        ("软件工程", "团队协作", 0.50),
        ("软件工程", "沟通表达", 0.40),
        ("数据库原理", "工程实践", 0.60),
        ("数据库原理", "编程能力", 0.40),
        ("高等数学A", "算法思维", 0.30),
        ("高等数学A", "学习能力", 0.50),
        ("线性代数", "算法思维", 0.40),
        ("线性代数", "学习能力", 0.40),
        ("大学英语", "沟通表达", 0.60),
        ("大学英语", "学习能力", 0.30),
        ("Web前端开发", "编程能力", 0.60),
        ("Web前端开发", "工程实践", 0.40),
        ("编译原理", "算法思维", 0.50),
        ("编译原理", "编程能力", 0.40),
        ("计算机组成原理", "工程实践", 0.40),
        ("计算机组成原理", "学习能力", 0.30),
        # 金融学课程映射
        ("微观经济学", "经济洞察", 0.80),
        ("微观经济学", "数理分析", 0.30),
        ("宏观经济学", "经济洞察", 0.80),
        ("宏观经济学", "数理分析", 0.30),
        ("计量经济学", "数理分析", 0.90),
        ("计量经济学", "经济洞察", 0.30),
        ("金融学原理", "财务技能", 0.80),
        ("金融学原理", "经济洞察", 0.40),
        ("风险管理", "风险意识", 0.90),
        ("风险管理", "财务技能", 0.30),
        ("投资学", "财务技能", 0.70),
        ("投资学", "风险意识", 0.50),
        ("投资学", "数理分析", 0.40),
        ("公司金融", "财务技能", 0.70),
        ("公司金融", "风险意识", 0.30),
        ("统计学", "数理分析", 0.70),
        ("统计学", "风险意识", 0.30),
        ("高等数学B", "数理分析", 0.60),
        ("高等数学B", "学习能力", 0.30),
        ("大学英语", "英语能力", 0.70),
        ("大学英语", "沟通表达", 0.30),
        ("金融英语", "英语能力", 0.80),
        ("金融英语", "财务技能", 0.20),
        ("国际金融", "英语能力", 0.50),
        ("国际金融", "经济洞察", 0.40),
    ]
    cursor.executemany(
        "INSERT INTO course_ability_mapping (course_name, ability_dimension, contribution_weight) VALUES (?, ?, ?)",
        mappings,
    )


def _seed_training_plans(cursor):
    import json

    se_plan = {
        "major": "软件工程",
        "basic_info": {
            "专业名称": "软件工程",
            "专业代码": "080902",
            "学制": "4年",
            "修业年限": "3—6年",
            "授予学位": "工学学士",
        },
        "objectives": "本专业培养适应社会主义现代化建设需要，德智体美劳全面发展，具备扎实的软件工程理论基础和工程实践能力，"
                      "掌握软件开发、项目管理、质量保证等核心技能，能够在IT企业、科研机构、政府部门从事软件系统分析、"
                      "设计、开发、测试、维护及项目管理等工作的高素质应用型人才。",
        "graduation_requirements": [
            {"id": "1", "title": "工程知识",
             "desc": "能够将数学、自然科学、工程基础和软件工程专业知识用于解决复杂软件工程问题。"},
            {"id": "2", "title": "问题分析",
             "desc": "能够应用数学、自然科学和工程科学的基本原理，识别、表达并通过文献研究分析复杂软件工程问题。"},
            {"id": "3", "title": "设计/开发解决方案",
             "desc": "能够设计针对复杂软件工程问题的解决方案，设计满足特定需求的软件系统，并体现创新意识。"},
            {"id": "4", "title": "研究",
             "desc": "能够基于科学原理并采用科学方法对复杂软件工程问题进行研究，包括设计实验、分析与解释数据。"},
            {"id": "5", "title": "使用现代工具",
             "desc": "能够针对复杂软件工程问题，开发、选择与使用恰当的技术、资源、现代工程工具和信息技术工具。"},
            {"id": "6", "title": "工程与社会",
             "desc": "能够基于工程相关背景知识进行合理分析，评价软件工程实践和复杂工程问题解决方案对社会的影响。"},
            {"id": "7", "title": "环境和可持续发展",
             "desc": "能够理解和评价针对复杂软件工程问题的工程实践对环境、社会可持续发展的影响。"},
            {"id": "8", "title": "职业规范",
             "desc": "具有人文社会科学素养、社会责任感，能够在工程实践中理解并遵守工程职业道德和规范。"},
            {"id": "9", "title": "个人和团队",
             "desc": "能够在多学科背景下的团队中承担个体、团队成员以及负责人的角色。"},
            {"id": "10", "title": "沟通",
             "desc": "能够就复杂工程问题与业界同行及社会公众进行有效沟通和交流，包括撰写报告和设计文稿、陈述发言。"},
            {"id": "11", "title": "项目管理",
             "desc": "理解并掌握工程管理原理与经济决策方法，并能在多学科环境中应用。"},
            {"id": "12", "title": "终身学习",
             "desc": "具有自主学习和终身学习的意识，有不断学习和适应发展的能力。"},
        ],
        "course_structure": {
            "categories": [
                {"name": "通识必修", "min_credits": 36, "color": "#1890ff"},
                {"name": "通识选修", "min_credits": 8, "color": "#52c41a"},
                {"name": "学科基础", "min_credits": 22, "color": "#fa8c16"},
                {"name": "专业必修", "min_credits": 28, "color": "#722ed1"},
                {"name": "专业选修", "min_credits": 12, "color": "#eb2f96"},
                {"name": "集中实践", "min_credits": 18, "color": "#13c2c2"},
                {"name": "创新创业", "min_credits": 4, "color": "#f5222d"},
                {"name": "美育劳动", "min_credits": 2, "color": "#faad14"},
            ],
            "total_min_credits": 130,
        },
        "ability_indicator_matrix": [
            {"indicator": "工程知识", "related_abilities": ["编程能力", "工程实践", "学习能力"], "level": "H"},
            {"indicator": "问题分析", "related_abilities": ["算法思维", "学习能力"], "level": "H"},
            {"indicator": "设计/开发解决方案", "related_abilities": ["编程能力", "工程实践", "算法思维"], "level": "H"},
            {"indicator": "研究", "related_abilities": ["算法思维", "学习能力"], "level": "M"},
            {"indicator": "使用现代工具", "related_abilities": ["工程实践", "编程能力"], "level": "H"},
            {"indicator": "工程与社会", "related_abilities": ["沟通表达", "团队协作"], "level": "M"},
            {"indicator": "环境和可持续发展", "related_abilities": ["沟通表达"], "level": "L"},
            {"indicator": "职业规范", "related_abilities": ["团队协作", "沟通表达"], "level": "M"},
            {"indicator": "个人和团队", "related_abilities": ["团队协作", "沟通表达"], "level": "H"},
            {"indicator": "沟通", "related_abilities": ["沟通表达", "团队协作"], "level": "H"},
            {"indicator": "项目管理", "related_abilities": ["工程实践", "团队协作"], "level": "M"},
            {"indicator": "终身学习", "related_abilities": ["学习能力"], "level": "H"},
        ],
        "course_requirement_matrix": [
            {"course": "程序设计基础", "reqs": {"工程知识": "H", "问题分析": "M", "设计/开发解决方案": "H", "使用现代工具": "H"}},
            {"course": "数据结构", "reqs": {"工程知识": "H", "问题分析": "H", "设计/开发解决方案": "H", "研究": "M"}},
            {"course": "算法设计与分析", "reqs": {"工程知识": "M", "问题分析": "H", "研究": "H"}},
            {"course": "操作系统", "reqs": {"工程知识": "H", "问题分析": "M", "设计/开发解决方案": "M", "研究": "M"}},
            {"course": "计算机网络", "reqs": {"工程知识": "M", "问题分析": "M", "使用现代工具": "M"}},
            {"course": "软件工程", "reqs": {"工程知识": "M", "设计/开发解决方案": "H", "个人和团队": "H", "沟通": "H", "项目管理": "H"}},
            {"course": "数据库原理", "reqs": {"工程知识": "M", "设计/开发解决方案": "H", "使用现代工具": "H"}},
            {"course": "高等数学A", "reqs": {"工程知识": "H", "问题分析": "H"}},
            {"course": "线性代数", "reqs": {"工程知识": "H", "问题分析": "M"}},
            {"course": "大学英语", "reqs": {"沟通": "H"}},
            {"course": "Web前端开发", "reqs": {"设计/开发解决方案": "H", "使用现代工具": "H"}},
            {"course": "编译原理", "reqs": {"工程知识": "M", "问题分析": "H"}},
            {"course": "计算机组成原理", "reqs": {"工程知识": "M"}},
        ],
    }

    fin_plan = {
        "major": "金融学",
        "basic_info": {
            "专业名称": "金融学",
            "专业代码": "020301K",
            "学制": "4年",
            "修业年限": "3—6年",
            "授予学位": "经济学学士",
        },
        "objectives": "本专业培养具备扎实的经济学与金融学理论基础，熟悉金融政策法规，掌握金融业务操作技能，"
                      "能够在银行、证券、保险等金融机构及政府经济管理部门从事金融分析、风险管理、投资理财等工作的应用型专业人才。",
        "graduation_requirements": [
            {"id": "1", "title": "经济分析能力",
             "desc": "能够运用现代经济学理论和方法，分析和解释经济金融现象与问题。"},
            {"id": "2", "title": "金融实务技能",
             "desc": "掌握金融产品设计、定价、交易和风险管理的基本方法和工具。"},
            {"id": "3", "title": "数据分析能力",
             "desc": "能够运用统计学和计量经济学方法，对金融数据进行处理、建模和分析。"},
            {"id": "4", "title": "风险管理意识",
             "desc": "具备识别、评估和管控金融风险的能力，理解金融监管框架和合规要求。"},
            {"id": "5", "title": "沟通表达能力",
             "desc": "能够撰写专业的金融分析报告，并进行有效的口头陈述和沟通。"},
            {"id": "6", "title": "国际视野",
             "desc": "了解国际金融市场运作规则，具备跨文化金融业务沟通能力。"},
            {"id": "7", "title": "团队协作",
             "desc": "能够在多元化的金融团队中有效协作，承担相应角色和职责。"},
            {"id": "8", "title": "职业素养",
             "desc": "遵守金融职业道德，具有社会责任感和合规意识。"},
            {"id": "9", "title": "创新思维",
             "desc": "能够结合金融科技发展趋势，创新性地解决金融实践问题。"},
            {"id": "10", "title": "终身学习",
             "desc": "具备自主学习和持续更新专业知识的能力，适应金融行业快速发展。"},
        ],
        "course_structure": {
            "categories": [
                {"name": "通识必修", "min_credits": 36, "color": "#1890ff"},
                {"name": "通识选修", "min_credits": 8, "color": "#52c41a"},
                {"name": "学科基础", "min_credits": 24, "color": "#fa8c16"},
                {"name": "专业必修", "min_credits": 26, "color": "#722ed1"},
                {"name": "专业选修", "min_credits": 14, "color": "#eb2f96"},
                {"name": "集中实践", "min_credits": 16, "color": "#13c2c2"},
                {"name": "创新创业", "min_credits": 4, "color": "#f5222d"},
                {"name": "美育劳动", "min_credits": 2, "color": "#faad14"},
            ],
            "total_min_credits": 130,
        },
        "ability_indicator_matrix": [
            {"indicator": "经济分析能力", "related_abilities": ["经济洞察", "数理分析"], "level": "H"},
            {"indicator": "金融实务技能", "related_abilities": ["财务技能", "数理分析"], "level": "H"},
            {"indicator": "数据分析能力", "related_abilities": ["数理分析", "财务技能"], "level": "H"},
            {"indicator": "风险管理意识", "related_abilities": ["风险意识", "经济洞察"], "level": "H"},
            {"indicator": "沟通表达能力", "related_abilities": ["沟通表达", "英语能力"], "level": "M"},
            {"indicator": "国际视野", "related_abilities": ["英语能力", "经济洞察"], "level": "M"},
            {"indicator": "团队协作", "related_abilities": ["沟通表达"], "level": "M"},
            {"indicator": "职业素养", "related_abilities": ["风险意识", "沟通表达"], "level": "M"},
            {"indicator": "创新思维", "related_abilities": ["学习能力", "经济洞察"], "level": "M"},
            {"indicator": "终身学习", "related_abilities": ["学习能力"], "level": "H"},
        ],
        "course_requirement_matrix": [
            {"course": "微观经济学", "reqs": {"经济分析能力": "H", "风险管理意识": "M"}},
            {"course": "宏观经济学", "reqs": {"经济分析能力": "H", "风险管理意识": "M"}},
            {"course": "计量经济学", "reqs": {"经济分析能力": "M", "数据分析能力": "H", "风险管理意识": "H"}},
            {"course": "金融学原理", "reqs": {"金融实务技能": "H", "风险管理意识": "M"}},
            {"course": "风险管理", "reqs": {"风险管理意识": "H", "职业素养": "M"}},
            {"course": "投资学", "reqs": {"金融实务技能": "H", "数据分析能力": "H", "风险管理意识": "H"}},
            {"course": "公司金融", "reqs": {"金融实务技能": "H", "沟通表达能力": "M"}},
            {"course": "统计学", "reqs": {"金融实务技能": "M", "数据分析能力": "H"}},
            {"course": "高等数学B", "reqs": {"经济分析能力": "M", "数据分析能力": "H"}},
            {"course": "大学英语", "reqs": {"沟通表达能力": "H"}},
            {"course": "金融英语", "reqs": {"风险管理意识": "H", "沟通表达能力": "H", "国际视野": "H"}},
            {"course": "国际金融", "reqs": {"经济分析能力": "M", "沟通表达能力": "H", "国际视野": "H"}},
        ],
    }

    cursor.execute(
        "INSERT INTO training_plan (major, plan_data) VALUES (?, ?)",
        ("软件工程", json.dumps(se_plan, ensure_ascii=False)),
    )
    cursor.execute(
        "INSERT INTO training_plan (major, plan_data) VALUES (?, ?)",
        ("金融学", json.dumps(fin_plan, ensure_ascii=False)),
    )
    profiles = [
        # 后端开发工程师
        ("后端开发工程师", "编程能力", 90, 0.30),
        ("后端开发工程师", "算法思维", 70, 0.15),
        ("后端开发工程师", "工程实践", 85, 0.25),
        ("后端开发工程师", "团队协作", 70, 0.15),
        ("后端开发工程师", "沟通表达", 50, 0.05),
        ("后端开发工程师", "学习能力", 60, 0.10),
        # 算法工程师
        ("算法工程师", "编程能力", 75, 0.15),
        ("算法工程师", "算法思维", 90, 0.30),
        ("算法工程师", "工程实践", 60, 0.10),
        ("算法工程师", "团队协作", 55, 0.10),
        ("算法工程师", "沟通表达", 45, 0.05),
        ("算法工程师", "学习能力", 75, 0.30),
        # 前端开发工程师
        ("前端开发工程师", "编程能力", 80, 0.20),
        ("前端开发工程师", "算法思维", 55, 0.10),
        ("前端开发工程师", "工程实践", 75, 0.25),
        ("前端开发工程师", "团队协作", 65, 0.15),
        ("前端开发工程师", "沟通表达", 60, 0.20),
        ("前端开发工程师", "学习能力", 60, 0.10),
        # 金融分析师
        ("金融分析师", "数理分析", 85, 0.25),
        ("金融分析师", "经济洞察", 80, 0.25),
        ("金融分析师", "风险意识", 70, 0.10),
        ("金融分析师", "沟通表达", 65, 0.15),
        ("金融分析师", "财务技能", 85, 0.20),
        ("金融分析师", "英语能力", 70, 0.05),
        # 风险管理师
        ("风险管理师", "数理分析", 80, 0.20),
        ("风险管理师", "经济洞察", 70, 0.15),
        ("风险管理师", "风险意识", 90, 0.30),
        ("风险管理师", "沟通表达", 60, 0.10),
        ("风险管理师", "财务技能", 75, 0.20),
        ("风险管理师", "英语能力", 65, 0.05),
    ]
    cursor.executemany(
        "INSERT INTO job_ability_profile (job_name, ability_dimension, required_level, importance_weight) VALUES (?, ?, ?, ?)",
        profiles,
    )


def _seed_students(cursor):
    pwd = bcrypt.hashpw("student123".encode(), bcrypt.gensalt()).decode()
    admin_pwd = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()

    students = [
        ("2021001", "张三", "计算机学院", "软件工程", "软工2101", 3.82, pwd, "student"),
        ("2021002", "李四", "计算机学院", "软件工程", "软工2101", 3.15, pwd, "student"),
        ("2021003", "王五", "计算机学院", "软件工程", "软工2102", 3.38, pwd, "student"),
        ("2021004", "赵六", "经济管理学院", "金融学", "金融2101", 3.76, pwd, "student"),
        ("2021005", "孙七", "经济管理学院", "金融学", "金融2101", 3.22, pwd, "student"),
        ("admin", "管理员", "信息中心", "系统管理", "admin", 0, admin_pwd, "admin"),
    ]
    cursor.executemany(
        "INSERT INTO students (student_id, name, college, major, class_name, gpa, password_hash, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        students,
    )

    _seed_courses(cursor)
    _seed_competitions(cursor)
    _seed_internships(cursor)
    _seed_projects(cursor)


def _seed_courses(cursor):
    courses = [
        # 张三 - 软件工程，学霸型
        ("2021001", "程序设计基础", 95, 4, 1.0, "2021秋", "学科基础"),
        ("2021001", "数据结构", 92, 4, 0.5, "2022春", "学科基础"),
        ("2021001", "算法设计与分析", 96, 3, 0.5, "2022秋", "专业必修"),
        ("2021001", "操作系统", 88, 4, 0.5, "2022秋", "专业必修"),
        ("2021001", "计算机网络", 85, 3, 0.5, "2023春", "专业必修"),
        ("2021001", "软件工程", 90, 3, 1.0, "2023春", "专业必修"),
        ("2021001", "数据库原理", 93, 3, 0.5, "2023春", "专业必修"),
        ("2021001", "高等数学A", 91, 5, 0, "2021秋", "通识必修"),
        ("2021001", "线性代数", 89, 3, 0, "2022春", "通识必修"),
        ("2021001", "大学英语", 87, 4, 0, "2021秋", "通识必修"),
        ("2021001", "Web前端开发", 90, 2, 1.0, "2023秋", "专业选修"),
        ("2021001", "编译原理", 86, 3, 0.5, "2023秋", "专业必修"),
        ("2021001", "计算机组成原理", 82, 3, 0.5, "2023秋", "专业必修"),
        # 李四 - 软件工程，实习型
        ("2021002", "程序设计基础", 72, 4, 1.0, "2021秋", "学科基础"),
        ("2021002", "数据结构", 68, 4, 0.5, "2022春", "学科基础"),
        ("2021002", "算法设计与分析", 65, 3, 0.5, "2022秋", "专业必修"),
        ("2021002", "操作系统", 70, 4, 0.5, "2022秋", "专业必修"),
        ("2021002", "计算机网络", 75, 3, 0.5, "2023春", "专业必修"),
        ("2021002", "软件工程", 80, 3, 1.0, "2023春", "专业必修"),
        ("2021002", "数据库原理", 78, 3, 0.5, "2023春", "专业必修"),
        ("2021002", "高等数学A", 74, 5, 0, "2021秋", "通识必修"),
        ("2021002", "线性代数", 70, 3, 0, "2022春", "通识必修"),
        ("2021002", "大学英语", 82, 4, 0, "2021秋", "通识必修"),
        ("2021002", "计算机组成原理", 68, 3, 0.5, "2023秋", "专业必修"),
        # 王五 - 软件工程，项目型
        ("2021003", "程序设计基础", 82, 4, 1.0, "2021秋", "学科基础"),
        ("2021003", "数据结构", 78, 4, 0.5, "2022春", "学科基础"),
        ("2021003", "算法设计与分析", 70, 3, 0.5, "2022秋", "专业必修"),
        ("2021003", "操作系统", 80, 4, 0.5, "2022秋", "专业必修"),
        ("2021003", "计算机网络", 76, 3, 0.5, "2023春", "专业必修"),
        ("2021003", "软件工程", 88, 3, 1.0, "2023春", "专业必修"),
        ("2021003", "数据库原理", 85, 3, 0.5, "2023春", "专业必修"),
        ("2021003", "高等数学A", 75, 5, 0, "2021秋", "通识必修"),
        ("2021003", "线性代数", 72, 3, 0, "2022春", "通识必修"),
        ("2021003", "大学英语", 68, 4, 0, "2021秋", "通识必修"),
        ("2021003", "Web前端开发", 90, 2, 1.0, "2023秋", "专业选修"),
        ("2021003", "编译原理", 74, 3, 0.5, "2023秋", "专业必修"),
        # 赵六 - 金融学，学霸型
        ("2021004", "微观经济学", 92, 4, 0, "2021秋", "学科基础"),
        ("2021004", "宏观经济学", 90, 4, 0, "2022春", "学科基础"),
        ("2021004", "计量经济学", 88, 3, 0.5, "2022秋", "专业必修"),
        ("2021004", "金融学原理", 93, 4, 0, "2022秋", "专业必修"),
        ("2021004", "风险管理", 85, 3, 0.5, "2023春", "专业必修"),
        ("2021004", "投资学", 90, 4, 0.5, "2023春", "专业必修"),
        ("2021004", "公司金融", 87, 3, 0, "2023秋", "专业必修"),
        ("2021004", "统计学", 89, 3, 0, "2022春", "通识必修"),
        ("2021004", "高等数学B", 91, 5, 0, "2021秋", "通识必修"),
        ("2021004", "大学英语", 88, 4, 0, "2021秋", "通识必修"),
        ("2021004", "金融英语", 86, 2, 0, "2023秋", "专业选修"),
        ("2021004", "国际金融", 84, 3, 0, "2023秋", "专业选修"),
        # 孙七 - 金融学，竞赛型
        ("2021005", "微观经济学", 75, 4, 0, "2021秋", "学科基础"),
        ("2021005", "宏观经济学", 72, 4, 0, "2022春", "学科基础"),
        ("2021005", "计量经济学", 70, 3, 0.5, "2022秋", "专业必修"),
        ("2021005", "金融学原理", 78, 4, 0, "2022秋", "专业必修"),
        ("2021005", "风险管理", 82, 3, 0.5, "2023春", "专业必修"),
        ("2021005", "投资学", 80, 4, 0.5, "2023春", "专业必修"),
        ("2021005", "公司金融", 76, 3, 0, "2023秋", "专业必修"),
        ("2021005", "统计学", 74, 3, 0, "2022春", "通识必修"),
        ("2021005", "高等数学B", 78, 5, 0, "2021秋", "通识必修"),
        ("2021005", "大学英语", 72, 4, 0, "2021秋", "通识必修"),
    ]
    cursor.executemany(
        "INSERT INTO courses (student_id, course_name, score, credit, practical_credit, semester, course_nature) VALUES (?, ?, ?, ?, ?, ?, ?)",
        courses,
    )


def _seed_competitions(cursor):
    comps = [
        ("2021001", "ACM-ICPC国际大学生程序设计竞赛", "国家级", "一等奖", 1, "2023-05"),
        ("2021001", "全国大学生数学建模竞赛", "国家级", "二等奖", 2, "2022-11"),
        ("2021002", "蓝桥杯全国软件和信息技术大赛", "省级", "三等奖", 3, "2023-04"),
        ("2021002", "中国大学生计算机设计大赛", "省级", "二等奖", 2, "2023-06"),
        ("2021003", "全国大学生软件创新大赛", "国家级", "三等奖", 2, "2023-08"),
        ("2021003", "蓝桥杯全国软件和信息技术大赛", "省级", "二等奖", 1, "2023-04"),
        ("2021004", "全国大学生金融挑战赛", "国家级", "一等奖", 2, "2023-07"),
        ("2021004", "全国大学生英语竞赛", "省级", "二等奖", 3, "2022-05"),
        ("2021005", "全国大学生数学建模竞赛", "国家级", "二等奖", 2, "2022-11"),
        ("2021005", "美国大学生数学建模竞赛", "国家级", "三等奖", 3, "2023-02"),
        ("2021005", "挑战杯全国大学生创业大赛", "省级", "一等奖", 1, "2023-05"),
    ]
    cursor.executemany(
        "INSERT INTO competitions (student_id, comp_name, level, award, rank, date) VALUES (?, ?, ?, ?, ?, ?)",
        comps,
    )


def _seed_internships(cursor):
    internships = [
        ("2021001", "阿里巴巴", "后端开发实习生", "参与电商平台订单系统的开发与维护", "2023-07 —2023-09"),
        ("2021002", "腾讯", "软件开发实习生", "负责微信小程序后台接口开发", "2023-01 —2023-06"),
        ("2021002", "字节跳动", "后端开发实习生", "参与内部工具平台开发", "2023-08 —2023-11"),
        ("2021003", "美团", "前端开发实习生", "参与商家端管理平台前端开发", "2023-07 —2023-09"),
        ("2021004", "中信证券", "行业研究实习生", "协助分析师完成行业研究报告", "2023-01 —2023-06"),
        ("2021004", "中国银行", "信贷分析实习生", "参与企业信贷审批流程", "2023-08 —2023-10"),
        ("2021005", "平安保险", "风险管理实习生", "参与公司风险评估模型搭建", "2023-07 —2023-10"),
    ]
    cursor.executemany(
        "INSERT INTO internships (student_id, company, position, description, period) VALUES (?, ?, ?, ?, ?)",
        internships,
    )


def _seed_projects(cursor):
    projects = [
        ("2021001", "校园二手交易平台", 1,
         "基于Spring Boot搭建的校园二手交易系统，支持用户认证、商品发布、在线聊天等功能",
         "2023-03 —2023-06"),
        ("2021001", "智能课程推荐系统", 2,
         "基于协同过滤算法实现个性化课程推荐，准确率提升30%",
         "2023-06 —2023-08"),
        ("2021002", "企业人事管理系统", 1,
         "独立完成前后端开发，实现员工信息管理、考勤、薪资等功能",
         "2023-05 —2023-08"),
        ("2021002", "在线考试系统", 3,
         "参与开发在线考试平台，负责试卷组卷算法和自动评分模块",
         "2023-09 —2023-12"),
        ("2021003", "个人博客系统", 1,
         "从零搭建个人技术博客，支持Markdown编辑、标签分类、评论功能",
         "2023-04 —2023-06"),
        ("2021003", "开源电商前端模板", 1,
         "在GitHub开源的电商前端模板项目，获得200+ Star",
         "2023-08 —2023-10"),
        ("2021004", "上市公司财务分析报告", 1,
         "对10家上市公司进行财务分析，完成估值模型搭建",
         "2023-05 —2023-08"),
        ("2021004", "量化交易策略回测系统", 2,
         "基于Python开发量化策略回测框架，支持多种技术指标",
         "2023-09 —2023-12"),
        ("2021005", "信用风险评估模型", 1,
         "使用逻辑回归和随机森林构建信用评分卡模型",
         "2023-06 —2023-09"),
        ("2021005", "金融数据可视化看板", 2,
         "搭建实时金融数据可视化面板，支持多维度数据分析",
         "2023-10 —2023-12"),
    ]
    cursor.executemany(
        "INSERT INTO projects (student_id, project_name, rank, description, period) VALUES (?, ?, ?, ?, ?)",
        projects,
    )
