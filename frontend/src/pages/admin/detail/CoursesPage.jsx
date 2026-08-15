import { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Button, Card, Col, Form, Input, InputNumber, Modal, Popconfirm, Row, Select, Space, Spin, message } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { getCourses, adminAddCourse, adminUpdateCourse, adminDeleteCourse } from "../../../api";
import DataTable from "../../../components/DataTable";

export default function CoursesPage() {
  const { studentId } = useOutletContext();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  const load = () => getCourses(studentId).then((r) => setData(r.data)).finally(() => setLoading(false));
  useEffect(() => { load(); }, [studentId]);

  const openAdd = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (r) => { setEditing(r); form.setFieldsValue(r); setModalOpen(true); };
  const handleSubmit = async () => {
    const vals = await form.validateFields();
    editing ? await adminUpdateCourse(editing.id, vals) : await adminAddCourse(studentId, vals);
    message.success(editing ? "更新成功" : "添加成功"); setModalOpen(false); load();
  };
  const handleDelete = async (id) => { await adminDeleteCourse(id); message.success("已删除"); load(); };

  const columns = [
    { title: "课程名称", key: "course_name" }, { title: "成绩", key: "score", sorter: true },
    { title: "总学分", key: "credit" }, { title: "实践学分", key: "practical_credit" },
    { title: "学期", key: "semester" }, { title: "类别", key: "course_nature" },
    { title: "操作", key: "act", width: 120,
      render: (_, r) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (loading) return <Spin style={{ display: "block", margin: "40px auto" }} />;

  return (
    <>
      <Card title={`课程成绩（${data.length} 门）`} extra={<Button size="small" icon={<PlusOutlined />} onClick={openAdd}>添加</Button>}>
        <DataTable data={data} columns={columns} />
      </Card>
      <Modal title={`${editing ? "编辑" : "添加"}课程`} open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)} width={560} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="course_name" label="课程名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Row gutter={12}>
            <Col span={8}><Form.Item name="score" label="成绩" rules={[{ required: true }]}><InputNumber min={0} max={100} style={{ width: "100%" }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="credit" label="总学分" rules={[{ required: true }]}><InputNumber min={0} max={10} step={0.5} style={{ width: "100%" }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="practical_credit" label="实践学分"><InputNumber min={0} max={10} step={0.5} style={{ width: "100%" }} /></Form.Item></Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}><Form.Item name="semester" label="学期" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="course_nature" label="类别" rules={[{ required: true }]}>
              <Select options={["通识必修","通识选修","学科基础","专业必修","专业选修","集中实践","创新创业","美育劳动"].map((v) => ({ value: v, label: v }))} /></Form.Item></Col>
          </Row>
        </Form>
      </Modal>
    </>
  );
}
