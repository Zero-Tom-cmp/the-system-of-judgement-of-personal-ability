import { useState } from "react";
import { Card, Progress, Tag, Collapse, Alert } from "antd";
import {
  TrophyOutlined,
  BulbOutlined,
  WarningOutlined,
} from "@ant-design/icons";

export default function JobMatchPanel({ matches }) {
  const [expandedJob, setExpandedJob] = useState(null);

  if (!matches || matches.length === 0) return null;

  const getColor = (rate) => {
    if (rate >= 85) return "#52c41a";
    if (rate >= 70) return "#1890ff";
    if (rate >= 50) return "#faad14";
    return "#ff4d4f";
  };

  const topJob = matches[0];
  const otherJobs = matches.slice(1);

  return (
    <div>
      {/* 最匹配岗位 - 突出显示 */}
      <Card
        className="job-card selected"
        size="small"
        style={{ marginBottom: 16, borderColor: "#1890ff" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <TrophyOutlined style={{ color: "#faad14", marginRight: 8 }} />
            <span style={{ fontWeight: "bold", fontSize: 16 }}>{topJob.job_name}</span>
            <Tag color="blue" style={{ marginLeft: 8 }}>最佳匹配</Tag>
          </div>
          <span style={{ fontSize: 24, fontWeight: "bold", color: getColor(topJob.overall_match) }}>
            {topJob.overall_match}%
          </span>
        </div>
        <Progress
          percent={topJob.overall_match}
          strokeColor={getColor(topJob.overall_match)}
          style={{ marginTop: 8 }}
        />

        {/* 维度匹配明细 */}
        <div style={{ marginTop: 12 }}>
          {topJob.dim_matches.map((dm) => (
            <div key={dm.dimension} style={{ display: "flex", alignItems: "center", marginBottom: 6 }}>
              <span style={{ width: 80, fontSize: 13 }}>{dm.dimension}</span>
              <Progress
                percent={dm.match_rate}
                size="small"
                strokeColor={getColor(dm.match_rate)}
                style={{ flex: 1, margin: "0 8px" }}
              />
              <span style={{ width: 100, fontSize: 12, color: "#888" }}>
                {dm.student_score}/{dm.required}分
              </span>
            </div>
          ))}
        </div>

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
                    （差距 {gap.gap} 分）
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
                      {job.overall_match}%
                    </span>
                  </div>
                  <Progress percent={job.overall_match} strokeColor={getColor(job.overall_match)} size="small" />
                  {job.gaps.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      {job.gaps.map((gap) => (
                        <Tag key={gap.dimension} color="orange" className="gap-tag">
                          {gap.dimension}: +{gap.gap}分
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
