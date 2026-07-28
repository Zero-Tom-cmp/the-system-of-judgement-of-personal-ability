import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Col, Descriptions, Row, Spin, Table, Tabs, Tag, message } from "antd";
import { LogoutOutlined } from "@ant-design/icons";
import {
  getStudentInfo,
  getCourses,
  getCompetitions,
  getInternships,
  getProjects,
  getAbilities,
  getJobMatch,
} from "../api";
import AbilityRadar from "../components/AbilityRadar";
import JobMatchPanel from "../components/JobMatchPanel";
import ScoreExplain from "../components/ScoreExplain";

export default function StudentDashboard() {
  const navigate = useNavigate();
  const studentId = localStorage.getItem("student_id");
  const name = localStorage.getItem("name");

  const [info, setInfo] = useState(null);
  const [courses, setCourses] = useState([]);
  const [competitions, setCompetitions] = useState([]);
  const [internships, setInternships] = useState([]);
  const [projects, setProjects] = useState([]);
  const [abilities, setAbilities] = useState(null);
  const [jobMatches, setJobMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    try {
      const [infoRes, coursesRes, compsRes, internRes, projRes, abiRes, jobRes] =
        await Promise.all([
          getStudentInfo(studentId),
          getCourses(studentId),
          getCompetitions(studentId),
          getInternships(studentId),
          getProjects(studentId),
          getAbilities(studentId),
          getJobMatch(studentId),
        ]);
      setInfo(infoRes.data);
      setCourses(coursesRes.data);
      setCompetitions(compsRes.data);
      setInternships(internRes.data);
      setProjects(projRes.data);
      setAbilities(abiRes.data);
      setJobMatches(jobRes.data);
    } catch (err) {
      message.error("数据加载失败");
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.clear();
    navigate("/");
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "200px auto" }} />;

  const courseColumns = [
    { title: "课程名称", dataIndex: "course_name", key: "course_name" },
    { title: "成绩", dataIndex: "score", key: "score", sorter: (a, b) => a.score - b.score },
    { title: "学分", dataIndex: "credit", key: "credit" },
    { title: "学期", dataIndex: "semester", key: "semester" },
    { title: "类别", dataIndex: "course_nature", key: "course_nature" },
  ];

  const compColumns = [
    { title: "竞赛名称", dataIndex: "comp_name", key: "comp_name" },
    { title: "级别", dataIndex: "level", key: "level" },
    { title: "获奖", dataIndex: "award", key: "award" },
    { title: "角色", dataIndex: "role", key: "role" },
    { title: "时间", dataIndex: "date", key: "date" },
  ];

  const internColumns = [
    { title: "公司", dataIndex: "company", key: "company" },
    { title: "职位", dataIndex: "position", key: "position" },
    { title: "时长(月)", dataIndex: "duration_months", key: "duration_months" },
    { title: "描述", dataIndex: "description", key: "description" },
    { title: "时间", dataIndex: "date", key: "date" },
  ];

  const projColumns = [
    { title: "项目名称", dataIndex: "project_name", key: "project_name" },
    { title: "角色", dataIndex: "role", key: "role" },
    { title: "描述", dataIndex: "description", key: "description" },
    { title: "技术栈", dataIndex: "tech_stack", key: "tech_stack" },
    { title: "时间", dataIndex: "date", key: "date" },
  ];

  const tabItems = [
    {
      key: "courses",
      label: `课程成绩 (${courses.length})`,
      children: (
        <Table columns={courseColumns} dataSource={courses} rowKey="id" pagination={false} />
      ),
    },
    {
      key: "competitions",
      label: `竞赛获奖 (${competitions.length})`,
      children: (
        <Table columns={compColumns} dataSource={competitions} rowKey="id" pagination={false} />
      ),
    },
    {
      key: "internships",
      label: `实习经历 (${internships.length})`,
      children: (
        <Table columns={internColumns} dataSource={internships} rowKey="id" pagination={false} />
      ),
    },
    {
      key: "projects",
      label: `项目经历 (${projects.length})`,
      children: (
        <Table columns={projColumns} dataSource={projects} rowKey="id" pagination={false} />
      ),
    },
  ];

  return (
    <div>
      <div className="dashboard-header">
        <h2>人岗匹配评估系统</h2>
        <div className="user-info">
          {name} | {info?.major} | {info?.college}
          <Button type="link" icon={<LogoutOutlined />} onClick={logout} style={{ color: "#fff", marginLeft: 16 }}>
            退出
          </Button>
        </div>
      </div>

      <div className="dashboard-content">
        <Row gutter={24}>
          {/* 左侧：基本信息 + 详细数据 */}
          <Col span={14}>
            <Card title="基本信息" className="section-card">
              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label="姓名">{info?.name}</Descriptions.Item>
                <Descriptions.Item label="学号">{info?.student_id}</Descriptions.Item>
                <Descriptions.Item label="学院">{info?.college}</Descriptions.Item>
                <Descriptions.Item label="专业">{info?.major}</Descriptions.Item>
                <Descriptions.Item label="班级">{info?.class_name}</Descriptions.Item>
                <Descriptions.Item label="GPA">
                  <Tag color="blue">{info?.gpa}</Tag>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="详细数据" className="section-card">
              <Tabs items={tabItems} />
            </Card>
          </Col>

          {/* 右侧：能力评估 + 解释 + 岗位匹配 */}
          <Col span={10}>
            {abilities && (
              <Card title="能力评估雷达图" className="section-card">
                <AbilityRadar abilities={abilities} />
                <ScoreExplain abilities={abilities} />
              </Card>
            )}

            {jobMatches.length > 0 && (
              <Card title="岗位匹配推荐" className="section-card">
                <JobMatchPanel matches={jobMatches} studentAbilities={abilities} />
              </Card>
            )}
          </Col>
        </Row>
      </div>
    </div>
  );
}
