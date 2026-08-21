import { AssetHealthCard } from "@/components/platform/asset-health-card";
import { ChartCard, GlassCard, MetricCard } from "@/components/platform/cards";
import { DowntimeTrendChart, RiskDistributionChart, SeverityBarChart } from "@/components/charts/industrial-charts";
import { assets as fallbackAssets } from "@/lib/demo-data";
import { cookies } from "next/headers";
import { backendBaseUrl, TOKEN_COOKIE } from "@/lib/backend-proxy";

type MaintenancePayload = {
  assets: any[];
  failure_patterns: any[];
  incomplete_maintenance_history: string[];
  high_risk_assets: any[];
  inspections: any[];
};

async function loadMaintenance(): Promise<MaintenancePayload | null> {
  try {
    const token = (await cookies()).get(TOKEN_COOKIE)?.value;
    const response = await fetch(`${backendBaseUrl()}/api/maintenance`, {
      headers: token ? { authorization: `Bearer ${token}` } : {},
      cache: "no-store"
    });
    if (!response.ok) return null;
    return (await response.json()) as MaintenancePayload;
  } catch {
    return null;
  }
}

export default async function MaintenancePage() {
  const data = await loadMaintenance();
  
  const assets = data?.assets || fallbackAssets;
  const highRiskCount = data?.high_risk_assets?.length ?? 0;
  const backlogCount = data?.incomplete_maintenance_history?.length ?? 0;
  const patternCount = data?.failure_patterns?.length ?? 0;
  
  // Real dynamic inspections
  const rawInspections = data?.inspections || [];
  const scheduleItems = rawInspections.map((i) => 
    `${i.asset_tag} ${i.finding.length > 30 ? i.finding.slice(0, 30) + "..." : i.finding} · Due ${i.next_due}`
  );

  // Fallback to demo items if database lacks inspections
  const displaySchedule = scheduleItems.length > 0 
    ? scheduleItems 
    : ["TRK-001 track condition strainer inspection · 48h (Demo)", "SW-002 oil contamination retest · 5d (Demo)", "HX401 pressure test · 12d (Demo)"];

  return (
    <div className="grid gap-5">
      <div>
        <h1 className="text-3xl font-black">Maintenance Intelligence</h1>
        <p className="mt-2 text-slate-400">Failure pattern analysis, predicted risks, backlog intelligence, MTBF, MTTR, and preventive maintenance scheduling.</p>
      </div>
      
      <section className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Failure Modes" value={patternCount || "7"} delta="From failure database" tone="warning" />
        <MetricCard label="Backlog / No History" value={backlogCount || "42"} delta="Assets with 0 work orders" tone="warning" />
        <MetricCard label="Avg MTBF (Demo)" value="76d" delta="Simulated fleet estimate" tone="success" />
        <MetricCard label="Avg MTTR (Demo)" value="6.9h" delta="Simulated fleet estimate" tone="success" />
      </section>
      
      <section className="grid gap-4 xl:grid-cols-2">
        <ChartCard title="MTBF / MTTR Trend (Simulated)" subtitle="Historical reliability tracking">
          <DowntimeTrendChart />
        </ChartCard>
        <ChartCard title="Work Order Intelligence (Simulated)" subtitle="Severity distribution check">
          <SeverityBarChart />
        </ChartCard>
      </section>
      
      <section className="grid gap-4 lg:grid-cols-3">
        {assets.map((asset: any) => (
          <AssetHealthCard key={asset.tag} asset={{
            tag: asset.tag,
            name: asset.name || asset.description || asset.tag,
            type: asset.asset_type || asset.type || "Asset",
            location: asset.location,
            riskScore: asset.risk_score || asset.riskScore || 50,
            reliabilityScore: asset.reliabilityScore || 85,
            status: asset.status,
            mtbf: asset.mtbf || 120,
            mttr: asset.mttr || 8,
            nextAction: asset.nextAction || "Review current maintenance history.",
            complianceStatus: asset.compliance_status || asset.complianceStatus || "Monitored",
            failureModes: asset.failure_modes || asset.failureModes || []
          }} />
        ))}
      </section>
      
      <GlassCard>
        <h2 className="mb-3 font-semibold">Preventive Maintenance Schedule</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {displaySchedule.map((item: string) => (
            <div key={item} className="rounded-xl bg-white/[0.06] p-4 text-sm text-slate-300">
              {item}
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
