import axios from "axios";

const api = axios.create({ baseURL: "/api" });

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

export function adminSearch(query) {
  return api.get("/admin/search", { params: { q: query } });
}

export function adminListStudents() {
  return api.get("/admin/students");
}
