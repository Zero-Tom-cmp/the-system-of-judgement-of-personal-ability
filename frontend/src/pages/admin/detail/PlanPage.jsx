import { useOutletContext } from "react-router-dom";
import { Card } from "antd";
import TrainingPlan from "../../../components/TrainingPlan";

export default function PlanPage() {
  const { info } = useOutletContext();
  return (
    <Card title="培养方案"><TrainingPlan major={info?.major} /></Card>
  );
}
