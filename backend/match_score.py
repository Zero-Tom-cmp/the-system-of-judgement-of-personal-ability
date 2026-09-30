# -*- coding: utf-8 -*-
"""岗位匹配度计算 —— 纯函数模块,不读数据库、不依赖 FastAPI。

对应论文《基于AHP-模糊综合评价的人才岗位匹配度测算》的核心测算部分。需要说明的是,
论文正文印的两个核心公式**都是错的**,本模块采用修正后的正确形式(修正依据见各函数
注释,并已用论文自身的示例数据复现验证,见 tests/test_match_score.py):

    (1) 单因素匹配度(确定型)  m_i = 1 - |s_i - r_i|
    (2) 单因素匹配度(模糊型)  m_i = Σ_k r_ik · (1 - |v_k - r_i|)
    (3) 综合匹配度            D   = Σ_i e_i · m_i     (e_i 为 AHP 权重,Σe_i = 1)
    (4) 百分制得分            Score = 100 · D_final

论文没有、属于本系统扩展的三项(默认取值见下方常量):
    - 硬性门槛        D_final = D_base · Π_j g_j          (默认不启用,gates 传空)
    - 学生数据缺失    m = 0 且权重保留在分母              (偏严,已确认)
    - 岗位要求为"无"  权重置 0 后重新归一化                (既不帮忙也不扣分)

分层约定:
    - certain_match / fuzzy_match 等核心公式函数只处理 **0~1 归一化值**
    - match_dimension / match_job 负责**单位换算**(0~100 → 0~1)与策略分派
"""

from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

#: 论文的 6 级评价等级及其分值(优秀=1 … 无=0)
GRADE_VALUES = {
    "优秀": 1.0,
    "良好": 0.8,
    "中": 0.6,
    "可": 0.4,
    "差": 0.2,
    "无": 0.0,
}

#: 等级顺序,用于隶属度字典的校验与展示
GRADE_ORDER = ("优秀", "良好", "中", "可", "差", "无")

#: 岗位要求为"无"的处理策略
NO_REQUIREMENT_EXCLUDE = "exclude"      # 权重置 0 并重新归一化(默认)
NO_REQUIREMENT_KEEP_FULL = "keep_full"  # 该维度匹配度记 1,权重保留

#: 学生数据缺失的处理策略
MISSING_KEEP_WEIGHT = "keep_weight"  # m=0 且权重保留在分母(默认,偏严)
MISSING_EXCLUDE = "exclude"          # m=0 且权重置 0(偏松,等同现状的隐式重算)

#: 超额达标(学生分值高于岗位要求)的处理策略 —— 详见 certain_match 文档
OVERSHOOT_SYMMETRIC = "symmetric"    # 论文原式:m = 1 - |s - r|,超额同样计差
OVERSHOOT_ONE_SIDED = "one_sided"    # 只惩罚不达标:m = 1 - max(0, r - s)


# ---------------------------------------------------------------------------
# 结果类型
# ---------------------------------------------------------------------------


class DimensionMatch(NamedTuple):
    """单个能力维度的匹配结果。"""

    dimension: str                    # 维度名,如"编程能力"
    match: float                      # 匹配度 m_i ∈ [0,1],数据缺失时记 0
    weight: float                     # 参与归一化的权重,被剔除时为 0
    required: Optional[float]         # 岗位要求(0~1),无要求时为 None
    student: Optional[float]          # 学生能力值(0~1),数据缺失时为 None
    data_missing: bool                # 学生该维度数据缺失
    no_requirement: bool              # 岗位对该维度无要求
    mode: str                         # certain / fuzzy / missing / excluded / no_requirement
    membership: Optional[Dict[str, float]] = None  # 模糊型时保留原始隶属度


class JobMatchResult(NamedTuple):
    """一个岗位的完整匹配结果。"""

    job_name: str
    d_base: float                     # 基础综合匹配度 D_base
    d_final: float                    # 过门槛后的匹配度 D_final
    score: float                      # 百分制得分 0~100
    dimensions: List[DimensionMatch]
    gate_failed: List[float]          # 未达标(<1)的门槛值,空表示全部通过
    evaluated_weight: float           # 实际参与计算的权重之和,为 0 表示无法评估
    missing_dimensions: List[str]     # 数据缺失的维度名


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------


