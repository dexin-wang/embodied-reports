import { ReportExplorer } from "./report-explorer";
import { reports } from "./reports";
import verifiedReports from "../data/verified.json";
import dossiers from "../data/dossiers.json";
import type { Report } from "./reports";

const organizationAliases: Record<string, string> = {
  "自变量机器人": "自变量机器人 / X² Robotics",
  "北京人形机器人创新中心": "北京人形机器人创新中心 / Beijing Humanoid Robot Innovation Center",
  "深度求索": "深度求索 / DeepSeek",
  "通义千问": "通义千问 / Qwen",
};

function canonicalOrganization(organization: string) {
  return Object.entries(organizationAliases).find(([name]) => organization.includes(name))?.[1] ?? organization;
}

function projectKey(title: string) {
  const words = title.toLowerCase().match(/[a-z]+|\d+/g)?.join(" ") ?? title.toLowerCase();
  const canonical = words === "embodied tien kung 3 0" ? "embodied tiangong 3 0" : words;
  return canonical.replace(/[^a-z0-9]/g, "");
}

function detailScore(report: Report) {
  return (report.details?.keyPoints.length ?? 0) + (report.details?.metrics.length ?? 0) + report.links.length;
}

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
    const merged = { ...report, ...dossier, organization: canonicalOrganization(report.organization), links: report.links };
    const key = projectKey(merged.title);
    const current = byId.get(key);
    if (!current || detailScore(merged) > detailScore(current)) byId.set(key, merged);
  }
  const merged = [...byId.values()].sort((a, b) => b.date.localeCompare(a.date));
  return <ReportExplorer reports={merged} />;
}
