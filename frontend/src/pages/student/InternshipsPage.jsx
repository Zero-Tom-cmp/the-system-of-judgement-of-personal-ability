import { useState, useEffect } from "react";
import { Card, Spin, message } from "antd";
import { getInternships } from "../../api";
import DataTable from "../../components/DataTable";

export default function InternshipsPage() {
  const studentId = localStorage.getItem("student_id");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getInternships(studentId).then((r) => setData(r.data)).catch(() => message.error("加载失败")).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Card title={`企业实习（共 ${data.length} 段）`} className="section-card" style={{ marginTop: 24 }}>
      <DataTable data={data} columns={[
        { title: "公司", key: "company" }, { title: "职位", key: "position" },
        { title: "描述", key: "description" }, { title: "时间", key: "period" },
      ]} />
    </Card>
  );
}
