import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Button, Layout, Menu } from "antd";
import {
  LogoutOutlined, TeamOutlined, ImportOutlined,
  SettingOutlined,
} from "@ant-design/icons";

const { Sider, Content } = Layout;

const MENU_ITEMS = [
  { key: "/admin",           icon: <TeamOutlined />,     label: "学生管理" },
  { key: "/admin/import",    icon: <ImportOutlined />,   label: "批量导入" },
  { key: "/admin/rules",     icon: <SettingOutlined />,  label: "规则配置" },
];

export default function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();

  // For student detail pages, highlight "学生管理"
  const selectedKey = location.pathname.startsWith("/admin/student/")
    ? "/admin"
    : MENU_ITEMS.find((m) => location.pathname === m.key)?.key || "/admin";

  const logout = () => { localStorage.clear(); navigate("/"); };

  return (
    <Layout style={{ height: "100vh", overflow: "hidden" }}>
      <div className="dashboard-header">
        <h2>人岗匹配评估系统 - 管理员</h2>
        <div className="user-info">
          管理员
          <Button type="link" icon={<LogoutOutlined />} onClick={logout} style={{ color: "#fff", marginLeft: 16 }}>退出</Button>
        </div>
      </div>
      <Layout style={{ height: "calc(100vh - 64px)" }}>
        <Sider width={200} style={{ background: "#fff", borderRight: "1px solid #f0f0f0", height: "100%", overflow: "hidden" }}>
          <div style={{ height: "100%", overflowY: "auto", paddingTop: 12 }}>
            <Menu
              mode="inline"
              selectedKeys={[selectedKey]}
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
