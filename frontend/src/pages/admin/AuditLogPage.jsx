import { useState, useEffect } from "react";
import { Card, Spin, Table, Tag, message } from "antd";
import { adminGetAuditLog } from "../../api";

export default function AuditLogPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminGetAuditLog(100).then((r) => setLogs(r.data)).catch(() => message.error("加载失败")).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Card title="操作日志" className="section-card" style={{ marginTop: 24 }}>
      <Table dataSource={logs} rowKey="id" size="middle" pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 条` }}
        columns={[
          { title: "时间", dataIndex: "created_at", key: "time", width: 170 },
          { title: "操作人", dataIndex: "operator", key: "op", width: 110 },
          { title: "操作", dataIndex: "action", key: "action", width: 90,
            render: (v) => <Tag color={v.includes("删除") ? "red" : v.includes("创建") ? "green" : "blue"}>{v}</Tag> },
          { title: "类型", dataIndex: "target_type", key: "type", width: 100 },
          { title: "目标", dataIndex: "target_id", key: "target", width: 120 },
          { title: "详情", dataIndex: "detail", key: "detail" },
        ]}
      />
    </Card>
  );
}
