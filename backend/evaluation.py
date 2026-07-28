"""
能力评估引擎

评估流程：
1. 获取学生的专业、课程、竞赛、实习、项目数据
2. 获取该专业的能力维度配置
3. 分别从四个数据源计算各维度的贡献分
4. 归一化到 0-100 分，生成解释信息
"""

LEVEL_SCORE = {"国际": 5, "国家": 4, "省": 3, "校": 2, "院": 1}
AWARD_SCORE = {"特等奖": 5, "一等奖": 4, "二等奖": 3, "三等奖": 2, "参与奖": 1}
ROLE_FACTOR = {"队长": 1.2, "核心队员": 1.0, "队员": 0.8}
COMPANY_TIER = {
    "阿里巴巴": 5, "腾讯": 5, "字节跳动": 5, "百度": 5, "美团": 4,
    "中信证券": 5, "中国银行": 4, "平安保险": 4, "京东": 4, "网易": 4,
    "华为": 5, "小米": 4, "滴滴": 4, "蚂蚁集团": 5,
}

# 竞赛→能力映射（默认映射，精确映射在数据库里可能没有）
COMPETITION_ABILITY_MAP = {
    "ACM": {"编程能力": 0.7, "算法思维": 0.9, "团队协作": 0.4},
    "程序设计": {"编程能力": 0.8, "算法思维": 0.5},
    "数学建模": {"算法思维": 0.7, "数理分析": 0.8, "学习能力": 0.5, "团队协作": 0.4},
    "蓝桥杯": {"编程能力": 0.8, "算法思维": 0.5},
    "软件创新": {"工程实践": 0.7, "编程能力": 0.5, "团队协作": 0.6},
    "计算机设计": {"工程实践": 0.6, "编程能力": 0.6, "团队协作": 0.4},
    "金融挑战": {"财务技能": 0.7, "经济洞察": 0.6, "风险意识": 0.5},
    "英语竞赛": {"英语能力": 0.8, "沟通表达": 0.4},
    "挑战杯": {"团队协作": 0.7, "工程实践": 0.5, "经济洞察": 0.4},
}


def evaluate_student_abilities(cursor, student_id: str) -> dict:
    """评估学生的各项能力得分，返回分数和解释"""
    # 获取学生基本信息
    student = cursor.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    if not student:
        raise ValueError(f"学生 {student_id} 不存在")

    major = student["major"]

    # 获取该专业的能力维度
    ability_configs = cursor.execute(
        "SELECT * FROM ability_config WHERE major = ? ORDER BY id", (major,)
    ).fetchall()
    ability_dims = {row["ability_dimension"]: row["weight"] for row in ability_configs}

    # 初始化分数容器 (每项能力的贡献明细)
    contributions = {dim: {"total": 0.0, "details": []} for dim in ability_dims}

    # 1. 课程贡献 (满分约40分)
    _eval_courses(cursor, student_id, contributions)

    # 2. 竞赛贡献 (满分约15分，但可超出)
    _eval_competitions(cursor, student_id, contributions)

    # 3. 实习贡献 (满分约10分)
    _eval_internships(cursor, student_id, contributions)

    # 4. 项目贡献 (满分约10分)
    _eval_projects(cursor, student_id, contributions)

    # 归一化到 0-100
    final_scores = {}
    for dim in ability_dims:
        raw = contributions[dim]["total"]
        # 使用 sigmoid-like 映射，满分约100
        score = min(100, max(0, round(raw * 100 / 50)))
        final_scores[dim] = {
            "score": score,
            "details": contributions[dim]["details"],
        }

    return {
        "student_id": student_id,
        "name": student["name"],
        "major": major,
        "abilities": final_scores,
        "ability_dims": list(ability_dims.keys()),
    }


def _eval_courses(cursor, student_id, contributions):
    courses = cursor.execute(
        "SELECT * FROM courses WHERE student_id = ?", (student_id,)
    ).fetchall()

    all_mappings = cursor.execute(
        "SELECT * FROM course_ability_mapping"
    ).fetchall()

    # 建立课程→能力映射查找表
    mapping_lookup = {}
    for m in all_mappings:
        key = m["course_name"]
        if key not in mapping_lookup:
            mapping_lookup[key] = []
        mapping_lookup[key].append((m["ability_dimension"], m["contribution_weight"]))

    total_credit = sum(c["credit"] for c in courses) if courses else 1

    for course in courses:
        course_name = course["course_name"]
        score = course["score"]
        credit = course["credit"]
        mappings = mapping_lookup.get(course_name, [])

        if not mappings:
            continue

        credit_weight = credit / total_credit
        for dim, weight in mappings:
            if dim in contributions:
                # 贡献 = 成绩百分制 * 映射权重 * 学分权重 * 40分满分
                contrib = (score / 100) * weight * credit_weight * 40
                contributions[dim]["total"] += contrib
                if contrib > 0.5:  # 只记录显著贡献
                    contributions[dim]["details"].append({
                        "source": f"课程: {course_name}",
                        "value": round(contrib, 1),
                        "comment": f"成绩{score}分，权重{weight}，学分{credit}",
                    })


