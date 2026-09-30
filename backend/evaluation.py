"""
能力评估引擎

评估流程：
1. 获取学生的专业、课程、竞赛、实习、项目数据
2. 获取该专业的能力维度配置
3. 分别从四个数据源计算各维度的贡献分
4. 归一化到 0-1 后转百分制，生成解释信息（归一化规则见 ability_score.py）
"""

from ability_score import ability_score_100
from match_score import match_job

LEVEL_SCORE = {"国家级": 4, "省级": 3}
AWARD_SCORE = {"特等奖": 5, "一等奖": 4, "二等奖": 3, "三等奖": 2, "参与奖": 1}
RANK_FACTOR = {1: 1.2, 2: 1.0, 3: 0.8}
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

# 英语证书 → 等级权重(0~1)。阈值取常见的"门槛线":
#   四级 425 是多数学校的毕业线,550 起算良好,600 起算优秀;
#   六级 425 是常见求职门槛,500/550/600 依次递进;
#   雅思 6.5 / 托福 90 是主流留学门槛,故从这一档起算 0.7。
# 取值时取「不超过该分数的最高档」,低于最低档或证书为空则不计贡献。
ENGLISH_CERT_LEVELS = {
    "CET4":  [(425, 0.40), (550, 0.50), (600, 0.60)],
    "CET6":  [(425, 0.60), (500, 0.70), (550, 0.80), (600, 0.90)],
    "IELTS": [(6.0, 0.60), (6.5, 0.70), (7.0, 0.80), (7.5, 0.90)],
    "TOEFL": [(80, 0.60), (90, 0.70), (100, 0.80), (110, 0.90)],
}

# 证书贡献的满分。取 15 是为了与竞赛同量级——两者都是"绝对分"来源,
# 不受 credit_weight 的学分摊薄影响,这是英语能力此前最缺的东西。
ENGLISH_CERT_MAX = 15.0

# 各证书的分数有效区间(上限),供接口校验录入值是否离谱
ENGLISH_CERT_MAX_SCORE = {"CET4": 710, "CET6": 710, "IELTS": 9.0, "TOEFL": 120}


def english_cert_level(cert, score):
    """把(证书类型, 分数)换算成 0~1 的等级权重。

    证书为空、分数为空、类型不认识、或分数低于最低档时返回 None,
    调用方据此判定"该项无贡献"(而不是记 0 分)。
    """
    if not cert or score is None:
        return None
    thresholds = ENGLISH_CERT_LEVELS.get(str(cert).strip().upper())
    if not thresholds:
        return None

    level = None
    for threshold, value in thresholds:
        if float(score) >= threshold:
            level = value
    return level


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

    # 5. 英语证书贡献 (满分15分，仅对设有"英语能力"维度的专业生效)
    _eval_english_cert(cursor, student_id, contributions)

    # 归一化到 0-100。能力分只表达"该维度能力有多强"，**不乘专业权重** ——
    # 权重由匹配度公式的 e_i 承担（见 match_score.combine_matches），避免重复计入。
    final_scores = {}
    for dim in ability_dims:
        raw = contributions[dim]["total"]
        final_scores[dim] = {
            "score": ability_score_100(raw, dim),
            "raw": round(raw, 2),
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
        level_v = LEVEL_SCORE.get(comp["level"], 2)
        award_v = AWARD_SCORE.get(comp["award"], 1)
        rank = comp["rank"] if comp["rank"] else 3
        rank_v = RANK_FACTOR.get(rank, 0.8)
        raw = level_v * award_v * rank_v
        max_possible = 24  # 4*5*1.2

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
                            "comment": f"{comp['level']}，{comp['award']}，队内排名第{comp['rank']}",
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
                        "comment": f"{comp['level']}，{comp['award']}，队内排名第{comp['rank']}",
                    })


