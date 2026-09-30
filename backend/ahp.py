# -*- coding: utf-8 -*-
"""AHP(层次分析法)权重计算 —— 纯函数模块,不读数据库、不依赖 FastAPI。

对应论文《基于AHP-模糊综合评价的人才岗位匹配度测算》中的式(4)~(8):

    (4) 构造判断矩阵   A = (a_ij),a_ij 取 1~9 及其倒数
    (5) 方根法求权重   w_i = (Π_j a_ij)^(1/n) / Σ_k (Π_j a_kj)^(1/n)
    (6) 最大特征根     λmax = (1/n) · Σ_i (Aw)_i / w_i
    (7) 一致性指标     CI = (λmax - n) / (n - 1)
    (8) 一致性比率     CR = CI / RI,CR < 0.1 认为通过一致性检验

之所以要把这块单独拆出来:判断矩阵的打分是主观的,唯一能自证可信的手段就是
一致性检验。把它做成纯函数,既能单测,也能在接入前先验证权重是否可用。

用 RI[4]=0.90 反算论文自己给的 λmax=4.043、CR=0.016:CI=(4.043-4)/3=0.0143,
CR=0.0143/0.90=0.0159≈0.016,与论文一致 —— 见 test_ahp.py 的对照测试。
"""

import math
from typing import List, NamedTuple, Sequence, Tuple

#: Saaty 随机一致性指标 RI(阶数 1~10),论文式(8)使用
RI_TABLE = {
    1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
}

#: 一致性比率阈值,论文取 0.1
CR_THRESHOLD = 0.1

#: 判断矩阵的容差。互反性放到 1e-3 是为了容忍 a_ij 被写成 0.333 这种三位小数
DIAGONAL_TOL = 1e-6
RECIPROCAL_TOL = 1e-3


class ConsistencyError(ValueError):
    """判断矩阵一致性检验不通过(CR >= 阈值)。

    继承 ValueError,调用方既可以精确捕获它给出"请调整打分"的提示,
    也可以像处理普通入参错误一样统一兜底。
    """


class AHPResult(NamedTuple):
    """一次 AHP 计算的完整结果。"""

    weights: List[float]      # 归一化权重,和为 1
    lambda_max: float         # 最大特征根
    ci: float                 # 一致性指标 CI
    cr: float                 # 一致性比率 CR
    consistent: bool          # CR < CR_THRESHOLD
    n: int                    # 判断矩阵阶数


def consistency_index(lambda_max: float, n: int) -> float:
    """CI = (λmax - n) / (n - 1)。

    论文式(7)。n <= 2 时矩阵恒为一致,分母为 0,直接返回 0。
    """
    if n <= 2:
        return 0.0
    return (float(lambda_max) - n) / (n - 1)


def consistency_ratio(lambda_max: float, n: int) -> float:
    """CR = CI / RI。

    论文式(8)。RI 为 0(阶数 <= 2)时矩阵恒为一致,直接返回 0,避免除零。
    """
    ri = RI_TABLE.get(n)
    if ri is None:
        raise ValueError(f"不支持 {n} 阶判断矩阵(RI 表仅覆盖 1~10 阶)")
    if ri == 0.0:
        return 0.0
    return consistency_index(lambda_max, n) / ri


def validate_judgment_matrix(matrix: Sequence[Sequence[float]]) -> int:
    """校验判断矩阵是否合法,合法则返回阶数 n。

    检查四项:非空方阵、对角线为 1、元素为正、满足互反性(a_ij · a_ji = 1)。
    任何一项不满足都抛 ValueError,并指明具体位置,便于调用方定位打分错误。
    """
    if not matrix:
        raise ValueError("判断矩阵不能为空")

    n = len(matrix)
    for i, row in enumerate(matrix):
        if len(row) != n:
            raise ValueError(f"判断矩阵必须是方阵:第 {i} 行长度为 {len(row)},期望 {n}")

    for i in range(n):
        diagonal = float(matrix[i][i])
        if abs(diagonal - 1.0) > DIAGONAL_TOL:
            raise ValueError(f"判断矩阵对角线必须为 1:a[{i}][{i}] = {diagonal}")
        for j in range(n):
            value = float(matrix[i][j])
            if value <= 0:
                raise ValueError(f"判断矩阵元素必须为正数:a[{i}][{j}] = {value}")
            product = value * float(matrix[j][i])
            if abs(product - 1.0) > RECIPROCAL_TOL:
                raise ValueError(
                    f"判断矩阵必须满足互反性:a[{i}][{j}]={value} 与 "
                    f"a[{j}][{i}]={matrix[j][i]} 的乘积为 {product:.6f},应为 1"
                )
    return n


