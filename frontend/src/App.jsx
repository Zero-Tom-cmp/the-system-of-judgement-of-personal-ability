import { Component, lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Button, Result, Spin } from "antd";
import LoginPage from "./pages/LoginPage";

// 路由级代码拆分 —— 懒加载所有页面组件
const StudentLayout = lazy(() => import("./pages/student/StudentLayout"));
const OverviewPage = lazy(() => import("./pages/student/OverviewPage"));
const CoursesPage = lazy(() => import("./pages/student/CoursesPage"));
const CompetitionsPage = lazy(() => import("./pages/student/CompetitionsPage"));
const InternshipsPage = lazy(() => import("./pages/student/InternshipsPage"));
const ProjectsPage = lazy(() => import("./pages/student/ProjectsPage"));
const TrainingPlanPage = lazy(() => import("./pages/student/TrainingPlanPage"));
const AbilitiesPage = lazy(() => import("./pages/student/AbilitiesPage"));
const JobMatchPage = lazy(() => import("./pages/student/JobMatchPage"));
const AdminLayout = lazy(() => import("./pages/admin/AdminLayout"));
const DashboardPage = lazy(() => import("./pages/admin/DashboardPage"));
const StudentDetailLayout = lazy(() => import("./pages/admin/StudentDetailLayout"));
const DetailBasicPage = lazy(() => import("./pages/admin/detail/BasicPage"));
const DetailCoursesPage = lazy(() => import("./pages/admin/detail/CoursesPage"));
const DetailCompetitionsPage = lazy(() => import("./pages/admin/detail/CompetitionsPage"));
const DetailInternshipsPage = lazy(() => import("./pages/admin/detail/InternshipsPage"));
const DetailProjectsPage = lazy(() => import("./pages/admin/detail/ProjectsPage"));
const DetailPlanPage = lazy(() => import("./pages/admin/detail/PlanPage"));
const DetailAbilitiesPage = lazy(() => import("./pages/admin/detail/AbilitiesPage"));
const DetailJobsPage = lazy(() => import("./pages/admin/detail/JobsPage"));
const ImportPage = lazy(() => import("./pages/admin/ImportPage"));
const AuditLogPage = lazy(() => import("./pages/admin/AuditLogPage"));
const RulesPage = lazy(() => import("./pages/admin/RulesPage"));

const PageLoader = () => <Spin size="large" style={{ display: "block", margin: "40px auto" }} />;

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <Result status="error" title="页面渲染出错" subTitle={this.state.error?.message || "未知错误"}
          extra={<Button type="primary" onClick={() => { this.setState({ hasError: false }); window.location.reload(); }}>刷新页面</Button>} />
      );
    }
    return this.props.children;
  }
}

function PrivateRoute({ children, allowedRole }) {
  const token = localStorage.getItem("token");
  const role = localStorage.getItem("role");
  if (!token) return <Navigate to="/" replace />;
  if (allowedRole && role !== allowedRole) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/student" element={<PrivateRoute allowedRole="student"><StudentLayout /></PrivateRoute>}>
            <Route index element={<OverviewPage />} />
            <Route path="courses" element={<CoursesPage />} />
            <Route path="comps" element={<CompetitionsPage />} />
            <Route path="interns" element={<InternshipsPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="plan" element={<TrainingPlanPage />} />
            <Route path="abilities" element={<AbilitiesPage />} />
            <Route path="jobs" element={<JobMatchPage />} />
          </Route>
          <Route path="/admin" element={<PrivateRoute allowedRole="admin"><AdminLayout /></PrivateRoute>}>
            <Route index element={<DashboardPage />} />
            <Route path="student/:studentId" element={<StudentDetailLayout />}>
              <Route index element={<DetailBasicPage />} />
              <Route path="courses" element={<DetailCoursesPage />} />
              <Route path="competitions" element={<DetailCompetitionsPage />} />
              <Route path="internships" element={<DetailInternshipsPage />} />
              <Route path="projects" element={<DetailProjectsPage />} />
              <Route path="plan" element={<DetailPlanPage />} />
              <Route path="abilities" element={<DetailAbilitiesPage />} />
              <Route path="jobs" element={<DetailJobsPage />} />
            </Route>
            <Route path="import" element={<ImportPage />} />
            <Route path="logs" element={<AuditLogPage />} />
            <Route path="rules" element={<RulesPage />} />
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
