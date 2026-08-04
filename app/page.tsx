import { ReportExplorer } from "./report-explorer";
import { reports } from "./reports";
import discoveredReports from "../data/discovered.json";
import catalogReports from "../data/catalog.json";
import enrichedReports from "../data/enriched.json";
import type { Report } from "./reports";

export default function Home() {
  const byId = new Map<string, Report>();
  // Later layers override earlier records. Enrichment therefore adds detailed
  // content without losing the stable catalog if live discovery is unavailable.
  for (const report of [...reports, ...(catalogReports as Report[]), ...(discoveredReports as Report[]), ...(enrichedReports as Report[])]) byId.set(report.id, report);
  const merged = [...byId.values()].sort((a, b) => b.date.localeCompare(a.date));
  return <ReportExplorer reports={merged} />;
}
