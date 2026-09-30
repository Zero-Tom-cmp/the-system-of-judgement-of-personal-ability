# -*- coding: utf-8 -*-
"""能力分归一化 —— 纯函数模块,不读数据库、不依赖 FastAPI。

修正的是 evaluation.evaluate_student_abilities 末尾这段:

    base_score     = min(100, max(0, round(raw * 100 / 50)))          # 除数 50 无依据
    weighted_score = min(100, max(0, round(base_score * weight * (1/0.2))))  # 权重乘了第二遍

两处错误:

  1. **除数 50 是拍脑袋的**。课程贡献的结构上界是 40 —— 见 _eval_courses:
     每门课贡献 (score/100)·weight·credit_weight·40,而 credit_weight 由
     total_credit 归一化,Σcredit_weight = 1,故单维度从课程最多拿到 40。
     实测全体学生 raw 中位仅 18.1,除以 50 后得分被系统性压在 30~50 区间。

  2. **再乘 weight×(1/0.2) 等于把权重算了第二遍**。专业能力权重在这里乘一次,
     match_jobs 里还会再乘一次岗位 importance_weight;而且 weight < 0.2 的维度
     被硬性封顶在 50 分(weight=0.10 → 100×0.10×5 = 50),结构上不可能及格。
     "沟通表达 4 分"就是这么来的:raw 3.8 → ÷50 → 8 分 → ×0.10×5 → 4 分,
     没有任何一步在表达"这个学生沟通能力差"。

修正后:

    s = min(1, raw / REFERENCE_RAW)

能力分只表达"该维度能力有多强",**不带任何权重**。权重统一交给匹配度公式里的
e_i(见 match_score.combine_matches),一个概念只出现一次。
"""

from typing import Dict, Optional

#: raw 的参考上界。取课程贡献的结构上界 40,含义是"课程全满 + 无额外加分 = 满分"。
#: 竞赛/实习/项目会在此基础上继续加分,故超额直接封顶到 1.0(即"达到优秀水平")。
DEFAULT_REFERENCE_RAW = 40.0

#: 分维度参考值覆盖(留空表示全部使用 DEFAULT_REFERENCE_RAW)。
#: 若将来发现某维度的数据源结构性地给不出足够 raw(如沟通表达、英语能力几乎
#: 没有课程映射),应优先补数据源,而不是在这里调小参考值把分数"抬"上去。
REFERENCE_RAW_BY_DIM: Dict[str, float] = {}


class NormalizationError(ValueError):
    """归一化入参非法。"""


def clamp01(value: float) -> float:
    """把数值截断到 [0,1]。"""
    return max(0.0, min(1.0, float(value)))


def reference_for(dimension: Optional[str] = None) -> float:
    """取某个维度的 raw 参考上界。"""
    if dimension is not None and dimension in REFERENCE_RAW_BY_DIM:
        return float(REFERENCE_RAW_BY_DIM[dimension])
    return DEFAULT_REFERENCE_RAW


def normalize_ability(
    raw: float,
    dimension: Optional[str] = None,
    reference: Optional[float] = None,
) -> float:
    """把原始贡献分 raw 归一化到 [0,1]。

    raw 为非负数;超过参考上界时封顶到 1.0,表示"已达到优秀水平"。
    """
    value = float(raw)
    if value < 0:
        raise NormalizationError(f"原始贡献分不能为负数:{raw}")

    ref = float(reference) if reference is not None else reference_for(dimension)
    if ref <= 0:
        raise NormalizationError(f"参考上界必须为正数:{ref}")

    return clamp01(value / ref)


def ability_score_100(
    raw: float,
    dimension: Optional[str] = None,
    reference: Optional[float] = None,
    digits: int = 1,
) -> float:
    """归一化后的百分制展示分(0~100)。"""
    return round(100.0 * normalize_ability(raw, dimension, reference), digits)


def normalize_abilities(raw_by_dimension: Dict[str, float]) -> Dict[str, float]:
    """批量归一化 {维度: raw} -> {维度: 0~1}。"""
    return {
        dimension: normalize_ability(raw, dimension)
        for dimension, raw in raw_by_dimension.items()
    }