def clamp01(value: float) -> float:
    """把数值截断到 [0,1]。"""
    return max(0.0, min(1.0, float(value)))


def score_to_unit(score_0_100: float) -> float:
    """把 0~100 的分值线性归一化到 [0,1](M6 方案 A:连续归一化)。

    注意入参口径必须是 **0~100**。若混入 0~1 的值(如 0.9),会得到 0.009 这种
    错误结果 —— 因此这里对超出 0~100 的输入直接报错,让单位混用尽早暴露。
    """
    value = float(score_0_100)
    if not 0.0 <= value <= 100.0:
        raise ValueError(f"分值必须在 0~100 区间,当前为 {score_0_100}")
    return value / 100.0


# ---------------------------------------------------------------------------
# 核心公式
# ---------------------------------------------------------------------------


def certain_match(
    student_value: float,
    required_value: float,
    overshoot_policy: str = OVERSHOOT_SYMMETRIC,
) -> float:
    """确定型单因素匹配度 m = 1 - |s - r|(入参为 0~1 归一化值)。

    **对论文的修正**:论文正文印的是"匹配度＝1－人才分值－岗位分值",该式在
    s=0.8、r=0.8 时会算出 -0.6,明显有误。论文紧接着的说明"相差'0'…对应匹配度
    为1;相差'1'…对应匹配度为0"证明原意是 1-|s-r|;论文 Table 2 的 G 矩阵元素
    也恰为 1-|等级分值－要求分值|。故此处采用 1-|s-r|。

    **overshoot_policy(请你留意)**:默认 "symmetric" 严格照论文,但该式对
    「超额达标」同样计差 —— 学生 1.0 对要求 0.6 只得 0.6,反而低于学生 0.6 对
    要求 0.6 的 1.0 分,即**能力越强匹配度越低**。这是论文模型的固有性质(它衡量
    "匹配"而非"优秀",认为过度胜任者同样不匹配),对社招或许合理,但对"给学生
    推荐岗位"可能反直觉。若确认要改,把策略切到 "one_sided" 即可,一处生效。
    """
    student = clamp01(student_value)
    required = clamp01(required_value)

    if overshoot_policy == OVERSHOOT_SYMMETRIC:
        gap = abs(student - required)
    elif overshoot_policy == OVERSHOOT_ONE_SIDED:
        gap = max(0.0, required - student)
    else:
        raise ValueError(f"未知的超额达标策略:{overshoot_policy}")

    return clamp01(1.0 - gap)


def normalize_membership(membership: Dict[str, float]) -> Dict[str, float]:
    """校验并归一化隶属度字典,使其和为 1。

    论文要求每个因素的隶属度满足 Σ_k r_ik = 1(Table 8 每列之和为 1)。
    输入允许未归一化,这里统一处理,避免调用方手工凑数。
    """
    if not membership:
        raise ValueError("隶属度不能为空")

    unknown = set(membership) - set(GRADE_VALUES)
    if unknown:
        raise ValueError(f"存在未知等级 {sorted(unknown)},合法等级为 {list(GRADE_ORDER)}")

    negatives = {k: v for k, v in membership.items() if float(v) < 0}
    if negatives:
        raise ValueError(f"隶属度不能为负数:{negatives}")

    values = {grade: 0.0 for grade in GRADE_ORDER}
    for grade, value in membership.items():
        values[grade] = float(value)

    total = sum(values.values())
    if total <= 0:
        raise ValueError("隶属度之和为 0,无法归一化")
    return {grade: value / total for grade, value in values.items()}


