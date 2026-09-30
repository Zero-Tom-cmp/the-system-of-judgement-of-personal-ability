"""岗位匹配度公式的单元测试。

核心证据是 test_paper_full_example_reproduces_published_D:用论文 Table 8 的隶属度
矩阵 + Table 1 的岗位等级要求,复现出论文印出的 F 向量与 D=0.8454。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from match_score import (
    GRADE_VALUES,
    MISSING_EXCLUDE,
    MISSING_KEEP_WEIGHT,
    NO_REQUIREMENT_EXCLUDE,
    NO_REQUIREMENT_KEEP_FULL,
    OVERSHOOT_ONE_SIDED,
    OVERSHOOT_SYMMETRIC,
    certain_match,
    combine_matches,
    fuzzy_match,
    match_dimension,
    match_job,
    normalize_membership,
    score_to_unit,
    to_score,
)


# ---------------------------------------------------------------------------
# 论文原始数据(Table 1 / Table 2 / Table 8 / AHP 权重)
# ---------------------------------------------------------------------------

#: 论文 Table 8 的模糊关系矩阵 R^T:每个因素对各等级的隶属度,列和为 1
PAPER_MEMBERSHIPS = {
    "健康状况": {"优秀": 0.2, "良好": 0.5, "中": 0.3},
    "外在形象": {"良好": 0.6, "中": 0.4},
    "业务水平": {"优秀": 0.4, "良好": 0.5, "中": 0.1},
    "管理能力": {"优秀": 0.5, "良好": 0.3, "中": 0.2},
    "创新能力": {"优秀": 0.2, "良好": 0.2, "中": 0.2, "可": 0.4},
    "忠诚度":   {"优秀": 0.2, "良好": 0.3, "中": 0.3, "可": 0.2},
    "责任感":   {"优秀": 0.3, "良好": 0.3, "中": 0.2, "可": 0.2},
    "业绩":     {"优秀": 0.2, "良好": 0.4, "中": 0.3, "可": 0.1},
    "奖励":     {"优秀": 0.5, "良好": 0.2, "中": 0.3},
}

#: 论文中"技术主管"岗位对各因素的等级要求(由论文印出的 F 反推并逐项验证)
PAPER_REQUIRED_GRADES = {
    "健康状况": "良好", "外在形象": "中",   "业务水平": "优秀",
    "管理能力": "优秀", "创新能力": "中",   "忠诚度":   "良好",
    "责任感":   "良好", "业绩":     "良好", "奖励":     "中",
}

#: 论文印出的单因素匹配度 F
PAPER_EXPECTED_F = [0.90, 0.88, 0.86, 0.86, 0.80, 0.82, 0.82, 0.86, 0.76]

#: 论文给出的 AHP 权重 E(注意:印到三位小数,实际和为 0.998)
PAPER_WEIGHTS = [0.065, 0.013, 0.223, 0.223, 0.074, 0.100, 0.100, 0.167, 0.033]

PAPER_FACTORS = list(PAPER_MEMBERSHIPS)


# ---------------------------------------------------------------------------
# 1. 确定型匹配
# ---------------------------------------------------------------------------


def test_certain_match_exact_and_bounded():
    """m = 1 - |s - r| 的基本性质:相等得 1、差 0.2 得 0.8、两端不越界。"""
    assert certain_match(0.8, 0.8) == pytest.approx(1.0)
    assert certain_match(0.8, 0.6) == pytest.approx(0.8)
    assert certain_match(0.6, 0.8) == pytest.approx(0.8)
    assert certain_match(0.0, 1.0) == pytest.approx(0.0)
    assert certain_match(1.0, 0.0) == pytest.approx(0.0)
    # 超出 [0,1] 的输入会被截断,不会算出负匹配度
    assert certain_match(1.5, 0.0) == pytest.approx(0.0)


def test_certain_match_rejects_unknown_policy():
    with pytest.raises(ValueError, match="未知的超额达标策略"):
        certain_match(0.8, 0.8, overshoot_policy="whatever")


def test_overqualified_penalty_is_a_deliberate_paper_property():
    """论文原式的固有性质:超额达标一样计差,能力越强匹配度反而越低。

    这里把这个反直觉的性质固定下来,避免它被无意改掉;若要改成只惩罚不达标,
    切换到 one_sided 策略即可。
    """
    # 论文原式:刚好达标得满分,超额 0.4 反而只得 0.6
    assert certain_match(0.6, 0.6, OVERSHOOT_SYMMETRIC) == pytest.approx(1.0)
    assert certain_match(1.0, 0.6, OVERSHOOT_SYMMETRIC) == pytest.approx(0.6)
    # 单边策略:超额不扣分
    assert certain_match(1.0, 0.6, OVERSHOOT_ONE_SIDED) == pytest.approx(1.0)
    assert certain_match(0.4, 0.6, OVERSHOOT_ONE_SIDED) == pytest.approx(0.8)


def test_score_to_unit_rejects_out_of_range():
    assert score_to_unit(90.0) == pytest.approx(0.9)
    with pytest.raises(ValueError, match="0~100"):
        score_to_unit(120.0)


# ---------------------------------------------------------------------------
# 2. 模糊型匹配(含与论文数值对照)
# ---------------------------------------------------------------------------


def test_fuzzy_match_reproduces_paper_three_factors():
    """论文中三个因素的 F 值逐一手工核对。

    健康状况(要求"良好"=0.8):0.2×0.8 + 0.5×1.0 + 0.3×0.8 = 0.90
    外在形象(要求"中"=0.6):  0.6×0.8 + 0.4×1.0           = 0.88
    业务水平(要求"优秀"=1.0):0.4×1.0 + 0.5×0.8 + 0.1×0.6 = 0.86
    """
    assert fuzzy_match(PAPER_MEMBERSHIPS["健康状况"], GRADE_VALUES["良好"]) == pytest.approx(0.90)
    assert fuzzy_match(PAPER_MEMBERSHIPS["外在形象"], GRADE_VALUES["中"]) == pytest.approx(0.88)
    assert fuzzy_match(PAPER_MEMBERSHIPS["业务水平"], GRADE_VALUES["优秀"]) == pytest.approx(0.86)


def test_fuzzy_match_degenerate_case_equals_certain():
    """隶属度退化为单点分布时,模糊型必须还原成确定型 —— 两者是同一个式子。"""
    membership = {"优秀": 1.0}
    for required in [0.0, 0.2, 0.6, 0.8, 1.0]:
        assert fuzzy_match(membership, required) == pytest.approx(
            certain_match(1.0, required)
        )


def test_fuzzy_match_accepts_continuous_requirement():
    """M6 方案 A:要求为连续值(如 0.9)时公式依然成立。"""
    membership = {"优秀": 0.5, "良好": 0.5}
    # 0.5×(1-0.1) + 0.5×(1-0.1) = 0.9
    assert fuzzy_match(membership, 0.9) == pytest.approx(0.9)


def test_paper_full_example_reproduces_published_D():
    """复现论文完整算例:F 向量逐项吻合,D = 0.8454。

    F_i = Σ_k r_ik·(1-|v_k - r_i|) 逐因素算出的 9 个值必须与论文印出的
    F=[0.9,0.88,0.86,0.86,0.8,0.82,0.82,0.86,0.76] 完全一致;再按论文的
    AHP 权重加权得到 D=0.8454。
    """
    matches = [
        fuzzy_match(PAPER_MEMBERSHIPS[factor], GRADE_VALUES[PAPER_REQUIRED_GRADES[factor]])
        for factor in PAPER_FACTORS
    ]

    # 9 个 F 值逐项吻合(这是公式正确的直接证据)
    assert matches == pytest.approx(PAPER_EXPECTED_F, abs=1e-9)

    # 严格复现:用论文印出的权重直接加权 = 0.8454
    published_d = sum(w * f for w, f in zip(PAPER_WEIGHTS, matches))
    assert published_d == pytest.approx(0.8454, abs=1e-8)

    # 经 combine_matches(内部会把权重归一化到和为 1)
    # 论文印的权重和为 0.998,归一化后 D 比 0.8454 高约 0.0017,属正常偏差
    dimensions = [
        match_dimension(
            factor,
            student_score=80.0,          # 占位,模糊型不使用学生分值
            required_level=GRADE_VALUES[PAPER_REQUIRED_GRADES[factor]] * 100,
            weight=weight,
            membership=PAPER_MEMBERSHIPS[factor],
        )
        for factor, weight in zip(PAPER_FACTORS, PAPER_WEIGHTS)
    ]
    assert combine_matches(dimensions) == pytest.approx(0.8454, abs=0.002)


def test_normalize_membership():
    assert normalize_membership({"优秀": 2, "良好": 2}) == pytest.approx(
        {"优秀": 0.5, "良好": 0.5, "中": 0.0, "可": 0.0, "差": 0.0, "无": 0.0}
    )
    with pytest.raises(ValueError, match="未知等级"):
        normalize_membership({"很好": 1.0})
    with pytest.raises(ValueError, match="负数"):
        normalize_membership({"优秀": -1.0})
    with pytest.raises(ValueError, match="之和为 0"):
        normalize_membership({"优秀": 0.0})


# ---------------------------------------------------------------------------
# 3. 岗位要求为"无"
# ---------------------------------------------------------------------------


def test_no_requirement_excluded_by_default():
    """岗位要求为 0/None → 该维度权重置 0,既不帮忙也不扣分。"""
    dim = match_dimension("英语能力", student_score=30.0, required_level=0.0, weight=0.5)
    assert dim.no_requirement is True
    assert dim.mode == "excluded"
    assert dim.weight == 0.0
    assert dim.required is None

    # 该维度不参与分母:另一个维度满分,总分仍是满分而不是被 30 分拉低
    other = match_dimension("编程能力", student_score=90.0, required_level=90.0, weight=0.5)
    assert combine_matches([dim, other]) == pytest.approx(1.0)


def test_no_requirement_none_value_excluded():
    dim = match_dimension("英语能力", student_score=None, required_level=None)
    assert dim.no_requirement is True
    assert dim.weight == 0.0


def test_no_requirement_keep_full_policy():
    """另一种策略:该维度记满分并保留权重(会抬高总分,故非默认)。"""
    dim = match_dimension(
        "英语能力", student_score=30.0, required_level=0.0, weight=0.5,
        no_requirement_policy=NO_REQUIREMENT_KEEP_FULL,
    )
    assert dim.match == pytest.approx(1.0)
    assert dim.weight == pytest.approx(0.5)
    assert dim.mode == "no_requirement"


# ---------------------------------------------------------------------------
# 4. 学生数据缺失
# ---------------------------------------------------------------------------


def test_missing_data_scores_zero_and_keeps_weight():
    """默认策略:缺数据记 0 分,但权重保留在分母里。"""
    dim = match_dimension("算法思维", student_score=None, required_level=90.0, weight=0.3)
    assert dim.data_missing is True
    assert dim.match == 0.0
    assert dim.student is None
    assert dim.weight == pytest.approx(0.3)
    assert dim.mode == "missing"


def test_missing_data_does_not_inflate_score():
    """回归测试:数据缺失绝不能被隐式重新归一化变成加分项。

    旧实现用 continue 跳过缺失维度,导致"填得越少、分数越高"。极端情况:
    4 个维度里只有 1 个有数据且满分,旧实现会给出 100% 匹配度。
    """
    specs = [{"dimension": "编程能力", "student_score": 100.0,
              "required_level": 100.0, "weight": 0.25}]
    specs += [
        {"dimension": name, "student_score": None, "required_level": 100.0, "weight": 0.25}
        for name in ("算法思维", "工程实践", "团队协作")
    ]

    result = match_job("测试岗位", specs)

    # 只有 1/4 的权重有数据支撑 → D = 0.25,得分 25 分
    assert result.d_base == pytest.approx(0.25)
    assert result.score == pytest.approx(25.0)
    assert result.score != 100.0
    assert sorted(result.missing_dimensions) == ["团队协作", "工程实践", "算法思维"]

    # 对照:改成"剔除缺失维度"的偏松策略,才会得到满分 —— 这正是要避免的
    loose = match_job("测试岗位", specs, missing_policy=MISSING_EXCLUDE)
    assert loose.score == pytest.approx(100.0)


def test_missing_exclude_policy_renormalizes():
    """偏松策略下缺失维度权重置 0,总分由剩余维度归一化得到。"""
    dim = match_dimension(
        "算法思维", student_score=None, required_level=90.0, weight=0.3,
        missing_policy=MISSING_EXCLUDE,
    )
    assert dim.weight == 0.0
    assert dim.data_missing is True
    assert dim.match == 0.0


# ---------------------------------------------------------------------------
# 5. 综合、门槛与百分制
# ---------------------------------------------------------------------------


def test_combine_matches_normalizes_weights():
    """权重不必手工凑成 1,内部会归一化。"""
    dims = [
        match_dimension("A", student_score=100.0, required_level=100.0, weight=2.0),
        match_dimension("B", student_score=50.0, required_level=100.0, weight=2.0),
    ]
    # A 得 1.0(m=1)、B 得 0.5(m=0.5),等权 → (1.0+0.5)/2 = 0.75
    assert combine_matches(dims) == pytest.approx(0.75)


def test_combine_matches_returns_zero_when_nothing_evaluated():
    dims = [match_dimension("A", student_score=90.0, required_level=0.0, weight=1.0)]
    assert combine_matches(dims) == 0.0


def test_gates_default_off_is_identity():
    assert to_score(0.8454) == pytest.approx(84.5)
    dims = [match_dimension("A", student_score=90.0, required_level=90.0, weight=1.0)]
    with_gates = match_job("岗位", [{"dimension": "A", "student_score": 90.0,
                                     "required_level": 90.0, "weight": 1.0}])
    assert with_gates.d_final == pytest.approx(with_gates.d_base)
    assert with_gates.gate_failed == []
    assert combine_matches(dims) == pytest.approx(1.0)


def test_gate_zero_zeroes_the_score():
    """硬性门槛未达标(0)→ 一票否决,总分归零。"""
    specs = [{"dimension": "编程能力", "student_score": 100.0,
              "required_level": 100.0, "weight": 1.0}]
    result = match_job("后端开发工程师", specs, gates=[0.0])
    assert result.d_base == pytest.approx(1.0)
    assert result.d_final == pytest.approx(0.0)
    assert result.score == pytest.approx(0.0)
    assert result.gate_failed == [0.0]


def test_gate_partial_penalty():
    """门槛系数 0.5 → 总分减半(用于"部分满足"的情形)。"""
    specs = [{"dimension": "编程能力", "student_score": 100.0,
              "required_level": 100.0, "weight": 1.0}]
    result = match_job("岗位", specs, gates=[0.5])
    assert result.score == pytest.approx(50.0)


def test_gate_rejects_out_of_range():
    with pytest.raises(ValueError, match="0~1"):
        match_job("岗位", [{"dimension": "A", "student_score": 90.0,
                            "required_level": 90.0}], gates=[1.5])


def test_match_job_end_to_end_example():
    """端到端示例(合成数据,非真实库数据):4 个维度、含门槛。

    编程能力 85/90 → m = 1-|0.85-0.90| = 0.95,权重 0.4
    算法思维 60/90 → m = 1-|0.60-0.90| = 0.70,权重 0.3
    工程实践 70/70 → m = 1.0,              权重 0.2
    团队协作 缺失  → m = 0,                权重 0.1
    D_base = (0.4×0.95 + 0.3×0.70 + 0.2×1.0 + 0.1×0) / 1.0
           = (0.38 + 0.21 + 0.20 + 0) / 1.0 = 0.79
    """
    specs = [
        {"dimension": "编程能力", "student_score": 85.0, "required_level": 90.0, "weight": 0.4},
        {"dimension": "算法思维", "student_score": 60.0, "required_level": 90.0, "weight": 0.3},
        {"dimension": "工程实践", "student_score": 70.0, "required_level": 70.0, "weight": 0.2},
        {"dimension": "团队协作", "student_score": None, "required_level": 70.0, "weight": 0.1},
    ]
    result = match_job("后端开发工程师", specs)

    assert result.d_base == pytest.approx(0.79)
    assert result.d_final == pytest.approx(0.79)
    assert result.score == pytest.approx(79.0)
    assert result.evaluated_weight == pytest.approx(1.0)
    assert result.missing_dimensions == ["团队协作"]

    by_name = {d.dimension: d for d in result.dimensions}
    assert by_name["编程能力"].match == pytest.approx(0.95)
    assert by_name["算法思维"].match == pytest.approx(0.70)
    assert by_name["工程实践"].match == pytest.approx(1.0)
    assert by_name["团队协作"].mode == "missing"
