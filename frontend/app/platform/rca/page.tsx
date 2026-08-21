"use client";

import { useState } from "react";
import { BrainCircuit, Download, FileText, GitBranch, LucideIcon, ShieldAlert } from "lucide-react";
import { CitationCard } from "@/components/platform/citation-card";
import { GlassCard, MetricCard } from "@/components/platform/cards";
import { SeverityBadge } from "@/components/platform/badges";
import { citations, rcaTimeline } from "@/lib/demo-data";

export default function RcaPage() {
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState("");

  async function exportPdf() {
    setExporting(true);
    setMessage("");
    try {
      const response = await fetch("/api/reports/rca/TRK-001", { method: "POST" });
      if (!response.ok) throw new Error(`Export failed with ${response.status}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "RCA_TRK-001.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setMessage("RCA PDF exported successfully.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to export RCA PDF.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="grid gap-5">
      <section className="command-panel rounded-3xl p-6">
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-300">RCA Assistant</p>
        <h1 className="mt-2 text-4xl font-black tracking-normal">Evidence-led Root Cause Investigation</h1>
        <p className="mt-2 max-w-3xl text-slate-400">Generate professional RCA reports with timeline, hypotheses, corrective actions, preventive actions, and source citations.</p>
      </section>
      <section className="grid gap-4 md:grid-cols-4"><MetricCard label="Incident Risk" value="High" delta="Repeated rail defect" tone="critical" /><MetricCard label="Evidence" value="3 docs" delta="Cited sources" tone="success" /><MetricCard label="Confidence" value="86%" delta="Source agreement" tone="info" /><MetricCard label="Actions" value="4" delta="Corrective/preventive" tone="warning" /></section>
      <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
        <GlassCard>
          <h2 className="text-xl font-black">Investigation Inputs</h2>
          <div className="mt-5 grid gap-3">
            {["Asset: TRK-001 Track Section", "Incident: repeated rail defect", "Failure description: high vibration and track geometry deviation symptoms", "Evidence: WO-10877, WO-10421, SOP-MECH-014"].map((item) => <input key={item} defaultValue={item} className="rounded-xl border border-white/10 bg-white/[0.07] p-3 text-white" />)}
            <button onClick={exportPdf} disabled={exporting} className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-blue-500 px-5 font-bold transition hover:bg-cyan-500 disabled:cursor-wait disabled:opacity-70">
              <Download size={18} /> {exporting ? "Exporting..." : "Export RCA PDF"}
            </button>
            {message ? <p className="rounded-xl border border-white/10 bg-white/[0.05] p-3 text-sm text-slate-300">{message}</p> : null}
          </div>
          <div className="mt-5 grid gap-3">
            {([
              [BrainCircuit, "Hypothesis", "Track Geometry Deviation and track geometry restriction likely initiated rail defect."],
              [GitBranch, "Contributing Factor", "Possible rail alignment deviation after prior maintenance window."],
              [ShieldAlert, "Risk Control", "Verify track possession safety control and inspection follow-up isolation before casing work."],
              [FileText, "Evidence", "Attach work orders, SOP, and OEM troubleshooting references."]
            ] as Array<[LucideIcon, string, string]>).map(([ItemIcon, title, body]) => <div key={title} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"><ItemIcon className="mb-3 text-cyan-300" /><h3 className="font-bold">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-400">{body}</p></div>)}
          </div>
        </GlassCard>
        <GlassCard>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-bold">Professional RCA Report Preview</h2><SeverityBadge value="High" /></div>
          <p className="leading-7 text-slate-300">Incident summary: TRK-001 Track Section experienced repeated rail defect after vibration alarms and track geometry deviation-like operating conditions. Likely root causes include low track condition pressure, ballast and drainage deterioration, inspection follow-up instability, and possible rail alignment deviation.</p>
          <h3 className="mt-5 font-semibold text-cyan-200">Investigation Timeline</h3>
          {rcaTimeline.map((item) => <div key={item.time} className="mt-3 rounded-2xl border border-white/10 bg-white/[0.04] p-4"><strong className="text-cyan-200">{item.time}</strong><p className="mt-1 text-sm leading-6 text-slate-400">{item.event}</p></div>)}
          <h3 className="mt-5 font-semibold text-cyan-200">Evidence Citations</h3>
          <div className="mt-3 grid gap-3">{citations.map((citation) => <CitationCard key={citation.title} {...citation} />)}</div>
        </GlassCard>
      </div>
    </div>
  );
}
