"""AHP 权重与一致性检验的单元测试。

其中 test_consistency_ratio_matches_paper 用论文自己给出的 λmax=4.043、CR=0.016
反向验证了 RI 表和 CI/CR 公式,可作为"实现对得上论文"的证据。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from ahp import (
    CR_THRESHOLD,
    RI_TABLE,
    ConsistencyError,
    ahp_weights,
    build_judgment_matrix,
    consistency_ratio,
    require_consistent_weights,
    validate_judgment_matrix,
)


# --- 1. 完全一致的判断矩阵 ------------------------------------------------


def test_perfectly_consistent_matrix():
    """a_ij = w_i/w_j 的矩阵必然完全一致:λmax=n、CI=0、CR=0。"""
    matrix = [
        [1, 2, 4],
        [1 / 2, 1, 2],
        [1 / 4, 1 / 2, 1],
    ]
    result = ahp_weights(matrix)

    assert result.weights == pytest.approx([4 / 7, 2 / 7, 1 / 7], abs=1e-9)
    assert result.lambda_max == pytest.approx(3.0, abs=1e-9)
    assert result.ci == pytest.approx(0.0, abs=1e-9)
    assert result.cr == pytest.approx(0.0, abs=1e-9)
    assert result.consistent is True
    assert result.n == 3


def test_weights_always_sum_to_one_on_nine_factors():
    """9 阶矩阵(论文的因素个数)必须能算出归一化权重,并还原出原始权重。

    用等比数列构造 a_ij = w_i/w_j,最大/最小比恰为 9,落在 Saaty 1~9 标度内。
    """
    q = 9 ** (1 / 8)                          # 相邻两因素的相对重要度
    raw = [q ** (8 - i) for i in range(9)]    # 9 个因素,首尾相差 9 倍
    total = sum(raw)
    target = [value / total for value in raw]

    matrix = [[target[i] / target[j] for j in range(9)] for i in range(9)]
    result = ahp_weights(matrix)

    assert len(result.weights) == 9
    assert sum(result.weights) == pytest.approx(1.0, abs=1e-12)
    assert result.weights == pytest.approx(target, abs=1e-9)
    assert result.lambda_max == pytest.approx(9.0, abs=1e-9)
    assert result.consistent is True


# --- 2. 一致性检验不通过 --------------------------------------------------


def test_cyclic_inconsistent_matrix_rejected():
    """循环矛盾打分(A>B、B>C、C>A)必须被判为不一致并被拒绝。

    该矩阵 A·[1,1,1]ᵀ = 10.1111·[1,1,1]ᵀ,故 λmax = 10.1111 是精确值,
    CI = (10.1111-3)/2 = 3.5556,CR = 3.5556/0.58 = 6.13,远超 0.1。
    """
    matrix = [
        [1, 9, 1 / 9],
        [1 / 9, 1, 9],
        [9, 1 / 9, 1],
    ]
    result = ahp_weights(matrix)

    assert result.lambda_max == pytest.approx(10.1111, abs=1e-4)
    assert result.ci == pytest.approx(3.5556, abs=1e-4)
    assert result.cr == pytest.approx(6.1303, abs=1e-3)
    assert result.consistent is False

    # require_consistent_weights 必须抛错,且错误信息里带 CR 值
    with pytest.raises(ConsistencyError) as excinfo:
        require_consistent_weights(matrix)
    assert "一致性检验不通过" in str(excinfo.value)
    assert "CR" in str(excinfo.value)


def test_require_consistent_weights_passes_when_consistent():
    """一致性达标时返回结果而非抛错。"""
    matrix = [[1, 2, 4], [1 / 2, 1, 2], [1 / 4, 1 / 2, 1]]
    result = require_consistent_weights(matrix)
    assert result.consistent is True


# --- 3. 与论文数值对照 ----------------------------------------------------


def test_consistency_ratio_matches_paper():
    """论文给出 λmax=4.043、n=4 时 CR=0.016,本实现须复现该值。

    CI = (4.043 - 4) / (4 - 1) = 0.01433
    CR = 0.01433 / RI[4] = 0.01433 / 0.90 = 0.0159 ≈ 0.016
    """
    assert consistency_ratio(4.043, 4) == pytest.approx(0.016, abs=5e-4)


def test_ri_table_covers_paper_orders():
    """RI 表必须覆盖论文用到的 1~9 阶,且 RI[4]=0.90(上一条测试依赖它)。"""
    for n in range(1, 10):
        assert n in RI_TABLE
    assert RI_TABLE[4] == 0.90
    assert RI_TABLE[3] == 0.58
    # 阶数越大允许的偏差越大,RI 单调不减
    values = [RI_TABLE[n] for n in range(1, 11)]
    assert values == sorted(values)


def test_two_order_matrix_always_consistent():
    """2 阶矩阵 RI=0,必须返回 CR=0 而不是除零异常。"""
    result = ahp_weights([[1, 5], [1 / 5, 1]])
    assert result.cr == 0.0
    assert result.consistent is True


# --- 4. 入参校验 ----------------------------------------------------------


def test_validate_rejects_non_square():
    with pytest.raises(ValueError, match="方阵"):
        validate_judgment_matrix([[1, 2], [1 / 2, 1], [1 / 3, 3]])


def test_validate_rejects_bad_diagonal():
    with pytest.raises(ValueError, match="对角线"):
        validate_judgment_matrix([[2, 2], [1 / 2, 1]])


def test_validate_rejects_non_positive():
    with pytest.raises(ValueError, match="正数"):
        validate_judgment_matrix([[1, -2], [-1 / 2, 1]])


def test_validate_rejects_non_reciprocal():
    with pytest.raises(ValueError, match="互反"):
        validate_judgment_matrix([[1, 3], [1 / 5, 1]])


def test_build_judgment_matrix_fills_reciprocal():
    """只给上三角打分,下三角自动取倒数。"""
    matrix = build_judgment_matrix(3, [(0, 1, 2), (0, 2, 4), (1, 2, 2)])
    assert matrix == [[1, 2, 4], [1 / 2, 1, 2], [1 / 4, 1 / 2, 1]]


def test_build_judgment_matrix_rejects_incomplete():
    with pytest.raises(ValueError, match="不完整"):
        build_judgment_matrix(3, [(0, 1, 2)])


def test_build_judgment_matrix_rejects_diagonal():
    with pytest.raises(ValueError, match="对角线"):
        build_judgment_matrix(3, [(0, 0, 5)])
