import { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Button, Card, Col, Form, Input, InputNumber, Modal, Popconfirm, Row, Select, Space, Spin, message } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { getCompetitions, adminAddCompetition, adminUpdateCompetition, adminDeleteCompetition } from "../../../api";
import DataTable from "../../../components/DataTable";

export default function CompetitionsPage() {
  const { studentId } = useOutletContext();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  const load = () => getCompetitions(studentId).then((r) => setData(r.data)).finally(() => setLoading(false));
  useEffect(() => { load(); }, [studentId]);

  const openAdd = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (r) => { setEditing(r); form.setFieldsValue(r); setModalOpen(true); };
  const handleSubmit = async () => {
    const vals = await form.validateFields();
    editing ? await adminUpdateCompetition(editing.id, vals) : await adminAddCompetition(studentId, vals);
    message.success(editing ? "更新成功" : "添加成功"); setModalOpen(false); load();
  };
  const handleDelete = async (id) => { await adminDeleteCompetition(id); message.success("已删除"); load(); };

  const columns = [
    { title: "竞赛名称", key: "comp_name" }, { title: "级别", key: "level", sorter: true },
    { title: "获奖", key: "award" }, { title: "排名", key: "rank" }, { title: "时间", key: "date" },
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
      <Card title={`竞赛获奖（${data.length} 项）`} extra={<Button size="small" icon={<PlusOutlined />} onClick={openAdd}>添加</Button>}>
        <DataTable data={data} columns={columns} />
      </Card>
      <Modal title={`${editing ? "编辑" : "添加"}竞赛`} open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)} width={560} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="comp_name" label="竞赛名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Row gutter={12}>
            <Col span={8}><Form.Item name="level" label="级别" rules={[{ required: true }]}><Select options={[{ value: "国家级" }, { value: "省级" }]} /></Form.Item></Col>
            <Col span={8}><Form.Item name="award" label="获奖" rules={[{ required: true }]}><Select options={["一等奖","二等奖","三等奖","参与奖"].map((v) => ({ value: v, label: v }))} /></Form.Item></Col>
            <Col span={8}><Form.Item name="rank" label="队内排名" rules={[{ required: true }]}><InputNumber min={1} max={10} style={{ width: "100%" }} /></Form.Item></Col>
          </Row>
          <Form.Item name="date" label="时间" rules={[{ required: true }]}><Input placeholder="如 2023-05" /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}
