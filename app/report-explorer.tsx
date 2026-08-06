"use client";

import { useEffect, useMemo, useState } from "react";
import { getReportDetails, type Report } from "./reports";

const standardFields = [
  "Vision-language-action", "Large language models", "Humanoid intelligence",
  "Whole-body control", "World models", "Robot manipulation",
  "Dexterous manipulation", "Tactile intelligence", "Data & benchmarks",
  "Robot systems", "Embodied AI",
];
const allowedFields = new Set(standardFields);

function displayFields(report: Report) {
  return (report.fields ?? report.tags).filter((field) => allowedFields.has(field));
}

const kindLabels: Record<string, string> = {
  Company: "公司",
  University: "高校",
  "Research Lab": "科研机构",
  Community: "社区",
};

function ExternalIcon() {
  return <span aria-hidden="true">↗</span>;
}

function SourceFrameworkFigure({ report, compact = false }: { report: Report; compact?: boolean }) {
  const [unavailable, setUnavailable] = useState(false);
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  const asset = report.framework?.imageUrl ?? `${basePath}/frameworks/${report.id}.jpg`;
  return (
    <figure className={compact ? "source-framework card-framework" : "source-framework"}>
      {!unavailable ? <img src={asset} alt={`${report.title} 的原始方法框架图`} onError={() => setUnavailable(true)} /> : <div className="framework-unavailable">暂未找到可可靠提取的原始方法框架图</div>}
      <>{!compact && <figcaption>原始方法图 · {report.framework?.caption ?? "来源为公开技术报告 PDF 或官方项目页"}{report.framework?.page ? ` · PDF 第 ${report.framework.page} 页` : ""}</figcaption>}</>
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
            <ol className="detail-list">{details.keyPoints.map((point) => <li key={point}>{point}</li>)}</ol>
          </div>
          <div className="dialog-block">
            <div className="dialog-block-title"><span>03</span><h3>实现功能</h3></div>
            <ol className="detail-list">{details.capabilities.map((item) => <li key={item}>{item}</li>)}</ol>
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
  const [year, setYear] = useState("All");
  const [month, setMonth] = useState("All");
  const [openOnly, setOpenOnly] = useState(false);
  const [selected, setSelected] = useState<Report | null>(null);

  const fields = useMemo(() => standardFields.filter((item) => reports.some((report) => displayFields(report).includes(item))), [reports]);
  const organizations = useMemo(() => [...new Set(reports.map((report) => report.organization))].sort(), [reports]);
  const years = useMemo(() => [...new Set(reports.map((report) => String(report.year)))].sort((a, b) => b.localeCompare(a)), [reports]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return reports.filter((report) => {
      const reportFields = displayFields(report);
      const matchesField = field === "All" || reportFields.includes(field);
      const matchesOrganization = organization === "All" || report.organization === organization;
      const matchesYear = year === "All" || String(report.year) === year;
      const matchesMonth = month === "All" || report.date.slice(5, 7) === month;
      const matchesOpen = !openOnly || report.openSource;
      const haystack = [report.title, report.organization, report.summary, ...reportFields].join(" ").toLowerCase();
      return matchesField && matchesOrganization && matchesYear && matchesMonth && matchesOpen && (!needle || haystack.includes(needle));
    });
  }, [field, month, openOnly, organization, query, reports, year]);

  const resetFilters = () => { setQuery(""); setField("All"); setOrganization("All"); setYear("All"); setMonth("All"); setOpenOnly(false); };

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

        <div className="filter-facets" aria-label="Report filters">
          <details className="facet" open>
            <summary>年份 <span>{year === "All" ? "全部" : year}</span></summary>
            <div className="facet-options"><button type="button" className={year === "All" ? "selected" : ""} onClick={() => setYear("All")}>全部</button>{years.map((item) => <button type="button" className={year === item ? "selected" : ""} key={item} onClick={() => setYear(item)}>{item}</button>)}</div>
          </details>
          <details className="facet" open>
            <summary>技术领域 <span>{field === "All" ? "全部" : field}</span></summary>
            <div className="facet-options"><button type="button" className={field === "All" ? "selected" : ""} onClick={() => setField("All")}>全部</button>{fields.map((item) => <button type="button" className={field === item ? "selected" : ""} key={item} onClick={() => setField(item)}>{item}</button>)}</div>
          </details>
          <details className="facet">
            <summary>机构 <span>{organization === "All" ? "全部" : organization}</span></summary>
            <div className="facet-options"><button type="button" className={organization === "All" ? "selected" : ""} onClick={() => setOrganization("All")}>全部</button>{organizations.map((item) => <button type="button" className={organization === item ? "selected" : ""} key={item} onClick={() => setOrganization(item)}>{item}</button>)}</div>
          </details>
          <details className="facet">
            <summary>月份 <span>{month === "All" ? "全部" : `${month} 月`}</span></summary>
            <div className="facet-options"><button type="button" className={month === "All" ? "selected" : ""} onClick={() => setMonth("All")}>全部</button>{Array.from({ length: 12 }, (_, index) => String(index + 1).padStart(2, "0")).map((item) => <button type="button" className={month === item ? "selected" : ""} key={item} onClick={() => setMonth(item)}>{item} 月</button>)}</div>
          </details>
          <details className="facet">
            <summary>开源状态 <span>{openOnly ? "仅开源" : "全部"}</span></summary>
            <div className="facet-options"><button type="button" className={!openOnly ? "selected" : ""} onClick={() => setOpenOnly(false)}>全部</button><button type="button" className={openOnly ? "selected" : ""} onClick={() => setOpenOnly(true)}>仅开源</button></div>
          </details>
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
                <SourceFrameworkFigure report={report} compact />
                <div className="tags">{displayFields(report).map((tag) => <span key={tag}>{tag}</span>)}</div>
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
