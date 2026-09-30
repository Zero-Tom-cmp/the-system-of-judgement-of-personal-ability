import { Card, Progress, Tag, Collapse, Alert, Empty } from "antd";
import {
  TrophyOutlined,
  BulbOutlined,
  WarningOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";

// 维度行的列宽。四列并排后进度条只剩 flex 的余量，故定宽列尽量收紧。
const COL = { dim: 68, pair: 88, gap: 86, rate: 52 };

// 后端返回的是保留一位小数的数值，但 40.0 经 JS 序列化后变成 40，
// 同一列里就会混出「40 / 60」和「69.7 / 75」两种小数位。统一补齐。
const fixed = (v) => Number(v).toFixed(1);

/**
 * 把「要求 − 能力」翻译成一行可读文案。
 *
 * 差距用后端给的 student_score / required 直接相减（均为 0~100 口径），
 * 不依赖 match_rate —— 这样「超出」和「差」在数字上是对称的，学生能直接
 * 看出「超出 18.2 分」与「差 18.2 分」扣掉的是同样的分。
 *
 * 「超出」刻意用橙色而非绿色：这里衡量的是"离岗位要求有多近"，高出要求和
 * 达不到要求一样算偏离、扣一样的分。涂成绿色会让学生以为超额能加分。
 */
function describeGap(dm) {
  if (dm.data_missing) return { text: "无数据", color: "#999" };
  if (dm.no_requirement) return { text: "岗位不要求", color: "#999" };

  const { student_score: s, required: r } = dm;
  if (s == null || r == null) return { text: "—", color: "#999" };

  const gap = Math.round((r - s) * 10) / 10;
  if (gap > 0) return { text: `差 ${gap} 分`, color: "#cf1322" };
  if (gap < 0) return { text: `超出 ${Math.abs(gap)} 分`, color: "#d46b08" };
  return { text: "刚好达标", color: "#52c41a" };
}

export default function JobMatchPanel({ matches }) {
  if (!matches || matches.length === 0) {
    return <Empty description="暂无课程、竞赛、实习或项目数据，无法进行岗位匹配评估" />;
  }

  const getColor = (rate) => {
    if (rate >= 85) return "#52c41a";
    if (rate >= 70) return "#1890ff";
    if (rate >= 50) return "#faad14";
    return "#ff4d4f";
  };

  const topJob = matches[0];
  const otherJobs = matches.slice(1);

  const dims = topJob.dim_matches;
  const missingDims = topJob.missing_dimensions || [];
  const d = (v) => Math.round(v * 10) / 10;

  // 加权平均差距 = 100 − 匹配得分。这不是巧合：每个维度都是按"要求与能力的
  // 距离"计分，各维度加权汇总后，被扣掉的那部分恰好就是加权的平均差距。
  // 但若有维度数据缺失（后端按最差情况计入，相当于记了满值差距），
  // 这个数就不再是「能力差距」了，此时不显示，改由缺失提示单独说明。
  const gapTotal = d(100 - topJob.overall_match);

  const overDims = dims
    .filter(
      (dm) =>
        !dm.data_missing &&
        !dm.no_requirement &&
        dm.student_score != null &&
        dm.required != null &&
        dm.student_score > dm.required
    )
    .map((dm) => ({ dimension: dm.dimension, amount: d(dm.student_score - dm.required) }));

  // 维度行是否参与匹配度计算：岗位不要求和数据缺失都不参与
  const isEvaluated = (dm) => !dm.data_missing && !dm.no_requirement;

  const renderDimRow = (dm) => {
    const gap = describeGap(dm);
    const evaluated = isEvaluated(dm);
    return (
      <div key={dm.dimension} style={{ display: "flex", alignItems: "center", marginBottom: 6 }}>
        <span style={{ width: COL.dim, fontSize: 13, color: evaluated ? undefined : "#999" }}>
          {dm.dimension}
        </span>
        {evaluated ? (
          <Progress
            percent={dm.match_rate}
            size="small"
            strokeColor={getColor(dm.match_rate)}
            style={{ flex: 1, margin: "0 8px" }}
          />
        ) : (
          <span style={{ flex: 1, margin: "0 8px", fontSize: 12, color: "#bbb" }}>
            {dm.no_requirement ? "本岗位不考察该维度" : "缺少数据，已按 0 分计入"}
          </span>
        )}
        <span style={{ width: COL.pair, fontSize: 12, color: "#888", textAlign: "right" }}>
          {evaluated ? `${fixed(dm.student_score)} / ${fixed(dm.required)}` : "—"}
        </span>
        <span style={{ width: COL.gap, fontSize: 12, color: gap.color, textAlign: "right" }}>
          {gap.text}
        </span>
        <span style={{ width: COL.rate, fontSize: 12, color: "#888", textAlign: "right" }}>
          {evaluated ? `${fixed(dm.match_rate)}%` : "—"}
        </span>
      </div>
    );
  };

  return (
    <div>
      {/* 最匹配岗位 - 突出显示 */}
      <Card
        className="job-card selected"
        size="small"
        style={{ marginBottom: 16, borderColor: "#1890ff" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <TrophyOutlined style={{ color: "#faad14", marginRight: 8 }} />
            <span style={{ fontWeight: "bold", fontSize: 16 }}>{topJob.job_name}</span>
            <Tag color="blue" style={{ marginLeft: 8 }}>最佳匹配</Tag>
          </div>
          <div style={{ textAlign: "right" }}>
            <div>
              <span style={{ fontSize: 12, color: "#888" }}>匹配得分 </span>
              <span style={{ fontSize: 24, fontWeight: "bold", color: getColor(topJob.overall_match) }}>
                {topJob.overall_match}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "#888" }}>
              {missingDims.length > 0
                ? `${missingDims.length} 个维度无数据，已按 0 分计入`
                : `加权平均差距 ${gapTotal} 分`}
            </div>
          </div>
        </div>
        <Progress
          percent={topJob.overall_match}
          strokeColor={getColor(topJob.overall_match)}
          style={{ marginTop: 8 }}
        />

        {/* 维度匹配明细 */}
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "flex", marginBottom: 4, fontSize: 11, color: "#999" }}>
            <span style={{ width: COL.dim }}>维度</span>
            <span style={{ flex: 1, margin: "0 8px" }} />
            <span style={{ width: COL.pair, textAlign: "right" }}>能力 / 要求</span>
            <span style={{ width: COL.gap, textAlign: "right" }}>差距</span>
            <span style={{ width: COL.rate, textAlign: "right" }}>匹配度</span>
          </div>
          {dims.map(renderDimRow)}
        </div>

        {/* 超额达标说明：超出和不足都算偏离要求，不解释的话学生会以为是算错了 */}
        {overDims.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 12, color: "#d46b08" }}>
            <InfoCircleOutlined style={{ marginRight: 4 }} />
            超出要求同样算差距：
            {overDims.map((o) => `${o.dimension} 超出 ${o.amount} 分`).join("、")}
            。这里看的是你和岗位要求的接近程度——高出和不足都算偏离，扣分一样，
            所以超出并不会把匹配度拉满。
          </div>
        )}

        {/* 数据缺失提示 */}
        {missingDims.length > 0 && (
          <Alert
            type="info"
            message={`本岗位 ${dims.length} 个维度中有 ${missingDims.length} 个你缺少数据（${missingDims.join("、")}）`}
            description="这些维度已按 0 分计入总分——没证据不等于达标，因此会拉低匹配得分。补充对应的课程、竞赛、实习或项目经历即可改善。"
            style={{ marginTop: 12 }}
          />
        )}

        {/* 差距分析 */}
        {topJob.gaps.length > 0 && (
          <Alert
            type="warning"
            icon={<WarningOutlined />}
            message="能力差距分析"
            description={
              <div>
                {topJob.gaps.map((gap) => (
                  <div key={gap.dimension} style={{ marginBottom: 6 }}>
                    <Tag color="orange">{gap.dimension}</Tag>
                    当前 <b>{gap.current}</b> 分，目标 <b>{gap.required}</b> 分
                    （{gap.gap >= 0 ? `差 ${gap.gap} 分` : `超出 ${Math.abs(gap.gap)} 分`}）
                    <div style={{ color: "#666", fontSize: 12, marginTop: 2 }}>
                      <BulbOutlined /> {gap.suggestion}
                    </div>
                  </div>
                ))}
              </div>
            }
            style={{ marginTop: 12 }}
          />
        )}
      </Card>

      {/* 其他匹配岗位 */}
      {otherJobs.length > 0 && (
        <Collapse
          items={[
            {
              key: "other",
              label: `其他岗位匹配结果 (${otherJobs.length}个)`,
              children: otherJobs.map((job) => (
                <Card key={job.job_name} className="job-card" size="small" style={{ marginBottom: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: "bold" }}>{job.job_name}</span>
                    <span style={{ fontSize: 18, fontWeight: "bold", color: getColor(job.overall_match) }}>
                      {job.overall_match} 分
                    </span>
                  </div>
                  <Progress percent={job.overall_match} strokeColor={getColor(job.overall_match)} size="small" />
                  {job.gaps.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      {job.gaps.map((gap) => (
                        <Tag
                          key={gap.dimension}
                          color={gap.gap >= 0 ? "orange" : "volcano"}
                          className="gap-tag"
                        >
                          {gap.dimension}:{" "}
                          {gap.gap >= 0 ? `差 ${gap.gap} 分` : `超出 ${Math.abs(gap.gap)} 分`}
                        </Tag>
                      ))}
                    </div>
                  )}
                </Card>
              )),
            },
          ]}
        />
      )}
    </div>
  );
}
