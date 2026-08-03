"use client";

import { useMemo, useState } from "react";
import type { Report } from "./reports";

const filters = ["All", "VLA", "Humanoid", "World Models", "Manipulation", "Datasets"];

function ExternalIcon() {
  return <span aria-hidden="true">↗</span>;
}

export function ReportExplorer({ reports }: { reports: Report[] }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All");
  const [openOnly, setOpenOnly] = useState(false);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return reports.filter((report) => {
      const matchesFilter = filter === "All" || report.tags.includes(filter);
      const matchesOpen = !openOnly || report.openSource;
      const haystack = [report.title, report.organization, report.summary, ...report.tags]
        .join(" ")
        .toLowerCase();
      return matchesFilter && matchesOpen && (!needle || haystack.includes(needle));
    });
  }, [filter, openOnly, query, reports]);

  return (
    <main>
      <header className="site-header page-shell">
        <a className="brand" href="#top">Embodied Reports</a>
        <nav aria-label="Primary navigation">
          <a className="active" href="#reports">Reports</a>
          <a href="#organizations">Organizations</a>
          <a href="#about">About</a>
          <a href="https://github.com/dexin-wang/embodied-reports" target="_blank" rel="noreferrer">GitHub</a>
        </nav>
      </header>

      <section className="page-shell hero" id="top">
        <p className="eyebrow">A living index · Since 2025</p>
        <h1>Influential embodied intelligence reports, tracked in one place.</h1>
        <p className="intro">Technical reports from research companies and labs—organized for fast scanning, grounded in primary sources, and continuously updated.</p>

        <label className="search-box">
          <span aria-hidden="true" className="search-icon">⌕</span>
          <span className="sr-only">Search reports</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search reports, models, organizations, or methods…" />
          {query && <button onClick={() => setQuery("")} aria-label="Clear search">×</button>}
        </label>

        <div className="controls" aria-label="Report filters">
          <div className="filter-row">
            {filters.map((item) => (
              <button key={item} className={filter === item ? "selected" : ""} onClick={() => setFilter(item)}>{item}</button>
            ))}
          </div>
          <label className="open-toggle"><input type="checkbox" checked={openOnly} onChange={(event) => setOpenOnly(event.target.checked)} /> Open source only</label>
        </div>
      </section>

      <section className="page-shell report-section" id="reports">
        <div className="section-heading">
          <div><p className="kicker">LATEST REPORTS</p><h2>{filter === "All" ? "All technical reports" : filter}</h2></div>
          <p><strong>{visible.length}</strong> of {reports.length} reports · Newest first</p>
        </div>

        {visible.length > 0 ? (
          <div className="report-grid">
            {visible.map((report) => (
              <article className="report-card" key={report.id}>
                <div className="card-top">
                  <div>
                    <h3>{report.title}</h3>
                    <p className="meta">{report.organization} <span>·</span> <time dateTime={report.date}>{report.date}</time></p>
                  </div>
                  <div className="badges">
                    {report.featured && <span className="status filled">Featured</span>}
                    <span className="status">✓ Verified</span>
                  </div>
                </div>
                <div className="tags">{report.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
                <p className="summary">{report.summary}</p>
                <div className="links">
                  {report.links.map((link) => <a key={link.label} href={link.url} target="_blank" rel="noreferrer">{link.label} <ExternalIcon /></a>)}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty"><h3>No matching reports</h3><p>Try another keyword or clear one of the filters.</p><button onClick={() => { setQuery(""); setFilter("All"); setOpenOnly(false); }}>Reset filters</button></div>
        )}
      </section>

      <section className="page-shell about-grid" id="about">
        <div><p className="kicker">ABOUT THE INDEX</p><h2>Company reports first. Evidence over hype.</h2></div>
        <p>We track consequential releases across VLA, humanoids, world models, manipulation, tactile intelligence, datasets and embodied systems. Publication venue is not an inclusion requirement; a verifiable technical contribution is.</p>
      </section>

      <footer className="page-shell"><p>Embodied Reports</p><p>Primary sources · Transparent metadata · Automated discovery</p></footer>
    </main>
  );
}
