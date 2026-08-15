import ReactECharts from "echarts-for-react";

import { Empty } from "antd";

export default function AbilityRadar({ abilities }) {
  if (!abilities) return null;

  const dims = abilities.ability_dims || [];
  if (dims.length === 0) {
    return <Empty description="暂无能力评估数据，请先添加课程、竞赛、实习或项目数据" />;
  }
  const scores = dims.map((d) => abilities.abilities[d]?.score || 0);

  const option = {
    tooltip: {
      trigger: "item",
      formatter: (params) => {
        const idx = params.dataIndex;
        return `${dims[idx]}：<b>${scores[idx]} 分</b>`;
      },
    },
    radar: {
      center: ["50%", "50%"],
      radius: "65%",
      indicator: dims.map((d) => ({ name: d, max: 100 })),
      axisName: {
        color: "#333",
        fontSize: 13,
        fontWeight: "bold",
      },
      shape: "polygon",
      splitNumber: 5,
      splitArea: {
        areaStyle: {
          color: ["rgba(24, 144, 255, 0.02)", "rgba(24, 144, 255, 0.02)"],
        },
      },
    },
    series: [
      {
        type: "radar",
        data: [{ value: scores, name: abilities.name, areaStyle: { color: "rgba(24, 144, 255, 0.25)" } }],
        symbol: "circle",
        symbolSize: 6,
        lineStyle: { color: "#1890ff", width: 2 },
        itemStyle: { color: "#1890ff", borderColor: "#fff", borderWidth: 1 },
        areaStyle: { color: "rgba(24, 144, 255, 0.15)" },
      },
    ],
  };

  return (
    <div className="radar-container">
      <ReactECharts option={option} style={{ height: 380, width: "100%" }} />
    </div>
  );
}
