import { ReportExplorer } from "./report-explorer";
import { reports } from "./reports";
import verifiedReports from "../data/verified.json";
import dossiers from "../data/dossiers.json";
import type { Report } from "./reports";

export default function Home() {
  const byId = new Map<string, Report>();
  const dossierById = new Map(
    (dossiers as Array<Partial<Report> & Pick<Report, "id">>).map((dossier) => [dossier.id, dossier]),
  );
  // Static records and automatically verified releases share one presentation
  // path. Source-grounded dossiers override only descriptive fields and keep
  // the original report/project links intact.
  for (const report of [...reports, ...(verifiedReports as Report[])]) {
    const dossier = dossierById.get(report.id);
    byId.set(report.id, { ...report, ...dossier, links: report.links });
  }
  const merged = [...byId.values()].sort((a, b) => b.date.localeCompare(a.date));
  return <ReportExplorer reports={merged} />;
}
