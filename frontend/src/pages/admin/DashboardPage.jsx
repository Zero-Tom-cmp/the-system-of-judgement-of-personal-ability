import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Col, Form, Input, InputNumber, Modal, Popconfirm, Row, Select, Space, Spin, Statistic, Table, Tag, message } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, TeamOutlined, BookOutlined, TrophyOutlined, ExperimentOutlined, ProjectOutlined, SearchOutlined, ClearOutlined } from "@ant-design/icons";
import { adminListStudents, adminGetStats, adminCreateStudent, adminUpdateStudent, adminDeleteStudent, adminBatchDelete, adminBatchResetPwd } from "../../api";

export default function DashboardPage() {
  const navigate = useNavigate();
  const [students, setStudents] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  // 搜索与筛选
  const [filters, setFilters] = useState({ college: "", major: "", class_name: "", name: "", student_id: "" });
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => { loadData(); }, []);

  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const loadData = async (p = 1) => {
    try {
      const [s, st] = await Promise.all([
        adminListStudents(p, pageSize, filters.name || filters.student_id || "", filters.college, filters.major),
        adminGetStats(),
      ]);
      setStudents(s.data.data); setTotal(s.data.total); setStats(st.data);
    } catch (err) { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  // 提取可用的筛选选项
  const collegeOptions = useMemo(() => [...new Set(students.map((s) => s.college).filter(Boolean))].sort(), [students]);
  const majorOptions = useMemo(() => {
    const base = filters.college ? students.filter((s) => s.college === filters.college) : students;
    return [...new Set(base.map((s) => s.major).filter(Boolean))].sort();
  }, [students, filters.college]);
  const classOptions = useMemo(() => {
    let base = students;
    if (filters.college) base = base.filter((s) => s.college === filters.college);
    if (filters.major) base = base.filter((s) => s.major === filters.major);
    return [...new Set(base.map((s) => s.class_name).filter(Boolean))].sort();
  }, [students, filters.college, filters.major]);

  // 筛选 + 排序
  const filtered = useMemo(() => {
    let result = [...students];
    if (filters.student_id) result = result.filter((s) => s.student_id.includes(filters.student_id));
    if (filters.name) result = result.filter((s) => s.name.includes(filters.name));
    if (filters.college) result = result.filter((s) => s.college === filters.college);
    if (filters.major) result = result.filter((s) => s.major === filters.major);
    if (filters.class_name) result = result.filter((s) => s.class_name === filters.class_name);
    result.sort((a, b) => a.student_id.localeCompare(b.student_id));
    return result;
  }, [students, filters]);

  const updateFilter = (key, value) => {
    const next = { ...filters, [key]: value };
    // 联动清除
    if (key === "college") { next.major = ""; next.class_name = ""; }
    if (key === "major") { next.class_name = ""; }
    setFilters(next);
  };
  const clearFilters = () => setFilters({ college: "", major: "", class_name: "", name: "", student_id: "" });

  const openAdd = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (s) => { setEditing(s); form.setFieldsValue(s); setModalOpen(true); };
  const handleSubmit = async () => {
    const vals = await form.validateFields();
    if (editing) {
      const data = {}; for (const k of ["name","college","major","class_name","gpa"]) if (vals[k] !== editing[k]) data[k] = vals[k];
      if (vals.password) data.password = vals.password;
      if (Object.keys(data).length > 0) await adminUpdateStudent(editing.student_id, data);
    } else { await adminCreateStudent(vals); }
    message.success(editing ? "更新成功" : "创建成功"); setModalOpen(false); loadData();
  };
  const handleDelete = async (sid) => { await adminDeleteStudent(sid); message.success("已删除"); loadData(); };

  const handleBatchDelete = async () => {
    Modal.confirm({
      title: `确认删除 ${selectedRowKeys.length} 名学生？`,
      content: "将同时删除这些学生的全部课程、竞赛、实习、项目数据，不可恢复。",
      okText: "确认删除", okType: "danger", cancelText: "取消",
      onOk: async () => {
        await adminBatchDelete(selectedRowKeys);
        message.success(`已删除 ${selectedRowKeys.length} 名学生`);
        setSelectedRowKeys([]); loadData();
      },
    });
  };

  const [batchPwdModalOpen, setBatchPwdModalOpen] = useState(false);
  const [batchPwdForm] = Form.useForm();

  const handleBatchResetPwd = () => { batchPwdForm.resetFields(); setBatchPwdModalOpen(true); };
  const submitBatchResetPwd = async () => {
    const vals = await batchPwdForm.validateFields();
    await adminBatchResetPwd(selectedRowKeys, vals.new_password);
    message.success(`已重置 ${selectedRowKeys.length} 名学生密码`);
    setBatchPwdModalOpen(false); setSelectedRowKeys([]);
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <div style={{ marginTop: 24 }}>
      {/* 统计面板 */}
      {stats && (
        <Card className="section-card" size="small">
          <Row gutter={16}>
            <Col span={6}><Statistic title="学生总数" value={stats.total_students} prefix={<TeamOutlined />} /></Col>
            <Col span={6}><Statistic title="平均 GPA" value={stats.avg_gpa} precision={2} /></Col>
            <Col span={6}><Statistic title="课程记录" value={stats.total_courses} prefix={<BookOutlined />} /></Col>
            <Col span={6}><Statistic title="竞赛记录" value={stats.total_competitions} prefix={<TrophyOutlined />} /></Col>
          </Row>
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={6}><Statistic title="实习记录" value={stats.total_internships} prefix={<ExperimentOutlined />} /></Col>
            <Col span={6}><Statistic title="项目记录" value={stats.total_projects} prefix={<ProjectOutlined />} /></Col>
            <Col span={12}>
              <span style={{ fontSize: 13, color: "#666" }}>专业分布：{stats.majors?.map((m) => <Tag key={m.major}>{m.major} {m.count}人</Tag>)}</span>
            </Col>
          </Row>
        </Card>
      )}

      {/* 搜索与筛选 —— 居中 */}
      <Card className="section-card" size="small">
        <div style={{ textAlign: "center", marginBottom: 12 }}>
          <SearchOutlined style={{ fontSize: 18, marginRight: 8, color: "#1890ff" }} />
          <span style={{ fontSize: 15, fontWeight: 500 }}>搜索与筛选</span>
        </div>
        <Row gutter={[12, 12]} justify="center">
          <Col><Select placeholder="学院" allowClear value={filters.college || undefined} onChange={(v) => updateFilter("college", v || "")} style={{ width: 150 }} options={collegeOptions.map((c) => ({ value: c, label: c }))} /></Col>
          <Col><Select placeholder="专业" allowClear value={filters.major || undefined} onChange={(v) => updateFilter("major", v || "")} style={{ width: 140 }} options={majorOptions.map((m) => ({ value: m, label: m }))} /></Col>
          <Col><Select placeholder="班级" allowClear value={filters.class_name || undefined} onChange={(v) => updateFilter("class_name", v || "")} style={{ width: 140 }} options={classOptions.map((c) => ({ value: c, label: c }))} /></Col>
          <Col><Input placeholder="姓名" allowClear value={filters.name} onChange={(e) => updateFilter("name", e.target.value)} style={{ width: 120 }} prefix={<SearchOutlined />} /></Col>
          <Col><Input placeholder="学号" allowClear value={filters.student_id} onChange={(e) => updateFilter("student_id", e.target.value)} style={{ width: 140 }} prefix={<SearchOutlined />} /></Col>
          <Col><Button icon={<ClearOutlined />} onClick={clearFilters}>清除筛选</Button></Col>
        </Row>
      </Card>

      {/* 学生表格 */}
      <Card
        title={`学生管理（${filtered.length} 人）`}
        className="section-card"
        extra={
          <Space>
            {selectedRowKeys.length > 0 && (
              <>
                <span style={{ color: "#1890ff", fontSize: 13 }}>已选 {selectedRowKeys.length} 人</span>
                <Button size="small" onClick={handleBatchResetPwd}>批量重置密码</Button>
                <Popconfirm title={`确定删除 ${selectedRowKeys.length} 名学生及其全部数据？`} onConfirm={handleBatchDelete}>
                  <Button size="small" danger>批量删除</Button>
                </Popconfirm>
              </>
            )}
            <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>添加学生</Button>
          </Space>
        }
      >
        <Table
          dataSource={filtered} rowKey="student_id" size="middle"
          rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
          pagination={{ current: page, pageSize, total, showTotal: (t) => `共 ${t} 人`, onChange: (p) => { setPage(p); loadData(p); } }}
          columns={[
            { title: "学号", dataIndex: "student_id", key: "sid", defaultSortOrder: "ascend", sorter: (a, b) => a.student_id.localeCompare(b.student_id) },
            { title: "姓名", dataIndex: "name", key: "name" },
            { title: "学院", dataIndex: "college", key: "college" },
            { title: "专业", dataIndex: "major", key: "major" },
            { title: "班级", dataIndex: "class_name", key: "cls" },
            { title: "GPA", dataIndex: "gpa", key: "gpa", width: 70 },
            { title: "操作", key: "act", width: 240,
              render: (_, r) => (
                <Space size="small">
                  <Button type="link" size="small" onClick={() => navigate(`/admin/student/${r.student_id}`)}>查看详情</Button>
                  <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
                  <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.student_id)}>
                    <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {/* 批量重置密码 Modal */}
      <Modal title={`重置 ${selectedRowKeys.length} 名学生密码`} open={batchPwdModalOpen} onOk={submitBatchResetPwd} onCancel={() => setBatchPwdModalOpen(false)} destroyOnClose>
        <Form form={batchPwdForm} layout="vertical">
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6, message: "至少6位" }]}>
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 学生 CRUD Modal */}
      <Modal title={editing ? "编辑学生" : "添加学生"} open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)} width={560} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="student_id" label="学号" rules={[{ required: true }]}><Input disabled={!!editing} /></Form.Item>
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}><Input /></Form.Item>
          <Row gutter={12}>
            <Col span={12}><Form.Item name="college" label="学院" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="major" label="专业" rules={[{ required: true }]}><Input /></Form.Item></Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}><Form.Item name="class_name" label="班级" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="gpa" label="GPA" rules={[{ required: true }]}><InputNumber min={0} max={5} step={0.01} style={{ width: "100%" }} /></Form.Item></Col>
          </Row>
          <Form.Item name="password" label={editing ? "新密码（留空不修改）" : "密码"} rules={editing ? [] : [{ required: true }]}><Input.Password /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
