import { useState, useEffect } from "react";
import { Button, Card, Spin, Empty, message } from "antd";
import { FilePdfOutlined } from "@ant-design/icons";
import { getResume, downloadResumePdf } from "../../api";

/* 简历版式：模板一 · 极简单栏（用户确认版式），
   页面样式在 App.css 的「简历（模板一）」段落，
   与后端 resume-templates/01-minimal.tpl.html 保持一致 */

/* JSON 数字直接渲染即可：44.0 → "44"，3.82 → "3.82" */
const fmtNum = (v) => String(Number(v));

const Bullets = ({ items }) =>
  items && items.length > 0 ? (
    <ul className="r-bullets">
      {items.map((b, i) => <li key={i}>{b}</li>)}
    </ul>
  ) : (
    <div className="r-empty">（暂无描述，请在系统中补充）</div>
  );

const EntryHead = ({ title, role, date }) => (
  <div className="r-entry-head">
    <span>
      <span className="r-title">{title}</span>
      {role && <span className="r-role">{role}</span>}
    </span>
    <span className="r-date">{date}</span>
  </div>
);

export default function ResumePage() {
  const studentId = localStorage.getItem("student_id");
  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    getResume(studentId)
      .then((r) => setResume(r.data))
      .catch(() => message.error("简历加载失败"))
      .finally(() => setLoading(false));
  }, [studentId]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await downloadResumePdf(studentId);
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${resume.basic.name}-简历.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      message.error("PDF 生成失败，请稍后重试");
    } finally {
      setDownloading(false);
    }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!resume) return <Empty description="暂无数据" style={{ marginTop: 100 }} />;

  const b = resume.basic;
  const ed = resume.education;
  const { abilities, keywords } = resume.skills;

  return (
    <div className="resume-page" style={{ marginTop: 24 }}>
      <div className="no-print" style={{ marginBottom: 16 }}>
        <Card size="small">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 15, fontWeight: 500 }}>
              我的简历（内容由系统根据课程、竞赛、实习、项目数据自动生成）
            </span>
            <Button type="primary" icon={<FilePdfOutlined />} loading={downloading} onClick={handleDownload}>
              下载 PDF 简历
            </Button>
          </div>
        </Card>
      </div>

      <div className="resume-sheet">
        <header className="r-header">
          <div>
            <h1>{b.name}</h1>
            <span className="tagline">{b.major} · 本科在读</span>
          </div>
          <div className="contact">
            <span className="ph">联系方式待完善（电话 / 邮箱 / GitHub）</span>
          </div>
        </header>

        <section>
          <h2>教育背景</h2>
          <div className="r-entry">
            <EntryHead
              title={`${b.college} · ${b.major}`}
              role="本科在读"
              date={b.grade_year ? `${b.grade_year} 级 · 在读` : "在读"}
            />
            <div className="r-sub">
              GPA {fmtNum(b.gpa)}（专业排名 {ed.rank} / {ed.rank_total}）· 已修 {b.total_courses} 门课程 / {fmtNum(b.total_credits)} 学分
            </div>
            {ed.core_courses.length > 0 ? (
              <div className="r-sub">
                核心课程：{ed.core_courses.map((c) => `${c.course_name} ${fmtNum(c.score)}`).join(" · ")}
              </div>
            ) : (
              <div className="r-sub r-empty">核心课程：待补充</div>
            )}
          </div>
        </section>

        <section>
          <h2>专业技能</h2>
          {abilities.length === 0 && keywords.length === 0 ? (
            <div className="r-empty">（暂无技能数据，完成课程、竞赛或项目录入后自动生成）</div>
          ) : (
            <>
              {abilities.length > 0 && (
                <div className="r-skill-group">
                  <span className="r-skill-label">核心能力</span>
                  <span className="r-skill-content">{abilities.join(" / ")}</span>
                </div>
              )}
              {keywords.length > 0 && (
                <div className="r-skill-group">
                  <span className="r-skill-label">技术关键词</span>
                  <span className="r-skill-content">{keywords.join(" / ")}</span>
                </div>
              )}
            </>
          )}
        </section>

        <section>
          <h2>实习经历</h2>
          {resume.internships.length === 0 ? (
            <div className="r-empty">（暂无实习经历）</div>
          ) : (
            resume.internships.map((it, i) => (
              <div className="r-entry" key={i}>
                <EntryHead title={it.company} role={it.position} date={it.period} />
                <Bullets items={it.bullets} />
              </div>
            ))
          )}
        </section>

        <section>
          <h2>项目经历</h2>
          {resume.projects.length === 0 ? (
            <div className="r-empty">（暂无项目经历）</div>
          ) : (
            resume.projects.map((p, i) => (
              <div className="r-entry" key={i}>
                <EntryHead title={p.project_name} role={`队内排名第 ${p.rank}`} date={p.period} />
                <Bullets items={p.bullets} />
              </div>
            ))
          )}
        </section>

        <section>
          <h2>竞赛获奖</h2>
          {resume.competitions.length === 0 ? (
            <div className="r-empty">（暂无竞赛获奖）</div>
          ) : (
            resume.competitions.map((c, i) => (
              <div className="r-comp" key={i}>
                <span className="r-comp-name">{c.comp_name}</span>
                <span className="r-comp-meta">
                  {[c.level, c.award, `队内排名第 ${c.rank}`, c.date].filter(Boolean).join(" · ")}
                </span>
              </div>
            ))
          )}
        </section>

        <div className="r-footer">本简历由人岗匹配评估系统自动生成</div>
      </div>
    </div>
  );
}
