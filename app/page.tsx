import { ReportExplorer } from "./report-explorer";
import { reports } from "./reports";
import verifiedReports from "../data/verified.json";
import type { Report } from "./reports";

export default function Home() {
  const byId = new Map<string, Report>();
  // The static records are the initial source-checked set.  Dynamic records
  // only appear here after the automated official-site and impact review.
  for (const report of [...reports, ...(verifiedReports as Report[])]) byId.set(report.id, report);
  const merged = [...byId.values()].sort((a, b) => b.date.localeCompare(a.date));
  return <ReportExplorer reports={merged} />;
}