def _eval_competitions(cursor, student_id, contributions):
    comps = cursor.execute(
        "SELECT * FROM competitions WHERE student_id = ?", (student_id,)
    ).fetchall()

    for comp in comps:
        level_v = LEVEL_SCORE.get(comp["level"], 1)
        award_v = AWARD_SCORE.get(comp["award"], 1)
        role_v = ROLE_FACTOR.get(comp["role"], 0.8)
        raw = level_v * award_v * role_v
        max_possible = 25  # 5*5*1.0

        # 匹配竞赛到能力维度
        matched = False
        for keyword, ability_map in COMPETITION_ABILITY_MAP.items():
            if keyword in comp["comp_name"]:
                for dim, weight in ability_map.items():
                    if dim in contributions:
                        contrib = (raw / max_possible) * weight * 15
                        contributions[dim]["total"] += contrib
                        contributions[dim]["details"].append({
                            "source": f"竞赛: {comp['comp_name']}",
                            "value": round(contrib, 1),
                            "comment": f"等级{comp['level']}，获奖{comp['award']}，角色{comp['role']}",
                        })
                matched = True
                break

        if not matched:
            # 默认归属到学习能力和团队协作
            for dim, weight in [("学习能力", 0.4), ("团队协作", 0.4)]:
                if dim in contributions:
                    contrib = (raw / max_possible) * weight * 15
                    contributions[dim]["total"] += contrib
                    contributions[dim]["details"].append({
                        "source": f"竞赛: {comp['comp_name']}",
                        "value": round(contrib, 1),
                        "comment": f"等级{comp['level']}，获奖{comp['award']}",
                    })


def _eval_internships(cursor, student_id, contributions):
    internships = cursor.execute(
        "SELECT * FROM internships WHERE student_id = ?", (student_id,)
    ).fetchall()

    for intern in internships:
        company_v = COMPANY_TIER.get(intern["company"], 2)
        duration = min(intern["duration_months"], 6)

        raw = company_v * (duration / 6)

        # 根据职位判断贡献维度
        position = intern["position"]
        if any(kw in position for kw in ["后端", "开发", "软件"]):
            ability_map = {"工程实践": 0.7, "团队协作": 0.5, "编程能力": 0.4}
        elif "前端" in position:
            ability_map = {"工程实践": 0.7, "编程能力": 0.5, "沟通表达": 0.4}
        elif "算法" in position:
            ability_map = {"算法思维": 0.7, "编程能力": 0.5, "学习能力": 0.4}
        elif any(kw in position for kw in ["金融", "行业研究", "信贷", "风险", "分析"]):
            ability_map = {"财务技能": 0.6, "经济洞察": 0.5, "风险意识": 0.5, "数理分析": 0.4}
        else:
            ability_map = {"团队协作": 0.5, "沟通表达": 0.5, "学习能力": 0.5}

        for dim, weight in ability_map.items():
            if dim in contributions:
                contrib = raw * weight * 10 / 5  # 满分约10
                contributions[dim]["total"] += contrib
                contributions[dim]["details"].append({
                    "source": f"实习: {intern['company']} {position}",
                    "value": round(contrib, 1),
                    "comment": f"{intern['company']}，{position}，{intern['duration_months']}个月",
                })