def fuzzy_match(
    membership: Dict[str, float],
    required_value: float,
    overshoot_policy: str = OVERSHOOT_SYMMETRIC,
) -> float:
    """模糊型单因素匹配度 m = Σ_k r_ik · (1 - |v_k - r|)。

    **对论文的修正**:论文正文印的是 "F = G·R^T",但 G 与 R 同为 m×n 矩阵,
    两个 m×n 相乘无定义。论文 Table 2 的 G 矩阵元素恰为 1-|等级分值-要求分值|,
    Table 8 的 R^T 是"等级 × 因素"且每列(每个因素)之和为 1,故正确形式是
    **逐因素内积**,即本函数。已用论文自身数据验证:健康状况(要求良好)→0.90、
    外在形象(要求中)→0.88、业务水平(要求优秀)→0.86,再加权得 D=0.8454,
    与论文印出的结果完全一致。

    参数:
        membership      {等级: 隶属度},会自动归一化,如 {"优秀": 0.4, "良好": 0.5, "中": 0.1}
        required_value  岗位要求等级分值(0~1)。采用 M6 方案 A(连续归一化)后,
                        这里也可以是 0.9 这样的连续值,公式依然成立。
    """
    values = normalize_membership(membership)
    required = clamp01(required_value)

    total = 0.0
    for grade, value in values.items():
        grade_value = GRADE_VALUES[grade]
        if overshoot_policy == OVERSHOOT_SYMMETRIC:
            gap = abs(grade_value - required)
        elif overshoot_policy == OVERSHOOT_ONE_SIDED:
            gap = max(0.0, required - grade_value)
        else:
            raise ValueError(f"未知的超额达标策略:{overshoot_policy}")
        total += value * (1.0 - gap)

    return clamp01(total)


# ---------------------------------------------------------------------------
# 维度级调度
# ---------------------------------------------------------------------------


def match_dimension(
    dimension: str,
    student_score: Optional[float],
    required_level: Optional[float],
    weight: float = 1.0,
    membership: Optional[Dict[str, float]] = None,
    overshoot_policy: str = OVERSHOOT_SYMMETRIC,
    missing_policy: str = MISSING_KEEP_WEIGHT,
    no_requirement_policy: str = NO_REQUIREMENT_EXCLUDE,
) -> DimensionMatch:
    """计算单个维度的匹配度,并处理"无要求 / 数据缺失"两种特殊情况。

    student_score / required_level 传 **0~100** 口径(与数据库字段一致),
    内部自动归一化。membership 非空时走模糊型,否则走确定型(默认)。

    判定优先级:
        1. 岗位无要求(required_level 为 None 或 <= 0)—— 该维度失去意义,
           默认剔除权重;学生数据缺失在此情形下不再重要,但仍如实标记。
        2. 学生数据缺失(student_score 为 None)—— 默认 m=0 但**保留权重**,
           即"没证据就算不匹配",避免缺失维度越多、总分被剩下的高分维度拉得越高。
    """
    # --- 情况 1:岗位对该维度无要求 -------------------------------------
    if required_level is None or float(required_level) <= 0:
        if no_requirement_policy == NO_REQUIREMENT_EXCLUDE:
            effective_weight = 0.0
            mode = "excluded"
        elif no_requirement_policy == NO_REQUIREMENT_KEEP_FULL:
            effective_weight = float(weight)
            mode = "no_requirement"
        else:
            raise ValueError(f"未知的岗位无要求策略:{no_requirement_policy}")

        return DimensionMatch(
            dimension=dimension,
            match=1.0,                      # 剔除时不参与加权,此值仅供展示
            weight=effective_weight,
            required=None,
            student=None if student_score is None else score_to_unit(student_score),
            data_missing=student_score is None,
            no_requirement=True,
            mode=mode,
        )

    required = score_to_unit(required_level)

    # --- 情况 2:学生该维度数据缺失 -------------------------------------
    if student_score is None:
        if missing_policy == MISSING_KEEP_WEIGHT:
            effective_weight = float(weight)
        elif missing_policy == MISSING_EXCLUDE:
            effective_weight = 0.0
        else:
            raise ValueError(f"未知的数据缺失策略:{missing_policy}")

        return DimensionMatch(
            dimension=dimension,
            match=0.0,
            weight=effective_weight,
            required=required,
            student=None,
            data_missing=True,
            no_requirement=False,
            mode="missing",
        )

    # --- 情况 3:正常计算 ------------------------------------------------
    student = score_to_unit(student_score)
    if membership:
        match = fuzzy_match(membership, required, overshoot_policy)
        mode = "fuzzy"
    else:
        match = certain_match(student, required, overshoot_policy)
        mode = "certain"

    return DimensionMatch(
        dimension=dimension,
        match=match,
        weight=float(weight),
        required=required,
        student=student,
        data_missing=False,
        no_requirement=False,
        mode=mode,
        membership=normalize_membership(membership) if membership else None,
    )


