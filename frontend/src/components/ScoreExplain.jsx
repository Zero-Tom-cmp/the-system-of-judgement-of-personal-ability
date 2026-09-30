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

/**
 * 把各条明细的原始贡献值按比例摊到该维度的最终得分上。
 *
 * 后端的 value 是原始贡献值（量纲 0~40），score 是换算成百分制之后的分数，
 * 两者差一个比例。直接显示 value 会出现"明细加起来 18.9、合计写 47.4"的情况，
 * 学生一加就发现对不上，所以这里统一换算到 score 的口径。
 *
 * 逐项四舍五入会留下 ±0.1 的零头，仍然加不平，因此用最大余额法：
 * 先各自向下取整，再把余额按小数部分从大到小补回去，保证总和分毫不差。
 */
function allocate(values, total, digits = 1) {
  const sum = values.reduce((a, b) => a + b, 0);
  if (sum <= 0 || total <= 0) return values.map(() => 0);

  const factor = 10 ** digits;
  const exact = values.map((v) => (v / sum) * total * factor);
  const out = exact.map(Math.floor);
  let remainder = Math.round(total * factor) - out.reduce((a, b) => a + b, 0);

  const byFraction = exact
    .map((v, i) => ({ i, frac: v - Math.floor(v) }))
    .sort((a, b) => b.frac - a.frac);
  for (let k = 0; k < byFraction.length && remainder > 0; k++, remainder--) {
    out[byFraction[k].i] += 1;
  }
  return out.map((v) => v / factor);
}

// 标签配色按"占该维度总分的比例"来，这样换算前后深浅分布不变
function tagColor(value, total) {
  if (total <= 0) return "default";
  if (value / total >= 0.25) return "green";
  if (value / total >= 0.1) return "blue";
  return "default";
}

export default function ScoreExplain({ abilities }) {
  if (!abilities || !abilities.abilities) return <Empty description="暂无数据" />;

  const dims = abilities.ability_dims;
  const items = dims.map((dim) => {
    const data = abilities.abilities[dim];
    if (!data) return null;

    const details = data.details || [];
    const sortedDetails = [...details].sort((a, b) => b.value - a.value);
    const parts = allocate(sortedDetails.map((x) => x.value), data.score);

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
                    <Tag color={tagColor(parts[idx], data.score)}>
                      贡献 +{parts[idx].toFixed(1)} 分
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