def _eval_internships(cursor, student_id, contributions):
    internships = cursor.execute(
        "SELECT * FROM internships WHERE student_id = ?", (student_id,)
    ).fetchall()

    for intern in internships:
        company_v = COMPANY_TIER.get(intern["company"], 2)
        raw = company_v / 5  # 归一化到 0~1

        # 根据职位判断贡献维度。
        # 任何岗位的实习都涉及需求对接、进度汇报与文档撰写，故各技术/金融分支统一
        # 附带沟通表达贡献 —— 此前只有"前端"和兜底分支带沟通表达，导致后端/算法
        # 实习的学生该维度几乎没有数据来源（只有 3 门课程映射）。
        position = intern["position"]
        if any(kw in position for kw in ["后端", "开发", "软件"]):
            ability_map = {"工程实践": 0.7, "团队协作": 0.5, "编程能力": 0.4, "沟通表达": 0.3}
        elif "前端" in position:
            ability_map = {"工程实践": 0.7, "编程能力": 0.5, "沟通表达": 0.4}
        elif "算法" in position:
            ability_map = {"算法思维": 0.7, "编程能力": 0.5, "学习能力": 0.4, "沟通表达": 0.3}
        elif any(kw in position for kw in ["金融", "行业研究", "信贷", "风险", "分析"]):
            ability_map = {"财务技能": 0.6, "经济洞察": 0.5, "风险意识": 0.5, "数理分析": 0.4,
                           "沟通表达": 0.4}
        else:
            ability_map = {"团队协作": 0.5, "沟通表达": 0.5, "学习能力": 0.5}

        for dim, weight in ability_map.items():
            if dim in contributions:
                contrib = raw * weight * 10  # 满分约10
                contributions[dim]["total"] += contrib
                contributions[dim]["details"].append({
                    "source": f"企业实习: {intern['company']} {position}",
                    "value": round(contrib, 1),
                    "comment": f"{intern['company']}，{position}，{intern['period']}",
                })


def _eval_projects(cursor, student_id, contributions):
    projects = cursor.execute(
        "SELECT * FROM projects WHERE student_id = ?", (student_id,)
    ).fetchall()

    for proj in projects:
        rank = proj["rank"] if proj["rank"] else 3
        rank_factor = RANK_FACTOR.get(rank, 0.8)

        # 根据项目描述关键词判断贡献维度
        desc = proj["description"]
        ability_map = {}
        if any(kw in desc for kw in ["Spring", "Django", "Node", "Go", "Java", "Python", "后端", "后台"]):
            ability_map["编程能力"] = max(ability_map.get("编程能力", 0), 0.5)
            ability_map["工程实践"] = max(ability_map.get("工程实践", 0), 0.5)
        if any(kw in desc for kw in ["React", "Vue", "前端", "UI", "页面"]):
            ability_map["编程能力"] = max(ability_map.get("编程能力", 0), 0.4)
            ability_map["工程实践"] = max(ability_map.get("工程实践", 0), 0.5)
        if any(kw in desc for kw in ["算法", "推荐", "机器学习", "模型", "预测", "分类", "回归"]):
            ability_map["算法思维"] = max(ability_map.get("算法思维", 0), 0.4)
            ability_map["数理分析"] = max(ability_map.get("数理分析", 0), 0.4)
            ability_map["学习能力"] = max(ability_map.get("学习能力", 0), 0.3)
        if any(kw in desc for kw in ["数据库", "MySQL", "Redis", "MongoDB"]):
            ability_map["工程实践"] = max(ability_map.get("工程实践", 0), 0.4)
        if any(kw in desc for kw in ["财务", "估值", "金融", "量化", "交易", "信用"]):
            ability_map["财务技能"] = max(ability_map.get("财务技能", 0), 0.4)
            ability_map["数理分析"] = max(ability_map.get("数理分析", 0), 0.3)

        # 最低保障：任何项目都涉及分工协作、进度同步与成果汇报
        ability_map["团队协作"] = max(ability_map.get("团队协作", 0), 0.3)
        ability_map["学习能力"] = max(ability_map.get("学习能力", 0), 0.3)
        ability_map["沟通表达"] = max(ability_map.get("沟通表达", 0), 0.3)

        for dim, weight in ability_map.items():
            if dim in contributions:
                contrib = rank_factor * weight * 10
                contributions[dim]["total"] += contrib
                contributions[dim]["details"].append({
                    "source": f"项目: {proj['project_name']}",
                    "value": round(contrib, 1),
                    "comment": f"队内排名第{proj['rank']}，{proj['period']}",
                })


