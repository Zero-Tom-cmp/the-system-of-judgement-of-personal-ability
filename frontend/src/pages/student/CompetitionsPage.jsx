import { useState, useEffect } from "react";
import { Card, Spin, message } from "antd";
import { getCompetitions } from "../../api";
import DataTable from "../../components/DataTable";

export default function CompetitionsPage() {
  const studentId = localStorage.getItem("student_id");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCompetitions(studentId).then((r) => setData(r.data)).catch(() => message.error("加载失败")).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Card title={`竞赛获奖（共 ${data.length} 项）`} className="section-card" style={{ marginTop: 24 }}>
      <DataTable data={data} columns={[
        { title: "竞赛名称", key: "comp_name" }, { title: "级别", key: "level", sorter: true },
        { title: "获奖", key: "award" }, { title: "排名", key: "rank" }, { title: "时间", key: "date" },
      ]} />
    </Card>
  );
}
