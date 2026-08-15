import { useState } from "react";
import { Button, Card, Modal, Space, Upload, Tag, message } from "antd";
import { UploadOutlined, DownloadOutlined, BookOutlined, TrophyOutlined, ExperimentOutlined, ProjectOutlined, ImportOutlined, WarningOutlined } from "@ant-design/icons";
import { adminImportCsv, adminDownloadTemplate, adminImportAll, adminDownloadAllTemplate, adminDownloadConflicts } from "../../api";

export default function ImportPage() {
  const [csvModalOpen, setCsvModalOpen] = useState(false);
  const [csvType, setCsvType] = useState("courses");
  const [csvFile, setCsvFile] = useState(null);
  const [csvLoading, setCsvLoading] = useState(false);

  const [allModalOpen, setAllModalOpen] = useState(false);
  const [allFile, setAllFile] = useState(null);
  const [allLoading, setAllLoading] = useState(false);

  // 持久化冲突数据（页面刷新后仍可下载）
  const [conflictResults, setConflictResults] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem("import_conflicts") || "null"); } catch { return null; }
  });

  const saveConflicts = (data) => {
    setConflictResults(data);
    sessionStorage.setItem("import_conflicts", JSON.stringify(data));
  };
  const clearConflicts = () => {
    setConflictResults(null);
    sessionStorage.removeItem("import_conflicts");
  };

  const labels = { courses: "课程", competitions: "竞赛", internships: "实习", projects: "项目" };

  const openCsv = (type) => { setCsvType(type); setCsvFile(null); setCsvModalOpen(true); };

  const handleCsvImport = async () => {
    if (!csvFile) { message.warning("请选择文件"); return; }
    setCsvLoading(true);
    try {
      const res = await adminImportCsv(csvType, csvFile);
      const errs = res.data.errors || [];
      const conflictCount = errs.filter((e) => typeof e === "object" && e.reason?.includes("冲突")).length;
      const otherErrs = errs.length - conflictCount;
      let msg = `导入完成: 成功 ${res.data.success} 条`;
      if (conflictCount > 0) msg += `, 冲突跳过 ${conflictCount} 条`;
      if (otherErrs > 0) msg += `, 失败 ${otherErrs} 条`;
      message.info(msg);
      if (conflictCount > 0) {
        saveConflicts({ errors: errs, sheet: labels[csvType] });
        downloadConflicts(errs, labels[csvType]);  // 自动下载
        message.info(`${msg}，冲突数据已自动下载`);
      } else if (otherErrs > 0) {
        Modal.warning({ title: "部分数据导入失败", content: <div>{errs.map((e, i) => <div key={i}>{typeof e === "string" ? e : e.reason}</div>)}</div> });
      }
      setCsvModalOpen(false);
    } catch (err) { message.error(err.response?.data?.detail || "导入失败"); }
    finally { setCsvLoading(false); }
  };

  const handleAllImport = async () => {
    if (!allFile) { message.warning("请选择文件"); return; }
    setAllLoading(true);
    try {
      const res = await adminImportAll(allFile);
      const results = res.data.results || {};
      let totalConflicts = 0;
      let totalErrors = 0;
      let allConflictErrors = [];

      const parts = Object.entries(results).map(([sheet, r]) => {
        const errs = r.errors || [];
        const conflicts = errs.filter((e) => typeof e === "object" && e.reason?.includes("冲突"));
        const other = errs.filter((e) => !(typeof e === "object" && e.reason?.includes("冲突")));
        totalConflicts += conflicts.length;
        totalErrors += other.length;
        if (conflicts.length > 0) allConflictErrors.push({ sheet, errors: conflicts });

        let status = `${r.success} 条成功`;
        if (conflicts.length > 0) status += `, ${conflicts.length} 条冲突跳过`;
        if (other.length > 0) status += `, ${other.length} 条失败`;
        if (r.processed !== undefined && r.processed < r.total_rows) status += ` (处理 ${r.processed}/${r.total_rows}, 未完成)`;
        return `${sheet}: ${status}`;
      }).join("\n");

      if (totalConflicts > 0) {
        saveConflicts({ errors: allConflictErrors, sheet: "综合" });
        downloadAllConflicts(allConflictErrors);  // 自动下载
        Modal.info({
          title: `检测到 ${totalConflicts} 条冲突数据（已自动下载）`,
          content: <pre style={{ fontSize: 12, maxHeight: 200, overflow: "auto" }}>{parts}</pre>,
        });
      } else {
        Modal.info({ title: res.data.message, content: <pre style={{ fontSize: 13 }}>{parts}</pre> });
      }
      setAllModalOpen(false);
    } catch (err) { message.error(err.response?.data?.detail || "导入失败"); }
    finally { setAllLoading(false); }
  };

  const downloadConflicts = async (errors, sheet) => {
    try {
      const res = await adminDownloadConflicts(errors, sheet);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a"); a.href = url; a.download = `conflicts_${sheet}.csv`; a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) { message.error("下载失败"); }
  };

  const downloadAllConflicts = async (allErrors) => {
    try {
      // 合并所有Sheet的冲突数据
      const merged = [];
      for (const group of allErrors) {
        for (const e of group.errors) {
          merged.push({ ...e, _sheet: group.sheet });
        }
      }
      const res = await adminDownloadConflicts(merged, "综合");
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a"); a.href = url; a.download = `conflicts_综合.zip`; a.click();
      window.URL.revokeObjectURL(url);
      message.success("冲突数据已下载");
    } catch (err) { message.error("下载失败"); }
  };

  const downloadTpl = async (type) => {
    try {
      const res = await adminDownloadTemplate(type);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a"); a.href = url; a.download = `${type}_template.csv`; a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) { message.error("下载失败"); }
  };

  const downloadAllTpl = async () => {
    try {
      const res = await adminDownloadAllTemplate();
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a"); a.href = url; a.download = "student_data_template.xlsx"; a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) { message.error("下载失败"); }
  };

  return (
    <div style={{ marginTop: 24 }}>
      <Card title="综合导入（Excel 一键导入全部数据）" className="section-card">
        <Space direction="vertical" size="middle">
          <span style={{ color: "#666" }}>一个 Excel 文件包含 5 个 Sheet（学生信息/课程/竞赛/实习/项目），自动分配到各模块</span>
          <span style={{ color: "#fa8c16", fontSize: 13 }}>
            <WarningOutlined /> 课程/竞赛/实习/项目中，同一学号下已存在的同名称记录将被跳过，可下载冲突数据
          </span>
          <Space>
            <Button icon={<DownloadOutlined />} onClick={downloadAllTpl}>下载 Excel 模板</Button>
            <Button type="primary" icon={<ImportOutlined />} onClick={() => setAllModalOpen(true)}>上传 Excel 导入</Button>
          </Space>
        </Space>
      </Card>

      <Card title="分模块 CSV 导入" className="section-card">
        <Space wrap size="middle">
          {Object.entries(labels).map(([k, v]) => (
            <Space key={k}>
              <Button icon={<DownloadOutlined />} onClick={() => downloadTpl(k)}>{v}模板</Button>
              <Button type="primary" icon={<ImportOutlined />} onClick={() => openCsv(k)}>导入{v}</Button>
            </Space>
          ))}
        </Space>
      </Card>

      {/* CSV Import Modal */}
      <Modal title={`导入${labels[csvType]} CSV`} open={csvModalOpen} onOk={handleCsvImport} onCancel={() => setCsvModalOpen(false)} confirmLoading={csvLoading}>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Upload accept=".csv" maxCount={1} beforeUpload={(f) => { setCsvFile(f); return false; }} onRemove={() => setCsvFile(null)}
            fileList={csvFile ? [{ uid: "-1", name: csvFile.name, status: "done" }] : []}>
            <Button icon={<UploadOutlined />}>选择文件</Button>
          </Upload>
        </Space>
      </Modal>

      {/* 上次导入冲突 */}
      {conflictResults && (
        <Card
          title={<><WarningOutlined style={{ color: "#fa8c16" }} /> 上次导入冲突数据</>}
          className="section-card"
          extra={<Button size="small" onClick={clearConflicts}>清除记录</Button>}
        >
          <p style={{ color: "#666", marginBottom: 12 }}>
            以下为最近一次导入时跳过的冲突数据，可下载 CSV 查看详情并修正后重新导入。
          </p>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={() => {
              const group = conflictResults;
              if (Array.isArray(group.errors) && group.errors.length > 0 && group.errors[0].sheet) {
                downloadAllConflicts(group.errors);
              } else {
                downloadConflicts(group.errors, group.sheet);
              }
            }}
          >
            下载冲突数据 CSV
          </Button>
        </Card>
      )}

      {/* Excel Import Modal */}
      <Modal title="综合导入 Excel" open={allModalOpen} onOk={handleAllImport} onCancel={() => setAllModalOpen(false)} confirmLoading={allLoading}>
        <Space direction="vertical" style={{ width: "100%" }}>
          <div style={{ color: "#666", fontSize: 13 }}>5个Sheet：学生基本信息、课程成绩、竞赛获奖、企业实习、项目经历</div>
          <Upload accept=".xlsx,.xls" maxCount={1} beforeUpload={(f) => { setAllFile(f); return false; }} onRemove={() => setAllFile(null)}
            fileList={allFile ? [{ uid: "-1", name: allFile.name, status: "done" }] : []}>
            <Button icon={<UploadOutlined />}>选择 Excel 文件</Button>
          </Upload>
        </Space>
      </Modal>
    </div>
  );
}