def _eval_english_cert(cursor, student_id, contributions):
    """英语证书贡献。

    英语能力此前只有课程 + 一个"英语竞赛"入口,而课程贡献受 credit_weight 的
    学分摊薄影响(分母是全专业课程总学分),实测该维度的上限只有 40 分的
    36%~44% —— 就算课程全考 100 分、拿到国家级特等奖也够不着及格线。
    证书像竞赛一样是"绝对分"来源,正好补上这个缺口。
    """
    if "英语能力" not in contributions:
        return  # 该专业没有这个维度(如软件工程)

    row = cursor.execute(
        "SELECT english_cert, english_score FROM students WHERE student_id = ?",
        (student_id,),
    ).fetchone()
    if not row:
        return

    level = english_cert_level(row["english_cert"], row["english_score"])
    if level is None:
        return  # 未填写或未达最低档，保持"无贡献"

    contrib = level * ENGLISH_CERT_MAX
    contributions["英语能力"]["total"] += contrib
    contributions["英语能力"]["details"].append({
        "source": f"英语证书: {row['english_cert']} {row['english_score']:g}",
        "value": round(contrib, 1),
        "comment": f"等级权重 {level}，满分 {ENGLISH_CERT_MAX:g}",
    })


def match_jobs(cursor, student_id: str) -> list:
    """将学生能力与岗位要求进行匹配"""
    # 检查学生是否有任何评估数据
    has_data = False
    for table in ["courses", "competitions", "internships", "projects"]:
        count = cursor.execute(
            f"SELECT COUNT(*) as c FROM {table} WHERE student_id = ?", (student_id,)
        ).fetchone()["c"]
        if count > 0:
            has_data = True
            break

    if not has_data:
        return []  # 无任何数据，无法评估

    ability_result = evaluate_student_abilities(cursor, student_id)
    abilities = ability_result["abilities"]
    major = ability_result["major"]

    # 根据学生专业筛选相关岗位
    MAJOR_JOBS = {
        "软件工程": ["后端开发工程师", "算法工程师", "前端开发工程师"],
        "金融学":   ["金融分析师", "风险管理师"],
    }
    relevant_jobs = MAJOR_JOBS.get(major, [])

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
        # 跳过与该专业无关的岗位
        if relevant_jobs and job_name not in relevant_jobs:
            continue

        # 组装维度规格（0~100 口径，换算与公式由 match_score 负责）
        specs = []
        for req in requirements:
            dim = req["dimension"]
            info = abilities.get(dim)
            # 两种情况都算"无证据"：该维度不在学生的能力配置里，或维度在配置里
            # 但没有任何数据来源（raw == 0）。二者都交给 match_score 的"数据缺失"
            # 分支处理（m = 0 且权重保留在分母，偏严，避免缺失维度反而抬高总分）。
            student_score = None if (info is None or info.get("raw", 0) == 0) else info["score"]
            specs.append({
                "dimension": dim,
                "student_score": student_score,
                "required_level": req["required"],
                "weight": req["weight"],
            })

        # 单维度匹配度 m = 1 - |s - r|，综合 D = Σ e·m，得分 = 100·D
        job = match_job(job_name, specs)

        dim_matches = []
        gaps = []
        for d in job.dimensions:
            dim_matches.append({
                "dimension": d.dimension,
                "student_score": None if d.student is None else round(d.student * 100, 1),
                "required": None if d.required is None else round(d.required * 100, 1),
                "match_rate": None if (d.data_missing or d.no_requirement) else round(d.match * 100, 1),
                "weight": d.weight,
                "insufficient": d.data_missing,
                "data_missing": d.data_missing,
                "no_requirement": d.no_requirement,
            })

            # 数据缺失/岗位无要求的维度不生成"提升建议" —— 前者不是短板而是没证据，
            # 后者岗位根本不看。缺失情况单独通过 missing_dimensions 暴露给前端。
            if d.data_missing or d.no_requirement:
                continue

            # 只有"学生低于岗位要求"才算短板。不能只看 match_rate < 80:
            # m = 1-|s-r| 对超额达标同样计差,一个远超要求的维度匹配度同样会掉到
            # 80 以下;若据此生成提升建议,就会出现"你已超出 35 分,建议多刷题"
            # 这种反向建议。
            match_rate = round(d.match * 100, 1)
            if d.student < d.required and match_rate < 80:
                current = d.student * 100
                required = d.required * 100
                gaps.append({
                    "dimension": d.dimension,
                    "current": round(current, 1),
                    "required": round(required, 1),
                    "gap": round(required - current, 1),
                    "suggestion": _get_improvement_suggestion(d.dimension, current, required, major),
                })

        results.append({
            "job_name": job_name,
            "overall_match": job.score,
            "d_base": round(job.d_base * 100, 1),
            "d_final": round(job.d_final * 100, 1),
            "dim_matches": dim_matches,
            "gaps": gaps,
            "missing_dimensions": job.missing_dimensions,
            "gate_failed": job.gate_failed,
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
