import { Card } from "antd";
import TrainingPlan from "../../components/TrainingPlan";

export default function TrainingPlanPage() {
  const major = localStorage.getItem("major");

  return (
    <Card title="培养方案" className="section-card" style={{ marginTop: 24 }}>
      <TrainingPlan major={major} />
    </Card>
  );
}
