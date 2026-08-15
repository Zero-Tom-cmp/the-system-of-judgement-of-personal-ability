import { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Card, Spin, message } from "antd";
import { getJobMatch } from "../../../api";
import JobMatchPanel from "../../../components/JobMatchPanel";

export default function JobsPage() {
  const { studentId } = useOutletContext();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getJobMatch(studentId).then((r) => setData(r.data)).catch(() => message.error("加载失败")).finally(() => setLoading(false));
  }, [studentId]);

  if (loading) return <Spin style={{ display: "block", margin: "40px auto" }} />;

  return (
    <Card title="岗位匹配推荐">
      <JobMatchPanel matches={data} />
    </Card>
  );
}
