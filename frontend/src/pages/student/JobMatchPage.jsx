import { useState, useEffect } from "react";
import { Card, Spin, message } from "antd";
import { getJobMatch } from "../../api";
import JobMatchPanel from "../../components/JobMatchPanel";

export default function JobMatchPage() {
  const studentId = localStorage.getItem("student_id");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getJobMatch(studentId).then((r) => setData(r.data)).catch(() => message.error("加载失败")).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Card title="岗位匹配推荐" className="section-card" style={{ marginTop: 24 }}>
      <JobMatchPanel matches={data} />
    </Card>
  );
}
