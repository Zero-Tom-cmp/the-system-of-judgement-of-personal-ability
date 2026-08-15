import { useState, useEffect, useMemo } from "react";
import { Card, Col, Descriptions, Row, Spin, Statistic, Tag, message } from "antd";
import { getStudentInfo, getCourses, getAbilities, getJobMatch } from "../../api";

export default function OverviewPage() {
  const studentId = localStorage.getItem("student_id");
  const [info, setInfo] = useState(null);
  const [courses, setCourses] = useState([]);
  const [abilities, setAbilities] = useState(null);
  const [jobMatches, setJobMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [i, c, a, j] = await Promise.all([
        getStudentInfo(studentId), getCourses(studentId),
        getAbilities(studentId), getJobMatch(studentId),
      ]);
      setInfo(i.data); setCourses(c.data); setAbilities(a.data); setJobMatches(j.data);
    } catch (err) { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  const summary = useMemo(() => {
    if (!abilities || !jobMatches.length) return null;
    const scores = Object.values(abilities.abilities).map((v) => v.score);
    const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
    const weakest = Object.entries(abilities.abilities).sort((a, b) => a[1].score - b[1].score)[0];
    return { avgScore: avg, bestJob: jobMatches[0], weakestAbility: weakest ? { name: weakest[0], score: weakest[1].score } : null };
  }, [abilities, jobMatches]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <>
      {summary && (
        <Card className="section-card" size="small" style={{ marginTop: 24 }}>
          <Row gutter={16}>
            <Col span={8}><Statistic title="综合能力均分" value={summary.avgScore} suffix="分" valueStyle={{ color: summary.avgScore >= 70 ? "#3f8600" : summary.avgScore >= 40 ? "#1890ff" : "#cf1322" }} /></Col>
            <Col span={8}><Statistic title="最佳匹配岗位" value={summary.bestJob?.job_name || "—"} valueStyle={{ fontSize: 18 }} /><Tag color="blue">{summary.bestJob?.overall_match}%</Tag></Col>
            <Col span={8}><Statistic title="最需提升能力" value={summary.weakestAbility?.name || "—"} valueStyle={{ fontSize: 16, color: "#cf1322" }} /><span style={{ fontSize: 13, color: "#999" }}>{summary.weakestAbility?.score} 分</span></Col>
          </Row>
        </Card>
      )}

      <Card title="基本信息" className="section-card">
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="姓名">{info?.name}</Descriptions.Item>
          <Descriptions.Item label="学号">{info?.student_id}</Descriptions.Item>
          <Descriptions.Item label="学院">{info?.college}</Descriptions.Item>
          <Descriptions.Item label="专业">{info?.major}</Descriptions.Item>
          <Descriptions.Item label="班级">{info?.class_name}</Descriptions.Item>
          <Descriptions.Item label="GPA"><Tag color="blue">{info?.gpa}</Tag></Descriptions.Item>
          <Descriptions.Item label="已修学分"><Tag color="green">{info?.total_credits} 学分</Tag></Descriptions.Item>
          <Descriptions.Item label="已修课程门数">{courses.length} 门</Descriptions.Item>
        </Descriptions>
      </Card>
    </>
  );
}
