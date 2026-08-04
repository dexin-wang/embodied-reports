"use client";

import { useEffect, useMemo, useState } from "react";
import { getReportDetails, type Report } from "./reports";

const kindLabels: Record<string, string> = {
  Company: "公司",
  University: "高校",
  "Research Lab": "科研机构",
  Community: "社区",
};

function ExternalIcon() {
  return <span aria-hidden="true">↗</span>;
}

function SourceFrameworkFigure({ report }: { report: Report }) {
  const [unavailable, setUnavailable] = useState(false);
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  const asset = `${basePath}/frameworks/${report.id}.jpg`;
  return (
    <figure className="source-framework">
      {!unavailable ? <img src={asset} alt={`${report.title} 的原始方法框架图`} onError={() => setUnavailable(true)} /> : <div className="framework-unavailable">暂未能从公开 PDF 中导出框架图。请打开原始报告查看方法图。</div>}
      <figcaption>原始方法图 · {report.framework?.caption ?? "自动从公开技术报告 PDF 的 Figure 1/首个方法图提取"}{report.framework?.page ? ` · PDF 第 ${report.framework.page} 页` : ""}</figcaption>
    </figure>
  );
}

function DetailDialog({ report, onClose }: { report: Report; onClose: () => void }) {
  const details = getReportDetails(report);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="report-dialog" role="dialog" aria-modal="true" aria-labelledby="report-dialog-title" onMouseDown={(event) => event.stopPropagation()}>
        <button className="dialog-close" onClick={onClose} aria-label="Close report details">×</button>
        <p className="kicker">REPORT DOSSIER · {report.date}</p>
        <h2 id="report-dialog-title">{report.title}</h2>
        <p className="dialog-meta">{report.organization} · {kindLabels[report.organizationKind ?? "Research Lab"]} · {report.openSource ? "开源" : "未标注开源"}</p>
        <p className="dialog-summary">{report.summary}</p>

        <div className="dialog-block">
          <div className="dialog-block-title"><span>01</span><h3>方法框架</h3></div>
          <SourceFrameworkFigure key={report.id} report={report} />
        </div>

        <div className="dialog-columns">
          <div className="dialog-block">
            <div className="dialog-block-title"><span>02</span><h3>技术重点</h3></div>
            <ul>{details.keyPoints.map((point) => <li key={point}>{point}</li>)}</ul>
          </div>
          <div className="dialog-block">
            <div className="dialog-block-title"><span>03</span><h3>实现功能</h3></div>
            <ul>{details.capabilities.map((item) => <li key={item}>{item}</li>)}</ul>
          </div>
        </div>

        <div className="dialog-block">
          <div className="dialog-block-title"><span>04</span><h3>指标与证据</h3></div>
          <div className="metric-list">
            {details.metrics.map((metric) => <div className="metric" key={`${metric.label}-${metric.value}`}><span>{metric.label}</span><strong>{metric.value}</strong>{metric.note && <p>{metric.note}</p>}</div>)}
          </div>
        </div>

        <div className="dialog-links">
          {report.links.map((link) => <a key={link.label} href={link.url} target="_blank" rel="noreferrer">Open {link.label} <ExternalIcon /></a>)}
        </div>
      </section>
    </div>
  );
}

