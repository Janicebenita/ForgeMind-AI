import { AlertTriangle, ClipboardCheck, FileText, LucideIcon, ShieldCheck, Wrench, BarChart2 } from "lucide-react";
import { AssetHealthCard } from "@/components/platform/asset-health-card";
import { RiskBadge, SeverityBadge } from "@/components/platform/badges";
import { ChartCard, GlassCard, MetricCard } from "@/components/platform/cards";
import { GraphCanvas } from "@/components/graph/graph-canvas";
import { assets as fallbackAssets, rcaTimeline as fallbackTimeline } from "@/lib/demo-data";
import { cookies } from "next/headers";
import { backendBaseUrl, TOKEN_COOKIE } from "@/lib/backend-proxy";

async function loadAsset(tag: string) {
  try {
    const token = (await cookies()).get(TOKEN_COOKIE)?.value;
    const response = await fetch(`${backendBaseUrl()}/api/assets/${tag}`, {
      headers: token ? { authorization: `Bearer ${token}` } : {},
      cache: "no-store"
    });
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

async function loadAllAssets() {
  try {
    const token = (await cookies()).get(TOKEN_COOKIE)?.value;
    const response = await fetch(`${backendBaseUrl()}/api/assets`, {
      headers: token ? { authorization: `Bearer ${token}` } : {},
      cache: "no-store"
    });
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

export default async function AssetsPage({
  searchParams,
}: {
  searchParams: Promise<{ tag?: string }>;
}) {
  const params = await searchParams;
  const activeTag = params.tag || "TRK-001";
  
  const assetData = await loadAsset(activeTag);
  const allAssets = await loadAllAssets() || fallbackAssets;

  // Fallback to static demo data if backend fetch failed or returns empty
  const activeAsset = assetData?.asset || fallbackAssets.find((a) => a.tag === activeTag) || fallbackAssets[0];
  const usage = assetData?.usage || [];
  const failures = assetData?.failures || [];
  const workOrders = assetData?.work_orders || [];
  const inspections = assetData?.inspections || [];
  const riskDrivers = assetData?.risk_drivers || [activeAsset.nextAction || "Inspect asset and verify track possession safety control evidence."];

  // Build a timeline dynamically from failures and inspections
  const timeline = failures.map((f: any) => ({
    time: f.occurred_on,
    event: `[Failure Record] Mode: ${f.failure_mode} (${f.severity} severity). Root cause context: ${f.root_cause || "None recorded"}`
  })).concat(inspections.map((i: any) => ({
    time: i.inspected_on,
    event: `[Inspection finding] Severity: ${i.severity}. Finding: ${i.finding}. Next due: ${i.next_due}`
  }))).sort((a: any, b: any) => b.time.localeCompare(a.time));

  const displayTimeline = timeline.length > 0 ? timeline : fallbackTimeline;

  return (
    <div className="grid gap-5">
      <section className="command-panel rounded-3xl p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-300">Industrial Digital Twin Profile</p>
            <h1 className="mt-2 text-4xl font-black tracking-normal">{activeAsset.tag} - {activeAsset.name || activeAsset.description}</h1>
            <p className="mt-2 text-slate-400">{activeAsset.asset_type || activeAsset.type} - {activeAsset.location} - {activeAsset.status}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <RiskBadge value={activeAsset.risk_score || activeAsset.riskScore || 50} />
            <SeverityBadge value={activeAsset.compliance_status || activeAsset.complianceStatus || "Monitored"} />
          </div>
        </div>
      </section>

      {/* Asset Selector */}
      <section className="flex flex-wrap gap-2 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
        {allAssets.map((ast: any) => (
          <a
            key={ast.tag}
            href={`/platform/assets?tag=${ast.tag}`}
            className={`rounded-xl px-4 py-2 text-sm font-bold transition ${
              ast.tag === activeTag
                ? "bg-blue-500 text-white"
                : "bg-white/5 text-slate-300 hover:bg-white/10"
            }`}
          >
            {ast.tag}
          </a>
        ))}
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Risk Score" value={activeAsset.risk_score || activeAsset.riskScore || 50} delta="Realtime hazard rating" tone="critical" />
        <MetricCard label="Location" value={activeAsset.location} delta="Area code / section tag" tone="info" />
        <MetricCard label="Type" value={activeAsset.asset_type || activeAsset.type} delta="Asset classification category" tone="info" />
        <MetricCard label="Status" value={activeAsset.status} delta="Asset operating status" tone="success" />
      </section>

      {usage.length > 0 && (
        <section className="grid gap-4 md:grid-cols-2">
          {usage.map((usg: any) => (
            <GlassCard key={usg.usage_id}>
              <div className="flex items-center gap-3">
                <BarChart2 className="text-cyan-300" size={24} />
                <div>
                  <h3 className="font-bold">{usg.metric} ({usg.period})</h3>
                  <p className="mt-1 text-2xl font-black text-white">{Number(usg.value).toLocaleString()} {usg.unit}</p>
                </div>
              </div>
            </GlassCard>
          ))}
        </section>
      )}

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <GlassCard>
          <h2 className="mb-4 text-lg font-bold">Timeline History</h2>
          <div className="max-h-[400px] overflow-y-auto pr-2 grid gap-3">
            {displayTimeline.map((item: any, idx: number) => (
              <div key={idx} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                <strong className="text-cyan-200">{item.time}</strong>
                <p className="mt-1 text-sm leading-6 text-slate-400">{item.event}</p>
              </div>
            ))}
          </div>
        </GlassCard>
        <ChartCard title="Related Asset Graph" subtitle="Documents, SOPs, failures, and compliance obligations">
          <GraphCanvas />
        </ChartCard>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {([
          [Wrench, "Open Work Orders", workOrders.length > 0 ? `${workOrders.length} work orders linked.` : "No active work orders."],
          [FileText, "Linked Document Evidence", assetData?.documents?.length > 0 ? `${assetData.documents.length} source documents.` : "No direct files linked."],
          [ShieldCheck, "Inspections Count", inspections.length > 0 ? `${inspections.length} recorded inspections.` : "No inspections recorded."],
          [AlertTriangle, "Critical Action", riskDrivers[0] || "No actions required."]
        ] as Array<[LucideIcon, string, string]>).map(([ItemIcon, title, body]) => (
          <GlassCard key={title}>
            <ItemIcon className="mb-4 text-cyan-300" />
            <h3 className="font-bold">{title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-400">{body}</p>
          </GlassCard>
        ))}
      </section>

      <GlassCard>
        <h2 className="mb-3 flex items-center gap-2 font-semibold">
          <ClipboardCheck size={18} /> Active Risk Drivers and Mitigations
        </h2>
        <div className="grid gap-2">
          {riskDrivers.map((driver: string, idx: number) => (
            <div key={idx} className="flex items-center gap-2 rounded-xl bg-white/5 p-3 text-sm text-slate-300">
              <span className="h-2 w-2 rounded-full bg-cyan-400" />
              {driver}
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}

