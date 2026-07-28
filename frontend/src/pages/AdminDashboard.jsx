import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  Row,
  Spin,
  Table,
  Tabs,
  Tag,
  message,
} from "antd";
import { LogoutOutlined, SearchOutlined } from "@ant-design/icons";
import {
  adminListStudents,
  adminSearch,
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

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [searchText, setSearchText] = useState("");

  // selected student detail data
  const [info, setInfo] = useState(null);
  const [courses, setCourses] = useState([]);
  const [competitions, setCompetitions] = useState([]);
  const [internships, setInternships] = useState([]);
  const [projects, setProjects] = useState([]);
  const [abilities, setAbilities] = useState(null);
  const [jobMatches, setJobMatches] = useState([]);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    loadStudentList();
  }, []);

  const loadStudentList = async () => {
    try {
      const res = await adminListStudents();
      setStudents(res.data);
    } catch (err) {
      message.error("加载学生列表失败");
    }
  };

  const handleSearch = async () => {
    if (!searchText.trim()) {
      loadStudentList();
      return;
    }
    try {
      const res = await adminSearch(searchText.trim());
      setStudents(res.data);
    } catch (err) {
      message.error("搜索失败");
    }
  };

  const handleSelectStudent = async (studentId) => {
    setLoadingDetail(true);
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
      setSelectedStudent(studentId);
    } catch (err) {
      message.error("加载学生详情失败");
    } finally {
      setLoadingDetail(false);
    }
  };

  const logout = () => {
    localStorage.clear();
    navigate("/");
  };

  const studentColumns = [
    { title: "学号", dataIndex: "student_id", key: "student_id" },
    { title: "姓名", dataIndex: "name", key: "name" },
    { title: "学院", dataIndex: "college", key: "college" },
    { title: "专业", dataIndex: "major", key: "major" },
    { title: "班级", dataIndex: "class_name", key: "class_name" },
    { title: "GPA", dataIndex: "gpa", key: "gpa" },
    {
      title: "操作",
      key: "action",
      render: (_, record) => (
        <Button
          type="link"
          onClick={() => handleSelectStudent(record.student_id)}
        >
          查看详情
        </Button>
      ),
    },
  ];

  const courseColumns = [
    { title: "课程名称", dataIndex: "course_name", key: "course_name" },
    { title: "成绩", dataIndex: "score", key: "score" },
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

  return (
    <div>
      <div className="dashboard-header">
        <h2>人岗匹配评估系统 - 管理员</h2>
        <div className="user-info">
          管理员
          <Button
            type="link"
            icon={<LogoutOutlined />}
            onClick={logout}
            style={{ color: "#fff", marginLeft: 16 }}
          >
            退出
          </Button>
        </div>
      </div>

      <div className="dashboard-content">
        <Card title="学生管理" className="section-card">
          <div className="admin-search">
            <Input.Search
              placeholder="输入学号或姓名搜索..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={handleSearch}
              enterButton={<><SearchOutlined /> 搜索</>}
              style={{ maxWidth: 400 }}
            />
          </div>
          <Table
            columns={studentColumns}
            dataSource={students}
            rowKey="student_id"
            pagination={false}
          />
        </Card>

        {selectedStudent && (
          <>
            {loadingDetail ? (
              <Spin size="large" style={{ display: "block", margin: "40px auto" }} />
            ) : (
              <Row gutter={24}>
                <Col span={14}>
                  <Card title={`${info?.name} - 基本信息`} className="section-card">
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
                    <Tabs
                      items={[
                        {
                          key: "courses",
                          label: "课程成绩",
                          children: (
                            <Table
                              columns={courseColumns}
                              dataSource={courses}
                              rowKey="id"
                              pagination={false}
                              size="small"
                            />
                          ),
                        },
                        {
                          key: "competitions",
                          label: "竞赛获奖",
                          children: (
                            <Table
                              columns={compColumns}
                              dataSource={competitions}
                              rowKey="id"
                              pagination={false}
                              size="small"
                            />
                          ),
                        },
                        {
                          key: "internships",
                          label: "实习经历",
                          children: (
                            <Table
                              columns={internColumns}
                              dataSource={internships}
                              rowKey="id"
                              pagination={false}
                              size="small"
                            />
                          ),
                        },
                        {
                          key: "projects",
                          label: "项目经历",
                          children: (
                            <Table
                              columns={projColumns}
                              dataSource={projects}
                              rowKey="id"
                              pagination={false}
                              size="small"
                            />
                          ),
                        },
                      ]}
                    />
                  </Card>
                </Col>

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
            )}
          </>
        )}
      </div>
    </div>
  );
}