def _eval_projects(cursor, student_id, contributions):
    projects = cursor.execute(
        "SELECT * FROM projects WHERE student_id = ?", (student_id,)
    ).fetchall()

    for proj in projects:
        role = proj["role"]
        tech_stack = proj["tech_stack"].lower()

        if "负责人" in role or "发起人" in role:
            role_factor = 1.2
        elif "核心" in role:
            role_factor = 1.0
        elif "独立" in role:
            role_factor = 1.1
        else:
            role_factor = 0.8

        # 根据技术栈判断贡献维度
        ability_map = {}
        if any(t in tech_stack for t in ["python", "spring", "node", "go", "java"]):
            ability_map["编程能力"] = max(ability_map.get("编程能力", 0), 0.5)
            ability_map["工程实践"] = max(ability_map.get("工程实践", 0), 0.5)
        if any(t in tech_stack for t in ["react", "vue", "next", "tailwind"]):
            ability_map["编程能力"] = max(ability_map.get("编程能力", 0), 0.4)
            ability_map["工程实践"] = max(ability_map.get("工程实践", 0), 0.5)
        if any(t in tech_stack for t in ["sklearn", "scikit-learn", "pandas", "numpy", "matplotlib"]):
            ability_map["算法思维"] = max(ability_map.get("算法思维", 0), 0.4)
            ability_map["数理分析"] = max(ability_map.get("数理分析", 0), 0.4)
            ability_map["学习能力"] = max(ability_map.get("学习能力", 0), 0.3)
        if any(t in tech_stack for t in ["mysql", "redis", "mongodb", "postgresql"]):
            ability_map["工程实践"] = max(ability_map.get("工程实践", 0), 0.4)
        if any(t in tech_stack for t in ["excel", "wind", "sql"]):
            ability_map["财务技能"] = max(ability_map.get("财务技能", 0), 0.4)
            ability_map["数理分析"] = max(ability_map.get("数理分析", 0), 0.3)

        # 最低保障
        ability_map["团队协作"] = max(ability_map.get("团队协作", 0), 0.3)
        ability_map["学习能力"] = max(ability_map.get("学习能力", 0), 0.3)

        for dim, weight in ability_map.items():
            if dim in contributions:
                contrib = role_factor * weight * 10
                contributions[dim]["total"] += contrib
                contributions[dim]["details"].append({
                    "source": f"项目: {proj['project_name']}",
                    "value": round(contrib, 1),
                    "comment": f"角色: {role}，技术栈: {proj['tech_stack']}",
                })


def match_jobs(cursor, student_id: str) -> list:
    """将学生能力与岗位要求进行匹配"""
    ability_result = evaluate_student_abilities(cursor, student_id)
    student_abilities = {dim: info["score"] for dim, info in ability_result["abilities"].items()}
    major = ability_result["major"]

    # 获取所有岗位的能力要求
    job_profiles = cursor.execute(
        "SELECT * FROM job_ability_profile"
    ).fetchall()

    # 按岗位分组
    jobs = {}
    for row in job_profiles:
        job_name = row["job_name"]
        if job_name not in jobs:
            jobs[job_name] = []
        jobs[job_name].append({
            "dimension": row["ability_dimension"],
            "required": row["required_level"],
            "weight": row["importance_weight"],
        })

    results = []
    for job_name, requirements in jobs.items():
        total_match = 0
        total_weight = 0
        dim_matches = []
        gaps = []

        for req in requirements:
            dim = req["dimension"]
            required = req["required"]
            weight = req["weight"]

            student_score = student_abilities.get(dim, 50)

            # 单维度匹配度 = 学生分/要求分 (max 100%)
            dim_match = min(100, round(student_score / required * 100, 1)) if required > 0 else 100
            total_match += dim_match * weight
            total_weight += weight

            dim_matches.append({
                "dimension": dim,
                "student_score": student_score,
                "required": required,
                "match_rate": dim_match,
                "weight": weight,
            })

            if dim_match < 80:
                gaps.append({
                    "dimension": dim,
                    "current": student_score,
                    "required": required,
                    "gap": required - student_score,
                    "suggestion": _get_improvement_suggestion(dim, student_score, required, major),
                })

        overall_match = round(total_match / total_weight, 1) if total_weight > 0 else 0
        results.append({
            "job_name": job_name,
            "overall_match": overall_match,
            "dim_matches": dim_matches,
            "gaps": gaps,
        })

    # 按整体匹配度排序
    results.sort(key=lambda x: x["overall_match"], reverse=True)
    return results


def _get_improvement_suggestion(dim: str, current: float, required: float, major: str) -> str:
    suggestions = {
        "编程能力": "建议多参与开源项目或企业实习，提升实际编码能力",
        "算法思维": "建议加强算法课程学习，多刷LeetCode/ACM题目",
        "工程实践": "建议参与更多实际项目开发，积累工程经验",
        "团队协作": "建议参加团队竞赛或社团活动，提升协作能力",
        "沟通表达": "建议参加演讲、辩论或写作活动，锻炼表达能力",
        "学习能力": "建议拓展跨学科知识，培养自主学习习惯",
        "数理分析": "建议加强数学/统计基础，参与数据分析项目",
        "经济洞察": "建议多阅读经济金融类研究报告，关注行业动态",
        "风险意识": "建议学习风险管理课程，参与风险评估相关实践",
        "财务技能": "建议考取CFA/CPA等证书，加强财务建模能力",
        "英语能力": "建议备考六级/雅思/托福，阅读英文金融文献",
    }
    return suggestions.get(dim, f"建议针对性提升{dim}，当前{current}分，目标{required}分")
