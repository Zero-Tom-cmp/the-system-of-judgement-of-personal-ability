import axios from "axios";

const api = axios.create({ baseURL: "/api", timeout: 300000 });  // 5分钟超时，大文件导入需要更长时间

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear();
      window.location.href = "/";
    }
    return Promise.reject(err);
  }
);

export function login(username, password) {
  return api.post("/login", { username, password });
}

export function getStudentInfo(studentId) {
  return api.get(`/student/${studentId}/info`);
}

export function getCourses(studentId) {
  return api.get(`/student/${studentId}/courses`);
}

export function getCompetitions(studentId) {
  return api.get(`/student/${studentId}/competitions`);
}

export function getInternships(studentId) {
  return api.get(`/student/${studentId}/internships`);
}

export function getProjects(studentId) {
  return api.get(`/student/${studentId}/projects`);
}

export function getAbilities(studentId) {
  return api.get(`/student/${studentId}/abilities`);
}

export function getJobMatch(studentId) {
  return api.get(`/student/${studentId}/job-match`);
}

export function getTrainingPlan(major) {
  return api.get(`/training-plan/${encodeURIComponent(major)}`);
}

export function adminSearch(query) {
  return api.get("/admin/search", { params: { q: query } });
}

export function adminListStudents(page = 1, pageSize = 100, search = "", college = "", major = "") {
  return api.get("/admin/students", { params: { page, page_size: pageSize, search, college, major } });
}

export function adminGetStats() {
  return api.get("/admin/stats");
}

// 学生 CRUD
export function adminCreateStudent(data) {
  return api.post("/admin/student", data);
}
export function adminUpdateStudent(studentId, data) {
  return api.put(`/admin/student/${studentId}`, data);
}
export function adminDeleteStudent(studentId) {
  return api.delete(`/admin/student/${studentId}`);
}

// 批量操作
export function adminBatchDelete(studentIds) {
  return api.post("/admin/students/batch-delete", { student_ids: studentIds });
}
export function adminBatchResetPwd(studentIds, newPassword = "student123") {
  return api.post("/admin/students/batch-reset-pwd", { student_ids: studentIds, new_password: newPassword });
}

// 课程 CRUD
export function adminAddCourse(studentId, data) {
  return api.post(`/admin/student/${studentId}/courses`, data);
}
export function adminUpdateCourse(courseId, data) {
  return api.put(`/admin/course/${courseId}`, data);
}
export function adminDeleteCourse(courseId) {
  return api.delete(`/admin/course/${courseId}`);
}

// 竞赛 CRUD
export function adminAddCompetition(studentId, data) {
  return api.post(`/admin/student/${studentId}/competitions`, data);
}
export function adminUpdateCompetition(compId, data) {
  return api.put(`/admin/competition/${compId}`, data);
}
export function adminDeleteCompetition(compId) {
  return api.delete(`/admin/competition/${compId}`);
}

// 实习 CRUD
export function adminAddInternship(studentId, data) {
  return api.post(`/admin/student/${studentId}/internships`, data);
}
export function adminUpdateInternship(internId, data) {
  return api.put(`/admin/internship/${internId}`, data);
}
export function adminDeleteInternship(internId) {
  return api.delete(`/admin/internship/${internId}`);
}

// 项目 CRUD
export function adminAddProject(studentId, data) {
  return api.post(`/admin/student/${studentId}/projects`, data);
}
export function adminUpdateProject(projId, data) {
  return api.put(`/admin/project/${projId}`, data);
}
export function adminDeleteProject(projId) {
  return api.delete(`/admin/project/${projId}`);
}

// 批量导入
export function adminImportCsv(dataType, file) {
  const formData = new FormData();
  formData.append("file", file);
  return api.post(`/admin/import/${dataType}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export function adminDownloadTemplate(dataType) {
  return api.get(`/admin/template/${dataType}`, { responseType: "blob" });
}

// 综合导入（Excel）
export function adminImportAll(file) {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/admin/import/all", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export function adminDownloadAllTemplate() {
  return api.get("/admin/template/all", { responseType: "blob" });
}

export function adminDownloadConflicts(errors, sheet) {
  return api.post("/admin/import/conflicts/download", { errors, sheet }, { responseType: "blob" });
}

// 密码修改
export function changePassword(old_password, new_password) {
  return api.put("/student/password", { old_password, new_password });
}

// 审计日志
export function adminGetAuditLog(limit = 50) {
  return api.get("/admin/audit-log", { params: { limit } });
}

// 评估规则
export function adminGetRules(ruleType) {
  return api.get(`/admin/rules/${ruleType}`);
}
export function adminUpdateRule(ruleType, ruleId, data) {
  return api.put(`/admin/rules/${ruleType}/${ruleId}`, data);
}
