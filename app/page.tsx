import { ReportExplorer } from "./report-explorer";
import { reports } from "./reports";
import discoveredReports from "../data/discovered.json";
import type { Report } from "./reports";

export default function Home() {
  const merged = [...reports, ...(discoveredReports as Report[])]
    .filter((report, index, all) => all.findIndex((item) => item.id === report.id) === index)
    .sort((a, b) => b.date.localeCompare(a.date));
  return <ReportExplorer reports={merged} />;
}
