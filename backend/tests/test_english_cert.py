"""英语证书换算与贡献的单元测试。

背景(这是加这个字段的理由,不是锦上添花):英语能力原先只有"课程 + 英语竞赛"
两个来源,而课程贡献 = (score/100)·w·credit_weight·40 里的 credit_weight
分母是**全专业课程总学分**,所以被摊薄得只剩零头。实测该维度的结构上界只有
40 分的 36%~44% —— 一个课程全考 100 分、拿到国家级特等奖的学生也够不着及格线。
证书像竞赛一样是**绝对分**来源,不受学分摊薄影响,补的正是这个缺口。

核心回归测试:
  - test_cert_raises_the_dimension_ceiling —— 课程满分仍不及格,加证书后及格
  - test_no_cert_leaves_score_unchanged   —— 没填证书的学生分数一分不变
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import database
from database import init_db
from evaluation import (
    ENGLISH_CERT_LEVELS, ENGLISH_CERT_MAX, ENGLISH_CERT_MAX_SCORE,
    english_cert_level, evaluate_student_abilities,
)

ZHAOLIU = "2021004"   # 金融学
ZHANGSAN = "2021001"  # 软件工程（没有"英语能力"维度）


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """建一个全新的库（含种子数据），返回连接。"""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    init_db()
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# --- 1. 换算函数（纯函数，不碰数据库）-------------------------------------


def test_each_cert_picks_the_highest_reached_tier():
    """取"不超过该分数的最高档"，而不是第一档。"""
    assert english_cert_level("CET4", 425) == pytest.approx(0.40)
    assert english_cert_level("CET4", 610) == pytest.approx(0.60)   # 不是 0.40
    assert english_cert_level("CET6", 505) == pytest.approx(0.70)
    assert english_cert_level("IELTS", 7.2) == pytest.approx(0.80)
    assert english_cert_level("TOEFL", 115) == pytest.approx(0.90)


def test_level_is_monotonic_inside_each_cert():
    """同一证书内，分数越高等级权重不降。"""
    for cert, thresholds in ENGLISH_CERT_LEVELS.items():
        low, high = min(t for t, _ in thresholds), max(t for t, _ in thresholds)
        assert english_cert_level(cert, low) <= english_cert_level(cert, high)


def test_below_lowest_threshold_gives_no_contribution():
    """低于最低档不算"0 分贡献"，而是"没有贡献"，两者在展示上不同。"""
    assert english_cert_level("CET4", 424) is None
    assert english_cert_level("IELTS", 5.5) is None


def test_empty_or_unknown_cert_gives_no_contribution():
    assert english_cert_level(None, 500) is None
    assert english_cert_level("", 500) is None
    assert english_cert_level("CET6", None) is None
    assert english_cert_level("GRE", 320) is None      # 不在支持列表内


def test_cert_type_is_case_and_space_insensitive():
    assert english_cert_level(" ielts ", 6.5) == english_cert_level("IELTS", 6.5)
    assert english_cert_level("cet6", 500) == english_cert_level("CET6", 500)


def test_max_score_table_covers_every_cert():
    """校验用的分数上限表必须覆盖所有证书，否则接口校验会 KeyError。"""
    assert set(ENGLISH_CERT_MAX_SCORE) == set(ENGLISH_CERT_LEVELS)


# --- 2. 贡献进入评分 ------------------------------------------------------


def test_cert_contributes_to_english_dimension(seeded_db):
    cur = seeded_db.cursor()
    cur.execute(
        "UPDATE students SET english_cert='CET6', english_score=530 WHERE student_id=?",
        (ZHAOLIU,))
    ability = evaluate_student_abilities(cur, ZHAOLIU)["abilities"]["英语能力"]

    # 六级 530 落在 500 档 → 0.70 × 15 = 10.5
    assert 0.70 * ENGLISH_CERT_MAX == pytest.approx(10.5)
    assert ability["raw"] >= 10.5
    assert any("英语证书" in d["source"] for d in ability["details"])


def test_cert_contribution_is_not_diluted_by_credit_weight(seeded_db):
    """证书贡献是固定值，不受课程门数/学分影响——这正是它相对课程贡献的价值。

    两门课 vs 十二门课的学生，同一张证书拿到的分必须一样。
    """
    cur = seeded_db.cursor()
    cur.execute(
        "UPDATE students SET english_cert='IELTS', english_score=6.5 WHERE student_id IN (?,?)",
        (ZHAOLIU, "2021005"))

    def cert_part(sid):
        details = evaluate_student_abilities(cur, sid)["abilities"]["英语能力"]["details"]
        cert = [d for d in details if "英语证书" in d["source"]]
        return sum(d["value"] for d in cert)

    # 赵六 12 门课、孙七 10 门课，证书贡献必须相同
    assert cert_part(ZHAOLIU) == pytest.approx(cert_part("2021005"))


def test_software_major_ignores_cert(seeded_db):
    """软件工程的能力配置里没有"英语能力"维度，证书应被静默忽略、不报错。"""
    cur = seeded_db.cursor()
    before = evaluate_student_abilities(cur, ZHANGSAN)["abilities"]
    cur.execute(
        "UPDATE students SET english_cert='IELTS', english_score=8.0 WHERE student_id=?",
        (ZHANGSAN,))
    after = evaluate_student_abilities(cur, ZHANGSAN)["abilities"]

    assert "英语能力" not in after
    assert {d: v["raw"] for d, v in before.items()} == {d: v["raw"] for d, v in after.items()}


def test_no_cert_leaves_score_unchanged(seeded_db):
    """没填证书的学生分数一分不变——不能因为加了字段就把所有人重算一遍。"""
    cur = seeded_db.cursor()
    cur.execute("UPDATE students SET english_cert=NULL, english_score=NULL WHERE student_id=?", (ZHAOLIU,))
    without = evaluate_student_abilities(cur, ZHAOLIU)["abilities"]["英语能力"]

    # 与"证书字段完全不存在"时一致：raw 只来自课程，没有证书明细
    assert not any("英语证书" in d["source"] for d in without["details"])


# --- 3. 关键回归：证书把维度上限拉回及格线 --------------------------------


def test_cert_raises_the_dimension_ceiling(seeded_db):
    """课程全考 100 分仍然不及格；加上一张证书才够得着。

    这条测试固化了"加这个字段的理由"——如果哪天有人把 credit_weight 的分母
    改成按维度归一化，这条会失败，提醒重新评估证书是否还有必要。
    """
    cur = seeded_db.cursor()
    cur.execute("UPDATE students SET english_cert=NULL, english_score=NULL WHERE student_id=?", (ZHAOLIU,))
    cur.execute(
        "UPDATE courses SET score=100 WHERE student_id=? AND course_name IN ('大学英语','金融英语','国际金融')",
        (ZHAOLIU,))
    perfect_courses = evaluate_student_abilities(cur, ZHAOLIU)["abilities"]["英语能力"]
    assert perfect_courses["score"] < 50, "英语课程全满分却仍不及格，说明上限被学分摊薄压住了"

    cur.execute("UPDATE students SET english_cert='IELTS', english_score=9.0 WHERE student_id=?", (ZHAOLIU,))
    with_cert = evaluate_student_abilities(cur, ZHAOLIU)["abilities"]["英语能力"]
    assert with_cert["score"] > perfect_courses["score"] + 20