def ahp_weights(matrix: Sequence[Sequence[float]]) -> AHPResult:
    """方根法计算 AHP 权重,并给出 λmax / CI / CR。

    与 require_consistent_weights 的区别:本函数**不因 CR 不达标而抛错**,
    而是把 consistent=False 放在结果里返回。适合"想先看看权重长什么样、
    再决定要不要调整打分"的探索场景。
    """
    n = validate_judgment_matrix(matrix)

    # 式(5):每行元素的几何平均,再归一化
    roots = [math.prod(float(v) for v in row) ** (1.0 / n) for row in matrix]
    total = sum(roots)
    if total <= 0:
        raise ValueError("判断矩阵各行几何平均之和为 0,无法归一化")
    weights = [root / total for root in roots]

    # 式(6):λmax = (1/n) Σ (Aw)_i / w_i
    lambda_max = 0.0
    for i in range(n):
        aw_i = sum(float(matrix[i][j]) * weights[j] for j in range(n))
        lambda_max += aw_i / weights[i]
    lambda_max /= n

    ci = consistency_index(lambda_max, n)
    cr = consistency_ratio(lambda_max, n)
    return AHPResult(
        weights=weights,
        lambda_max=lambda_max,
        ci=ci,
        cr=cr,
        consistent=cr < CR_THRESHOLD,
        n=n,
    )


def require_consistent_weights(
    matrix: Sequence[Sequence[float]], threshold: float = CR_THRESHOLD
) -> AHPResult:
    """同 ahp_weights,但 CR >= threshold 时抛 ConsistencyError。

    用于"权重必须可信才能上线"的场景 —— 一致性和不通过的权重意味着打分自相矛盾
    (例如 A 比 B 重要、B 比 C 重要,却又说 C 比 A 重要),此时算出来的权重没有意义。
    """
    result = ahp_weights(matrix)
    if result.cr >= threshold:
        raise ConsistencyError(
            f"判断矩阵一致性检验不通过:CR = {result.cr:.4f} >= {threshold}"
            f"(λmax = {result.lambda_max:.4f},CI = {result.ci:.4f},n = {result.n})。"
            f"请检查打分中相互矛盾之处,例如 A>B、B>C 却给出 C>A。"
        )
    return result


def build_judgment_matrix(n: int, comparisons: Sequence[Tuple[int, int, float]]):
    """由 (行下标, 列下标, 1~9 标度) 三元组构造互反判断矩阵。

    只需给出上三角(或任意一侧)的打分,另一侧自动取倒数,避免手写 1/3、1/5
    这类分数时写错方向。下标从 0 开始。

    例:build_judgment_matrix(3, [(0, 1, 2), (0, 2, 4), (1, 2, 2)])
        -> [[1, 2, 4], [1/2, 1, 2], [1/4, 1/2, 1]]
    """
    if n < 1:
        raise ValueError(f"判断矩阵阶数必须为正整数,当前为 {n}")

    matrix = [[1.0 if i == j else None for j in range(n)] for i in range(n)]
    for i, j, value in comparisons:
        if not (0 <= i < n and 0 <= j < n):
            raise ValueError(f"下标越界:({i}, {j}) 超出 {n} 阶矩阵")
        if i == j:
            raise ValueError(f"对角线元素不可指定:({i}, {j}),其值恒为 1")
        scale = float(value)
        if scale <= 0:
            raise ValueError(f"标度必须为正数:({i}, {j}) = {value}")
        matrix[i][j] = scale
        matrix[j][i] = 1.0 / scale

    for i in range(n):
        for j in range(n):
            if matrix[i][j] is None:
                raise ValueError(f"判断矩阵不完整,缺少元素 ({i}, {j}) 的打分")
    return matrix