# ---------------------------------------------------------------------------
# 综合匹配度
# ---------------------------------------------------------------------------


def combine_matches(dimensions: Sequence[DimensionMatch]) -> float:
    """D_base = Σ e_i · m_i,其中 e_i = weight_i / Σ weight(论文式(3))。

    权重会在内部重新归一化,因此调用方不必手工保证 Σe_i = 1 —— 论文 Table 里
    的权重印到三位小数、实际和为 0.998,归一是必要的。

    权重为 0 的维度(岗位无要求)不参与计算;若所有维度权重都为 0,返回 0.0,
    调用方应据此判定"无法评估"而不是"匹配度 0"。
    """
    total_weight = sum(d.weight for d in dimensions)
    if total_weight <= 0:
        return 0.0
    return sum(d.weight * d.match for d in dimensions) / total_weight


def apply_gates(d_base: float, gates: Optional[Iterable[float]] = None) -> float:
    """D_final = D_base · Π g_j —— **本项为扩展,论文没有**。

    gates 为空或 None 时原样返回 D_base,即默认不启用门槛,保证不改变现有结果。
    只有岗位明确标注了"必须/至少"类硬性要求时才传入,未达标(如 0)会把总分直接
    压制到 0,用于表达加权和无法表达的"一票否决"。
    """
    result = clamp01(d_base)
    if not gates:
        return result

    for gate in gates:
        value = float(gate)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"门槛系数必须在 0~1 区间: {gate}")
        result *= value
    return clamp01(result)


def to_score(d_final: float, digits: int = 1) -> float:
    """百分制得分 Score = 100 · D_final。"""
    return round(100.0 * clamp01(d_final), digits)


def match_job(
    job_name: str,
    specs: Sequence[dict],
    gates: Optional[Iterable[float]] = None,
    overshoot_policy: str = OVERSHOOT_SYMMETRIC,
    missing_policy: str = MISSING_KEEP_WEIGHT,
    no_requirement_policy: str = NO_REQUIREMENT_EXCLUDE,
) -> JobMatchResult:
    """一个岗位的完整匹配流程:逐维度算匹配度 → 加权 → 过门槛 → 百分制。

    specs 是维度规格列表,每项支持:
        {"dimension": "编程能力", "student_score": 88.0,
         "required_level": 90.0, "weight": 0.3,
         "membership": {...}}          # 可选,给了就走模糊型
    """
    dimensions = [
        match_dimension(
            dimension=spec["dimension"],
            student_score=spec.get("student_score"),
            required_level=spec.get("required_level"),
            weight=spec.get("weight", 1.0),
            membership=spec.get("membership"),
            overshoot_policy=overshoot_policy,
            missing_policy=missing_policy,
            no_requirement_policy=no_requirement_policy,
        )
        for spec in specs
    ]

    d_base = combine_matches(dimensions)
    gate_values = [float(g) for g in gates] if gates else []
    d_final = apply_gates(d_base, gate_values)

    return JobMatchResult(
        job_name=job_name,
        d_base=d_base,
        d_final=d_final,
        score=to_score(d_final),
        dimensions=dimensions,
        gate_failed=[g for g in gate_values if g < 1.0],
        evaluated_weight=sum(d.weight for d in dimensions),
        missing_dimensions=[d.dimension for d in dimensions if d.data_missing],
    )
