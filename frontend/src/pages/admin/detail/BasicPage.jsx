import { useOutletContext } from "react-router-dom";
import { Card, Descriptions, Tag } from "antd";

export default function BasicPage() {
  const { info } = useOutletContext();
  return (
    <Card title="基本信息">
      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="姓名">{info?.name}</Descriptions.Item>
        <Descriptions.Item label="学号">{info?.student_id}</Descriptions.Item>
        <Descriptions.Item label="学院">{info?.college}</Descriptions.Item>
        <Descriptions.Item label="专业">{info?.major}</Descriptions.Item>
        <Descriptions.Item label="班级">{info?.class_name}</Descriptions.Item>
        <Descriptions.Item label="GPA"><Tag color="blue">{info?.gpa}</Tag></Descriptions.Item>
        <Descriptions.Item label="已修学分"><Tag color="green">{info?.total_credits} 学分</Tag></Descriptions.Item>
        <Descriptions.Item label="英语证书">
          {/* 仅金融学设有"英语能力"维度，其他专业填了也不参与评分（见 evaluation._eval_english_cert） */}
          {info?.english_cert
            ? <Tag color="purple">{info.english_cert} {info.english_score}</Tag>
            : <span style={{ color: "#999" }}>未填写</span>}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}
