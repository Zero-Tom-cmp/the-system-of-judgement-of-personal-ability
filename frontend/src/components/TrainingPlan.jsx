import { useEffect, useState, useMemo } from "react";
import { Card, Descriptions, Tag, Table, Spin, Empty } from "antd";
import { BookOutlined } from "@ant-design/icons";
import { getTrainingPlan } from "../api";

const LEVEL_COLOR = { H: "red", M: "orange" };

export default function TrainingPlan({ major }) {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!major) return;
    setLoading(true);
    getTrainingPlan(major)
      .then((res) => setPlan(res.data))
      .catch(() => setPlan(null))
      .finally(() => setLoading(false));
  }, [major]);

  // 从矩阵数据中提取所有毕业要求作为列
  const { reqTitles, matrixData } = useMemo(() => {
    const rows = plan?.course_requirement_matrix || [];
    const titleSet = new Set();
    rows.forEach((r) => Object.keys(r.reqs || {}).forEach((t) => titleSet.add(t)));
    const titles = Array.from(titleSet);
    return { reqTitles: titles, matrixData: rows };
  }, [plan]);

  if (loading) return <Spin style={{ display: "block", margin: "20px auto" }} />;
  if (!plan) return <Empty description="暂无该专业的培养方案数据" />;

  return (
    <div>
      {/* 基本信息 */}
      <Card title={<><BookOutlined /> 专业基本信息</>} size="small" style={{ marginBottom: 16 }}>
        <Descriptions bordered size="small" column={3}>
          {Object.entries(plan.basic_info || {}).map(([k, v]) => (
            <Descriptions.Item key={k} label={k}>{v}</Descriptions.Item>
          ))}
        </Descriptions>
      </Card>

      {/* 毕业要求—课程体系对应矩阵 */}
      <Card
        title="毕业要求—课程体系对应矩阵"
        size="small"
        extra={<span style={{ fontSize: 12, color: "#999" }}>H=高支撑 M=中支撑</span>}
      >
        <div style={{ marginBottom: 12, fontSize: 13, color: "#666" }}>
          下表展示了各门课程对毕业要求指标点的支撑关系，是能力评估分数计算的核心依据。
          每门课程的成绩按支撑强度（H/M）加权后，映射到对应的能力维度，最终形成学生的能力雷达图。
        </div>
        <Table
          dataSource={matrixData}
          rowKey="course"
          pagination={false}
          size="small"
          scroll={{ x: "max-content" }}
          columns={[
            {
              title: "课程名称",
              dataIndex: "course",
              key: "course",
              width: 150,
              fixed: "left",
              render: (text) => <span style={{ fontWeight: 500, fontSize: 13 }}>{text}</span>,
            },
            ...reqTitles.map((title) => ({
              title: <span style={{ fontSize: 12 }}>{title}</span>,
              key: title,
              width: 90,
              align: "center",
              render: (_, row) => {
                const level = row.reqs?.[title];
                return level ? (
                  <Tag color={LEVEL_COLOR[level]} style={{ margin: 0 }}>{level}</Tag>
                ) : null;
              },
            })),
          ]}
        />
      </Card>
    </div>
  );
}
