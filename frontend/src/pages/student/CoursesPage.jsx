import { useState, useEffect } from "react";
import { Card, Spin, message } from "antd";
import { getCourses } from "../../api";
import DataTable from "../../components/DataTable";

export default function CoursesPage() {
  const studentId = localStorage.getItem("student_id");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCourses(studentId).then((r) => setData(r.data)).catch(() => message.error("加载失败")).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Card title={`课程成绩（共 ${data.length} 门）`} className="section-card" style={{ marginTop: 24 }}>
      <DataTable data={data} columns={[
        { title: "课程名称", key: "course_name" }, { title: "成绩", key: "score", sorter: true },
        { title: "总学分", key: "credit" }, { title: "实践学分", key: "practical_credit" },
        { title: "学期", key: "semester" }, { title: "类别", key: "course_nature" },
      ]} />
    </Card>
  );
}
