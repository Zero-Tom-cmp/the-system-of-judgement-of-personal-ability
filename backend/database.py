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
        DROP TABLE IF EXISTS job_ability_profile;
        DROP TABLE IF EXISTS course_ability_mapping;
        DROP TABLE IF EXISTS ability_config;
        DROP TABLE IF EXISTS projects;
        DROP TABLE IF EXISTS internships;
        DROP TABLE IF EXISTS competitions;
        DROP TABLE IF EXISTS courses;
        DROP TABLE IF EXISTS students;

        CREATE TABLE students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(50) NOT NULL,
            college VARCHAR(100) NOT NULL,
            major VARCHAR(100) NOT NULL,
            class_name VARCHAR(50) NOT NULL,
            gpa REAL NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'student'
        );

        CREATE TABLE courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) NOT NULL,
            course_name VARCHAR(100) NOT NULL,
            score REAL NOT NULL,
            credit REAL NOT NULL,
            semester VARCHAR(20) NOT NULL,
            course_nature VARCHAR(20) NOT NULL
        );

        CREATE TABLE competitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) NOT NULL,
            comp_name VARCHAR(200) NOT NULL,
            level VARCHAR(20) NOT NULL,
            award VARCHAR(50) NOT NULL,
            role VARCHAR(20) NOT NULL,
            date VARCHAR(20) NOT NULL
        );

        CREATE TABLE internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) NOT NULL,
            company VARCHAR(100) NOT NULL,
            position VARCHAR(100) NOT NULL,
            duration_months INTEGER NOT NULL,
            description TEXT NOT NULL,
            date VARCHAR(20) NOT NULL
        );

        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) NOT NULL,
            project_name VARCHAR(200) NOT NULL,
            role VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            tech_stack VARCHAR(200) NOT NULL,
            date VARCHAR(20) NOT NULL
        );

        CREATE TABLE ability_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            major VARCHAR(100) NOT NULL,
            ability_dimension VARCHAR(50) NOT NULL,
            weight REAL NOT NULL
        );

        CREATE TABLE course_ability_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name VARCHAR(100) NOT NULL,
            ability_dimension VARCHAR(50) NOT NULL,
            contribution_weight REAL NOT NULL
        );

        CREATE TABLE job_ability_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name VARCHAR(100) NOT NULL,
            ability_dimension VARCHAR(50) NOT NULL,
            required_level REAL NOT NULL,
            importance_weight REAL NOT NULL
        );
    """)

    _seed_ability_config(cursor)
    _seed_course_mapping(cursor)
    _seed_job_profiles(cursor)
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


def _seed_job_profiles(cursor):
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
        ("2021001", "程序设计基础", 95, 4, "2021秋", "必修"),
        ("2021001", "数据结构", 92, 4, "2022春", "必修"),
        ("2021001", "算法设计与分析", 96, 3, "2022秋", "必修"),
        ("2021001", "操作系统", 88, 4, "2022秋", "必修"),
        ("2021001", "计算机网络", 85, 3, "2023春", "必修"),
        ("2021001", "软件工程", 90, 3, "2023春", "必修"),
        ("2021001", "数据库原理", 93, 3, "2023春", "必修"),
        ("2021001", "高等数学A", 91, 5, "2021秋", "必修"),
        ("2021001", "线性代数", 89, 3, "2022春", "必修"),
        ("2021001", "大学英语", 87, 4, "2021秋", "必修"),
        ("2021001", "Web前端开发", 90, 2, "2023秋", "选修"),
        ("2021001", "编译原理", 86, 3, "2023秋", "必修"),
        ("2021001", "计算机组成原理", 82, 3, "2023秋", "必修"),
        # 李四 - 软件工程，实习型
        ("2021002", "程序设计基础", 72, 4, "2021秋", "必修"),
        ("2021002", "数据结构", 68, 4, "2022春", "必修"),
        ("2021002", "算法设计与分析", 65, 3, "2022秋", "必修"),
        ("2021002", "操作系统", 70, 4, "2022秋", "必修"),
        ("2021002", "计算机网络", 75, 3, "2023春", "必修"),
        ("2021002", "软件工程", 80, 3, "2023春", "必修"),
        ("2021002", "数据库原理", 78, 3, "2023春", "必修"),
        ("2021002", "高等数学A", 74, 5, "2021秋", "必修"),
        ("2021002", "线性代数", 70, 3, "2022春", "必修"),
        ("2021002", "大学英语", 82, 4, "2021秋", "必修"),
        ("2021002", "计算机组成原理", 68, 3, "2023秋", "必修"),
        # 王五 - 软件工程，项目型
        ("2021003", "程序设计基础", 82, 4, "2021秋", "必修"),
        ("2021003", "数据结构", 78, 4, "2022春", "必修"),
        ("2021003", "算法设计与分析", 70, 3, "2022秋", "必修"),
        ("2021003", "操作系统", 80, 4, "2022秋", "必修"),
        ("2021003", "计算机网络", 76, 3, "2023春", "必修"),
        ("2021003", "软件工程", 88, 3, "2023春", "必修"),
        ("2021003", "数据库原理", 85, 3, "2023春", "必修"),
        ("2021003", "高等数学A", 75, 5, "2021秋", "必修"),
        ("2021003", "线性代数", 72, 3, "2022春", "必修"),
        ("2021003", "大学英语", 68, 4, "2021秋", "必修"),
        ("2021003", "Web前端开发", 90, 2, "2023秋", "选修"),
        ("2021003", "编译原理", 74, 3, "2023秋", "必修"),
        # 赵六 - 金融学，学霸型
        ("2021004", "微观经济学", 92, 4, "2021秋", "必修"),
        ("2021004", "宏观经济学", 90, 4, "2022春", "必修"),
        ("2021004", "计量经济学", 88, 3, "2022秋", "必修"),
        ("2021004", "金融学原理", 93, 4, "2022秋", "必修"),
        ("2021004", "风险管理", 85, 3, "2023春", "必修"),
        ("2021004", "投资学", 90, 4, "2023春", "必修"),
        ("2021004", "公司金融", 87, 3, "2023秋", "必修"),
        ("2021004", "统计学", 89, 3, "2022春", "必修"),
        ("2021004", "高等数学B", 91, 5, "2021秋", "必修"),
        ("2021004", "大学英语", 88, 4, "2021秋", "必修"),
        ("2021004", "金融英语", 86, 2, "2023秋", "选修"),
        ("2021004", "国际金融", 84, 3, "2023秋", "选修"),
        # 孙七 - 金融学，竞赛型
        ("2021005", "微观经济学", 75, 4, "2021秋", "必修"),
        ("2021005", "宏观经济学", 72, 4, "2022春", "必修"),
        ("2021005", "计量经济学", 70, 3, "2022秋", "必修"),
        ("2021005", "金融学原理", 78, 4, "2022秋", "必修"),
        ("2021005", "风险管理", 82, 3, "2023春", "必修"),
        ("2021005", "投资学", 80, 4, "2023春", "必修"),
        ("2021005", "公司金融", 76, 3, "2023秋", "必修"),
        ("2021005", "统计学", 74, 3, "2022春", "必修"),
        ("2021005", "高等数学B", 78, 5, "2021秋", "必修"),
        ("2021005", "大学英语", 72, 4, "2021秋", "必修"),
    ]
    cursor.executemany(
        "INSERT INTO courses (student_id, course_name, score, credit, semester, course_nature) VALUES (?, ?, ?, ?, ?, ?)",
        courses,
    )


def _seed_competitions(cursor):
    comps = [
        ("2021001", "ACM-ICPC国际大学生程序设计竞赛", "国际", "一等奖", "队长", "2023-05"),
        ("2021001", "全国大学生数学建模竞赛", "国家", "二等奖", "核心队员", "2022-11"),
        ("2021002", "蓝桥杯全国软件和信息技术大赛", "省", "三等奖", "队员", "2023-04"),
        ("2021002", "中国大学生计算机设计大赛", "省", "二等奖", "队员", "2023-06"),
        ("2021003", "全国大学生软件创新大赛", "国家", "三等奖", "核心队员", "2023-08"),
        ("2021003", "蓝桥杯全国软件和信息技术大赛", "省", "二等奖", "队员", "2023-04"),
        ("2021004", "全国大学生金融挑战赛", "国家", "一等奖", "核心队员", "2023-07"),
        ("2021004", "全国大学生英语竞赛", "省", "二等奖", "队员", "2022-05"),
        ("2021005", "全国大学生数学建模竞赛", "国家", "二等奖", "核心队员", "2022-11"),
        ("2021005", "美国大学生数学建模竞赛", "国际", "三等奖", "队员", "2023-02"),
        ("2021005", "挑战杯全国大学生创业大赛", "省", "一等奖", "队长", "2023-05"),
    ]
    cursor.executemany(
        "INSERT INTO competitions (student_id, comp_name, level, award, role, date) VALUES (?, ?, ?, ?, ?, ?)",
        comps,
    )


def _seed_internships(cursor):
    internships = [
        ("2021001", "阿里巴巴", "后端开发实习生", 3, "参与电商平台订单系统的开发与维护", "2023-07"),
        ("2021002", "腾讯", "软件开发实习生", 6, "负责微信小程序后台接口开发", "2023-01"),
        ("2021002", "字节跳动", "后端开发实习生", 4, "参与内部工具平台开发", "2023-08"),
        ("2021003", "美团", "前端开发实习生", 3, "参与商家端管理平台前端开发", "2023-07"),
        ("2021004", "中信证券", "行业研究实习生", 6, "协助分析师完成行业研究报告", "2023-01"),
        ("2021004", "中国银行", "信贷分析实习生", 3, "参与企业信贷审批流程", "2023-08"),
        ("2021005", "平安保险", "风险管理实习生", 4, "参与公司风险评估模型搭建", "2023-07"),
    ]
    cursor.executemany(
        "INSERT INTO internships (student_id, company, position, duration_months, description, date) VALUES (?, ?, ?, ?, ?, ?)",
        internships,
    )


def _seed_projects(cursor):
    projects = [
        (
            "2021001",
            "校园二手交易平台",
            "后端负责人",
            "基于Spring Boot搭建的校园二手交易系统，支持用户认证、商品发布、在线聊天等功能",
            "Spring Boot, MySQL, Redis, WebSocket",
            "2023-03",
        ),
        (
            "2021001",
            "智能课程推荐系统",
            "算法设计",
            "基于协同过滤算法实现个性化课程推荐，准确率提升30%",
            "Python, Scikit-learn, Flask",
            "2023-06",
        ),
        (
            "2021002",
            "企业人事管理系统",
            "全栈开发",
            "独立完成前后端开发，实现员工信息管理、考勤、薪资等功能",
            "Vue.js, Node.js, MongoDB",
            "2023-05",
        ),
        (
            "2021002",
            "在线考试系统",
            "核心开发",
            "参与开发在线考试平台，负责试卷组卷算法和自动评分模块",
            "React, Spring Boot, MySQL",
            "2023-09",
        ),
        (
            "2021003",
            "个人博客系统",
            "独立开发",
            "从零搭建个人技术博客，支持Markdown编辑、标签分类、评论功能",
            "Next.js, TailwindCSS, Prisma, PostgreSQL",
            "2023-04",
        ),
        (
            "2021003",
            "开源电商前端模板",
            "项目发起人",
            "在GitHub开源的电商前端模板项目，获得200+ Star",
            "React, TypeScript, Ant Design",
            "2023-08",
        ),
        (
            "2021004",
            "上市公司财务分析报告",
            "项目负责人",
            "对10家上市公司进行财务分析，完成估值模型搭建",
            "Excel, Python, Wind",
            "2023-05",
        ),
        (
            "2021004",
            "量化交易策略回测系统",
            "核心开发",
            "基于Python开发量化策略回测框架，支持多种技术指标",
            "Python, Pandas, NumPy, Matplotlib",
            "2023-09",
        ),
        (
            "2021005",
            "信用风险评估模型",
            "数据分析",
            "使用逻辑回归和随机森林构建信用评分卡模型",
            "Python, Scikit-learn, SQL",
            "2023-06",
        ),
        (
            "2021005",
            "金融数据可视化看板",
            "前端开发",
            "搭建实时金融数据可视化面板，支持多维度数据分析",
            "React, ECharts, Flask",
            "2023-10",
        ),
    ]
    cursor.executemany(
        "INSERT INTO projects (student_id, project_name, role, description, tech_stack, date) VALUES (?, ?, ?, ?, ?, ?)",
        projects,
    )
