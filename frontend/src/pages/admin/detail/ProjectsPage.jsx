import { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Button, Card, Col, Form, Input, InputNumber, Modal, Popconfirm, Row, Space, Spin, message } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { getProjects, adminAddProject, adminUpdateProject, adminDeleteProject } from "../../../api";
import DataTable from "../../../components/DataTable";

export default function ProjectsPage() {
  const { studentId } = useOutletContext();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  const load = () => getProjects(studentId).then((r) => setData(r.data)).finally(() => setLoading(false));
  useEffect(() => { load(); }, [studentId]);

  const openAdd = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (r) => { setEditing(r); form.setFieldsValue(r); setModalOpen(true); };
  const handleSubmit = async () => {
    const vals = await form.validateFields();
    editing ? await adminUpdateProject(editing.id, vals) : await adminAddProject(studentId, vals);
    message.success(editing ? "更新成功" : "添加成功"); setModalOpen(false); load();
  };
  const handleDelete = async (id) => { await adminDeleteProject(id); message.success("已删除"); load(); };

  const columns = [
    { title: "项目名称", key: "project_name" }, { title: "排名", key: "rank" },
    { title: "描述", key: "description" }, { title: "时间", key: "period" },
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
      <Card title={`项目经历（${data.length} 个）`} extra={<Button size="small" icon={<PlusOutlined />} onClick={openAdd}>添加</Button>}>
        <DataTable data={data} columns={columns} />
      </Card>
      <Modal title={`${editing ? "编辑" : "添加"}项目`} open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)} width={560} destroyOnClose>
        <Form form={form} layout="vertical">
          <Row gutter={12}>
            <Col span={18}><Form.Item name="project_name" label="项目名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={6}><Form.Item name="rank" label="队内排名" rules={[{ required: true }]}><InputNumber min={1} max={10} style={{ width: "100%" }} /></Form.Item></Col>
          </Row>
          <Form.Item name="description" label="描述" rules={[{ required: true }]}><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="period" label="时间" rules={[{ required: true }]}><Input placeholder="如 2023-03 —2023-06" /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}
