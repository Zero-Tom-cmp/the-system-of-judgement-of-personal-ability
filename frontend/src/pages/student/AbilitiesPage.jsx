import { useState, useEffect } from "react";
import { Card, Spin, message } from "antd";
import { getAbilities } from "../../api";
import AbilityRadar from "../../components/AbilityRadar";
import ScoreExplain from "../../components/ScoreExplain";

export default function AbilitiesPage() {
  const studentId = localStorage.getItem("student_id");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAbilities(studentId).then((r) => setData(r.data)).catch(() => message.error("加载失败")).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Card title="实践能力评估雷达图" className="section-card" style={{ marginTop: 24 }}>
      <AbilityRadar abilities={data} />
      <ScoreExplain abilities={data} />
    </Card>
  );
}
