import { useState, useEffect } from "react";
import { Card, Spin, message } from "antd";
import { getProjects } from "../../api";
import DataTable from "../../components/DataTable";

export default function ProjectsPage() {
  const studentId = localStorage.getItem("student_id");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProjects(studentId).then((r) => setData(r.data)).catch(() => message.error("加载失败")).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Card title={`项目经历（共 ${data.length} 个）`} className="section-card" style={{ marginTop: 24 }}>
      <DataTable data={data} columns={[
        { title: "项目名称", key: "project_name" }, { title: "排名", key: "rank" },
        { title: "描述", key: "description" }, { title: "时间", key: "period" },
      ]} />
    </Card>
  );
}
