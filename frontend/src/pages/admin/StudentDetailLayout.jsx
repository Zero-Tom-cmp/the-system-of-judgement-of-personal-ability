import { useState, useEffect } from "react";
import { Outlet, useParams, useLocation, useNavigate } from "react-router-dom";
import { Button, Card, Descriptions, Layout, Menu, Spin, Tag, message } from "antd";
import { ArrowLeftOutlined, IdcardOutlined, BookOutlined, TrophyOutlined, ExperimentOutlined, ProjectOutlined, ScheduleOutlined, RadarChartOutlined, CompassOutlined } from "@ant-design/icons";
import { getStudentInfo, getCourses } from "../../api";

const { Sider, Content } = Layout;

export default function StudentDetailLayout() {
  const { studentId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [info, setInfo] = useState(null);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([getStudentInfo(studentId), getCourses(studentId)])
      .then(([i, c]) => { setInfo(i.data); setCourses(c.data); })
      .catch(() => message.error("加载失败"))
      .finally(() => setLoading(false));
  }, [studentId]);

  const base = `/admin/student/${studentId}`;
  const menuItems = [
    { key: base,                  icon: <IdcardOutlined />,     label: "基本信息" },
    { key: `${base}/courses`,     icon: <BookOutlined />,       label: "课程成绩" },
    { key: `${base}/competitions`,icon: <TrophyOutlined />,     label: "竞赛获奖" },
    { key: `${base}/internships`, icon: <ExperimentOutlined />, label: "企业实习" },
    { key: `${base}/projects`,    icon: <ProjectOutlined />,    label: "项目经历" },
    { key: `${base}/plan`,        icon: <ScheduleOutlined />,   label: "培养方案" },
    { key: `${base}/abilities`,   icon: <RadarChartOutlined />, label: "实践能力评估" },
    { key: `${base}/jobs`,        icon: <CompassOutlined />,    label: "岗位匹配" },
  ];

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <div style={{ marginTop: 24 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/admin")} style={{ marginBottom: 16 }}>返回学生列表</Button>

      <Card className="section-card" size="small">
        <Descriptions bordered size="small" column={3}>
          <Descriptions.Item label="姓名">{info?.name}</Descriptions.Item>
          <Descriptions.Item label="学号">{info?.student_id}</Descriptions.Item>
          <Descriptions.Item label="专业">{info?.major}</Descriptions.Item>
          <Descriptions.Item label="学院">{info?.college}</Descriptions.Item>
          <Descriptions.Item label="班级">{info?.class_name}</Descriptions.Item>
          <Descriptions.Item label="GPA"><Tag color="blue">{info?.gpa}</Tag></Descriptions.Item>
          <Descriptions.Item label="已修学分"><Tag color="green">{info?.total_credits} 学分</Tag></Descriptions.Item>
          <Descriptions.Item label="已修课程门数">{courses.length} 门</Descriptions.Item>
        </Descriptions>
      </Card>

      <Layout style={{ background: "transparent", marginTop: 16, minHeight: 400 }}>
        <Sider width={180} style={{ background: "#fff", borderRight: "1px solid #f0f0f0" }}>
          <Menu mode="inline" selectedKeys={[location.pathname]} items={menuItems}
            onClick={({ key }) => navigate(key)} style={{ borderRight: 0, fontSize: 13 }} />
        </Sider>
        <Content style={{ background: "transparent", paddingLeft: 24 }}>
          <Outlet context={{ studentId, info }} />
        </Content>
      </Layout>
    </div>
  );
}