export function ReportExplorer({ reports }: { reports: Report[] }) {
  const [query, setQuery] = useState("");
  const [field, setField] = useState("All");
  const [organization, setOrganization] = useState("All");
  const [organizationKind, setOrganizationKind] = useState("All");
  const [year, setYear] = useState("All");
  const [month, setMonth] = useState("All");
  const [openOnly, setOpenOnly] = useState(false);
  const [selected, setSelected] = useState<Report | null>(null);

  const fields = useMemo(() => [...new Set(reports.flatMap((report) => report.fields ?? report.tags))].sort(), [reports]);
  const organizations = useMemo(() => [...new Set(reports.map((report) => report.organization))].sort(), [reports]);
  const years = useMemo(() => [...new Set(reports.map((report) => String(report.year)))].sort((a, b) => b.localeCompare(a)), [reports]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return reports.filter((report) => {
      const reportFields = report.fields ?? report.tags;
      const matchesField = field === "All" || reportFields.includes(field);
      const matchesOrganization = organization === "All" || report.organization === organization;
      const matchesKind = organizationKind === "All" || (report.organizationKind ?? "Research Lab") === organizationKind;
      const matchesYear = year === "All" || String(report.year) === year;
      const matchesMonth = month === "All" || report.date.slice(5, 7) === month;
      const matchesOpen = !openOnly || report.openSource;
      const haystack = [report.title, report.organization, report.summary, ...reportFields].join(" ").toLowerCase();
      return matchesField && matchesOrganization && matchesKind && matchesYear && matchesMonth && matchesOpen && (!needle || haystack.includes(needle));
    });
  }, [field, month, openOnly, organization, organizationKind, query, reports, year]);

  const resetFilters = () => { setQuery(""); setField("All"); setOrganization("All"); setOrganizationKind("All"); setYear("All"); setMonth("All"); setOpenOnly(false); };

  return (
    <main>
      <header className="site-header page-shell">
        <a className="brand" href="#top">Embodied Reports</a>
        <nav aria-label="Primary navigation">
          <a className="active" href="#reports">Reports</a>
          <a href="#about">About</a>
          <a href="https://github.com/dexin-wang/embodied-reports" target="_blank" rel="noreferrer">GitHub</a>
        </nav>
      </header>

      <section className="page-shell hero" id="top">
        <p className="eyebrow">A living index · Since 2025</p>
        <h1>Influential embodied intelligence reports, tracked in one place.</h1>
        <p className="intro">技术报告优先、快速浏览。点击任意卡片即可查看方法框架、技术要点、功能与原始指标证据。</p>

        <label className="search-box">
          <span aria-hidden="true" className="search-icon">⌕</span>
          <span className="sr-only">Search reports</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索模型、机构、方法或能力…" />
          {query && <button onClick={() => setQuery("")} aria-label="Clear search">×</button>}
        </label>

        <div className="filter-panel" aria-label="Report filters">
          <label>技术领域<select value={field} onChange={(event) => setField(event.target.value)}><option value="All">全部领域</option>{fields.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>机构<select value={organization} onChange={(event) => setOrganization(event.target.value)}><option value="All">全部机构</option>{organizations.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>机构类型<select value={organizationKind} onChange={(event) => setOrganizationKind(event.target.value)}><option value="All">公司 / 高校 / 科研机构</option>{Object.entries(kindLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label>年份<select value={year} onChange={(event) => setYear(event.target.value)}><option value="All">全部年份</option>{years.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>月份<select value={month} onChange={(event) => setMonth(event.target.value)}><option value="All">全部月份</option>{Array.from({ length: 12 }, (_, index) => String(index + 1).padStart(2, "0")).map((item) => <option key={item} value={item}>{item} 月</option>)}</select></label>
          <label className="open-toggle"><input type="checkbox" checked={openOnly} onChange={(event) => setOpenOnly(event.target.checked)} /> 仅开源</label>
        </div>
      </section>

      <section className="page-shell report-section" id="reports">
        <div className="section-heading">
          <div><p className="kicker">LATEST REPORTS</p><h2>技术报告索引</h2></div>
          <p><strong>{visible.length}</strong> / {reports.length} 篇 · 按最新日期排序</p>
        </div>

        {visible.length > 0 ? (
          <div className="report-grid">
            {visible.map((report) => (
              <article className="report-card interactive" key={report.id} role="button" tabIndex={0} onClick={() => setSelected(report)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelected(report); } }}>
                <div className="card-top">
                  <div><h3>{report.title}</h3><p className="meta">{report.organization} <span>·</span> <time dateTime={report.date}>{report.date}</time></p></div>
                  <div className="badges"><span className="status">{report.verification === "Automated" ? "Auto-checked" : "Seed record"}</span>{report.openSource && <span className="status filled">Open source</span>}</div>
                </div>
                <div className="tags">{(report.fields ?? report.tags).map((tag) => <span key={tag}>{tag}</span>)}</div>
                <p className="summary">{report.summary}</p>
                <div className="card-bottom"><span className="details-hint">点击查看报告档案 <span aria-hidden="true">→</span></span><div className="links">{report.links.slice(0, 2).map((link) => <a key={link.label} href={link.url} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()}>{link.label} <ExternalIcon /></a>)}</div></div>
              </article>
            ))}
          </div>
        ) : <div className="empty"><h3>没有匹配的报告</h3><p>请调整检索条件，或重置筛选器。</p><button onClick={resetFilters}>重置筛选</button></div>}
      </section>

      <section className="page-shell about-grid" id="about"><div><p className="kicker">ABOUT THE INDEX</p><h2>自动核验，来源可追溯。</h2></div><p>每个自动收录条目都保留其主来源、领域判定、机构标签和自动筛选结果。数字指标只在能从原始摘要可靠提取时显示；来源始终是最终依据。</p></section>
      <footer className="page-shell"><p>Embodied Reports</p><p>Primary sources · Automated screening · No manual queue</p></footer>
      {selected && <DetailDialog report={selected} onClose={() => setSelected(null)} />}
    </main>
  );
}
