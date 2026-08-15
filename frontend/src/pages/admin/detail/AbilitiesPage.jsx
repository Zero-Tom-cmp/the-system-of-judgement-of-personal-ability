import { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Card, Spin, message } from "antd";
import { getAbilities } from "../../../api";
import AbilityRadar from "../../../components/AbilityRadar";
import ScoreExplain from "../../../components/ScoreExplain";

export default function AbilitiesPage() {
  const { studentId } = useOutletContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAbilities(studentId).then((r) => setData(r.data)).catch(() => message.error("加载失败")).finally(() => setLoading(false));
  }, [studentId]);

  if (loading) return <Spin style={{ display: "block", margin: "40px auto" }} />;

  return (
    <Card title="实践能力评估雷达图">
      <AbilityRadar abilities={data} />
      <ScoreExplain abilities={data} />
    </Card>
  );
}
