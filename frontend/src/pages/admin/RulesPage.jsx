import { useState, useEffect } from "react";
import { Card, InputNumber, Spin, Table, Tabs, message } from "antd";
import { adminGetRules, adminUpdateRule } from "../../api";

export default function RulesPage() {
  const [rules, setRules] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      adminGetRules("ability_config"),
      adminGetRules("course_mapping"),
      adminGetRules("job_profile"),
    ]).then(([a, c, j]) => { setRules({ ability_config: a.data, course_mapping: c.data, job_profile: j.data }); })
      .catch(() => message.error("加载失败"))
      .finally(() => setLoading(false));
  }, []);

  const save = async (type, id, data) => {
    try { await adminUpdateRule(type, id, data); message.success("已保存"); }
    catch (err) { message.error("保存失败"); }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Card title="评估规则配置" className="section-card" style={{ marginTop: 24 }}>
      <Tabs items={[
        {
          key: "ability", label: "能力维度配置",
          children: (
            <Table dataSource={rules.ability_config || []} rowKey="id" size="middle" pagination={false}
              columns={[
                { title: "专业", dataIndex: "major", key: "major" },
                { title: "能力维度", dataIndex: "ability_dimension", key: "dim" },
                { title: "权重", dataIndex: "weight", key: "weight",
                  render: (v, r) => (
                    <InputNumber size="small" min={0} max={1} step={0.05} defaultValue={v}
                      onBlur={(e) => save("ability_config", r.id, { weight: parseFloat(e.target.value) || v })} style={{ width: 80 }} />
                  )},
              ]} />
          ),
        },
        {
          key: "course", label: "课程→能力映射",
          children: (
            <Table dataSource={rules.course_mapping || []} rowKey="id" size="middle" pagination={{ pageSize: 15 }}
              columns={[
                { title: "课程名称", dataIndex: "course_name", key: "course" },
                { title: "能力维度", dataIndex: "ability_dimension", key: "dim" },
                { title: "贡献权重", dataIndex: "contribution_weight", key: "weight",
                  render: (v, r) => (
                    <InputNumber size="small" min={0} max={2} step={0.05} defaultValue={v}
                      onBlur={(e) => save("course_mapping", r.id, { contribution_weight: parseFloat(e.target.value) || v })} style={{ width: 80 }} />
                  )},
              ]} />
          ),
        },
        {
          key: "job", label: "岗位能力要求",
          children: (
            <Table dataSource={rules.job_profile || []} rowKey="id" size="middle" pagination={false}
              columns={[
                { title: "岗位", dataIndex: "job_name", key: "job" },
                { title: "能力维度", dataIndex: "ability_dimension", key: "dim" },
                { title: "要求分数", dataIndex: "required_level", key: "req",
                  render: (v, r) => (
                    <InputNumber size="small" min={0} max={100} defaultValue={v}
                      onBlur={(e) => save("job_profile", r.id, { required_level: parseFloat(e.target.value) || v })} style={{ width: 80 }} />
                  )},
                { title: "权重", dataIndex: "importance_weight", key: "w",
                  render: (v, r) => (
                    <InputNumber size="small" min={0} max={1} step={0.05} defaultValue={v}
                      onBlur={(e) => save("job_profile", r.id, { importance_weight: parseFloat(e.target.value) || v })} style={{ width: 80 }} />
                  )},
              ]} />
          ),
        },
      ]} />
    </Card>
  );
}
