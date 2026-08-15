import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Button, Layout, Menu } from "antd";
import {
  LogoutOutlined, IdcardOutlined, BookOutlined, TrophyOutlined,
  ExperimentOutlined, ProjectOutlined, ScheduleOutlined,
  RadarChartOutlined, CompassOutlined, HomeOutlined,
} from "@ant-design/icons";

const { Sider, Content } = Layout;

const MENU_ITEMS = [
  { key: "/student",          icon: <HomeOutlined />,        label: "总览" },
  { key: "/student/courses",  icon: <BookOutlined />,        label: "课程成绩" },
  { key: "/student/comps",    icon: <TrophyOutlined />,      label: "竞赛获奖" },
  { key: "/student/interns",  icon: <ExperimentOutlined />,  label: "企业实习" },
  { key: "/student/projects", icon: <ProjectOutlined />,     label: "项目经历" },
  { key: "/student/plan",     icon: <ScheduleOutlined />,    label: "培养方案" },
  { key: "/student/abilities",icon: <RadarChartOutlined />,  label: "实践能力评估" },
  { key: "/student/jobs",     icon: <CompassOutlined />,     label: "岗位匹配" },
];

export default function StudentLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const name = localStorage.getItem("name");
  const major = localStorage.getItem("major");

  const logout = () => { localStorage.clear(); navigate("/"); };

  return (
    <Layout style={{ height: "100vh", overflow: "hidden" }}>
      <div className="dashboard-header">
        <h2>人岗匹配评估系统</h2>
        <div className="user-info">
          {name} | {major}
          <Button type="link" icon={<LogoutOutlined />} onClick={logout} style={{ color: "#fff", marginLeft: 16 }}>退出</Button>
        </div>
      </div>
      <Layout style={{ height: "calc(100vh - 64px)" }}>
        <Sider width={200} style={{ background: "#fff", borderRight: "1px solid #f0f0f0", height: "100%", overflow: "hidden" }}>
          <div style={{ height: "100%", overflowY: "auto", paddingTop: 12 }}>
            <Menu
              mode="inline"
              selectedKeys={[location.pathname]}
              items={MENU_ITEMS}
              onClick={({ key }) => navigate(key)}
              style={{ borderRight: 0, fontSize: 14 }}
            />
          </div>
        </Sider>
        <Content style={{ background: "#f0f2f5", height: "100%", overflowY: "auto" }}>
          <div className="dashboard-content" style={{ maxWidth: 1100, margin: "0 auto", minHeight: "100%" }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
