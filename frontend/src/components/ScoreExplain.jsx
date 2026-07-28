import { Collapse, Tag, Empty } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";

const DIM_NAMES = {
  编程能力: "编程能力",
  算法思维: "算法思维",
  工程实践: "工程实践",
  团队协作: "团队协作",
  沟通表达: "沟通表达",
  学习能力: "学习能力",
  数理分析: "数理分析",
  经济洞察: "经济洞察",
  风险意识: "风险意识",
  财务技能: "财务技能",
  英语能力: "英语能力",
};

const DIM_DESCRIPTIONS = {
  编程能力: "代码编写、调试及软件设计能力",
  算法思维: "算法理解、设计及复杂度分析能力",
  工程实践: "软件开发全流程管理、工具使用及系统部署能力",
  团队协作: "团队沟通、任务分工及协作推进能力",
  沟通表达: "文档撰写、演讲汇报及技术沟通能力",
  学习能力: "新技术学习、知识迁移及自主学习能力",
  数理分析: "数学建模、数据处理及统计分析能力",
  经济洞察: "宏观/微观经济分析、行业判断能力",
  风险意识: "风险识别、评估及管控能力",
  财务技能: "财务分析、估值建模及会计实务能力",
  英语能力: "英语听说读写及专业英语应用能力",
};

export default function ScoreExplain({ abilities }) {
  if (!abilities || !abilities.abilities) return <Empty description="暂无数据" />;

  const dims = abilities.ability_dims;
  const items = dims.map((dim) => {
    const data = abilities.abilities[dim];
    if (!data) return null;

    const details = data.details || [];
    const sortedDetails = [...details].sort((a, b) => b.value - a.value);

    return {
      key: dim,
      label: (
        <span>
          <span style={{ fontWeight: "bold" }}>{dim}</span>
          <Tag color="blue" style={{ marginLeft: 8 }}>
            {data.score} 分
          </Tag>
          <span style={{ color: "#888", fontSize: 12, marginLeft: 8 }}>
            {DIM_DESCRIPTIONS[dim] || ""}
          </span>
        </span>
      ),
      children: (
        <div>
          {sortedDetails.length > 0 ? (
            <div>
              <div style={{ marginBottom: 8, color: "#666", fontSize: 13 }}>
                <InfoCircleOutlined /> 该维度得分由以下数据贡献：
              </div>
              {sortedDetails.map((item, idx) => (
                <div key={idx} className="explain-item" style={{ padding: "6px 0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ fontWeight: 500 }}>{item.source}</span>
                    <Tag color={item.value >= 5 ? "green" : item.value >= 2 ? "blue" : "default"}>
                      贡献 +{item.value} 分
                    </Tag>
                  </div>
                  <div style={{ fontSize: 12, color: "#999" }}>{item.comment}</div>
                </div>
              ))}
              <div style={{ marginTop: 8, textAlign: "right", fontWeight: "bold", color: "#1890ff" }}>
                合计：{data.score} 分
              </div>
            </div>
          ) : (
            <Empty description="该维度暂无直接数据支撑" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </div>
      ),
    };
  }).filter(Boolean);

  return (
    <Collapse
      items={items}
      style={{ marginTop: 16 }}
      size="small"
      expandIconPosition="end"
    />
  );
}
