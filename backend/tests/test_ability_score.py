"""能力分归一化的单元测试。

重点是两个回归测试:
  - test_low_weight_dimension_no_longer_capped  —— 修掉"权重<0.2 的维度封顶 50 分"
  - test_normalization_ignores_professional_weight —— 权重不再被计入能力分
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import ability_score
from ability_score import (
    DEFAULT_REFERENCE_RAW,
    NormalizationError,
    ability_score_100,
    normalize_ability,
    normalize_abilities,
    reference_for,
)


# --- 1. 归一化基本行为 ----------------------------------------------------


def test_normalize_uses_structural_reference():
    """参考上界取课程贡献的结构上界 40。"""
    assert DEFAULT_REFERENCE_RAW == 40.0
    assert normalize_ability(0.0) == pytest.approx(0.0)
    assert normalize_ability(20.0) == pytest.approx(0.5)
    assert normalize_ability(40.0) == pytest.approx(1.0)


def test_reference_is_the_course_structural_bound():
    """40 不是拍脑袋来的:_eval_courses 里 Σcredit_weight = 1,
    单维度从课程最多拿 (100/100)·1·1·40 = 40。"""
    # 课程满分情形:每门课 score=100、映射权重 1.0,学分权重合计 1
    raw = sum(1.0 * 1.0 * credit_weight * 40 for credit_weight in (0.3, 0.3, 0.4))
    assert raw == pytest.approx(DEFAULT_REFERENCE_RAW)


def test_over_reference_caps_at_one():
    """竞赛/实习/项目会在课程之上继续加分,超出参考值时封顶到 1.0。"""
    assert normalize_ability(60.0) == pytest.approx(1.0)
    assert ability_score_100(999.0) == pytest.approx(100.0)


def test_normalize_rejects_bad_input():
    with pytest.raises(NormalizationError, match="负数"):
        normalize_ability(-1.0)
    with pytest.raises(NormalizationError, match="正数"):
        normalize_ability(10.0, reference=0.0)


def test_score_100_rounding():
    assert ability_score_100(26.2) == pytest.approx(65.5)
    assert ability_score_100(3.8) == pytest.approx(9.5)


def test_normalize_abilities_batch():
    result = normalize_abilities({"编程能力": 40.0, "沟通表达": 20.0})
    assert result == pytest.approx({"编程能力": 1.0, "沟通表达": 0.5})


# --- 2. 分维度覆盖 --------------------------------------------------------


def test_per_dimension_reference_override(monkeypatch):
    """预留的分维度参考值生效,且不影响其他维度。"""
    monkeypatch.setitem(ability_score.REFERENCE_RAW_BY_DIM, "英语能力", 20.0)
    assert reference_for("英语能力") == 20.0
    assert reference_for("编程能力") == DEFAULT_REFERENCE_RAW
    assert normalize_ability(10.0, "英语能力") == pytest.approx(0.5)
    assert normalize_ability(10.0, "编程能力") == pytest.approx(0.25)


# --- 3. 回归测试:修掉旧公式的两个错误 ------------------------------------


def test_low_weight_dimension_no_longer_capped():
    """回归:旧公式下权重 0.10 的维度上限只有 50 分,新公式没有这个封顶。

    旧公式 weighted_score = base × weight × (1/0.2),weight=0.10 时
    即使 base 满分 100,也只能得到 100×0.10×5 = 50 分 —— "沟通表达"
    "学习能力""英语能力"三个维度因此结构上不可能及格。
    """
    weight = 0.10
    old_cap = min(100, round(100 * weight * (1 / 0.2)))
    assert old_cap == 50  # 记录旧公式的封顶

    # 新公式:raw=30(参考值 40 的 75%)直接得 75 分,越过旧的 50 分上限
    assert ability_score_100(30.0, "沟通表达") == pytest.approx(75.0)
    assert ability_score_100(30.0, "沟通表达") > old_cap


def test_normalization_ignores_professional_weight():
    """回归:权重不再进入能力分,同一个 raw 在任何维度都得同一个分。

    旧公式把 ability_config.weight 乘进了能力分,match_jobs 里又乘了一次
    importance_weight —— 同一个概念扣两遍。现在能力分只表达能力本身,
    权重只由匹配度的 e_i 承担。
    """
    raw = 24.0
    scores = {dim: ability_score_100(raw, dim) for dim in
              ("编程能力", "算法思维", "团队协作", "沟通表达", "英语能力")}
    assert len(set(scores.values())) == 1
    assert scores["沟通表达"] == pytest.approx(60.0)
