import { Table } from "antd";

export default function DataTable({ data, columns }) {
  const tableColumns = columns.map(({ key, sorter, ...rest }) => ({
    ...rest,
    dataIndex: key,
    key,
    sorter: sorter
      ? (a, b) => {
          const va = a[key];
          const vb = b[key];
          if (typeof va === "number" && typeof vb === "number") return va - vb;
          return String(va).localeCompare(String(vb), "zh");
        }
      : undefined,
  }));

  return (
    <Table
      columns={tableColumns}
      dataSource={data}
      rowKey="id"
      pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (t) => `共 ${t} 条`, pageSizeOptions: ["5", "10", "20", "50"] }}
      size="middle"
      scroll={{ x: "max-content" }}
    />
  );
}
