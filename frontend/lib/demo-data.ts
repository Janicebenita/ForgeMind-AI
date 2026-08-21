import type { LucideIcon } from "lucide-react";
import { Activity, AlertTriangle, BadgeCheck, BarChart3, BookOpen, ClipboardCheck, Factory, FileSearch, Gauge, ShieldCheck, Wrench, Zap } from "lucide-react";

export type RiskLevel = "Low" | "Medium" | "High" | "Critical";
export type ValidationStatus = "Approved" | "Needs Review" | "Rejected";

export type IndustrialAsset = {
  tag: string;
  name: string;
  type: string;
  location: string;
  status: string;
  riskScore: number;
  reliabilityScore: number;
  complianceStatus: "Ready" | "Partial" | "At Risk";
  mtbf: number;
  mttr: number;
  failureModes: string[];
  nextAction: string;
};

export const assets: IndustrialAsset[] = [
  {
    tag: "TRK-001",
    name: "Mainline Track Section A",
    type: "Track Section",
    location: "Corridor A KM 45.2-46.8",
    status: "Operational with advisory",
    riskScore: 78,
    reliabilityScore: 81,
    complianceStatus: "Partial",
    mtbf: 92,
    mttr: 4.2,
    failureModes: [
      "rail surface defect",
      "track geometry deviation",
      "gauge variation"
    ],
    nextAction: "Review ultrasonic rail testing and geometry inspection history"
  },
  {
    tag: "TRK-002",
    name: "Mainline Track Section B",
    type: "Track Section",
    location: "Corridor A KM 46.8-48.4",
    status: "Operational",
    riskScore: 52,
    reliabilityScore: 89,
    complianceStatus: "Ready",
    mtbf: 118,
    mttr: 3.1,
    failureModes: [
      "minor geometry deviation",
      "ballast deterioration"
    ],
    nextAction: "Continue scheduled geometry monitoring"
  },
  {
    tag: "SW-002",
    name: "Turnout Assembly 12A",
    type: "Turnout",
    location: "Station Approach",
    status: "Monitored",
    riskScore: 71,
    reliabilityScore: 74,
    complianceStatus: "Partial",
    mtbf: 76,
    mttr: 5.4,
    failureModes: [
      "switch rail misalignment",
      "point movement anomaly",
      "wear at crossing"
    ],
    nextAction: "Inspect switch rail alignment and point-machine condition"
  },
  {
    tag: "SIG-004",
    name: "Signal Relay Group S14",
    type: "Signalling",
    location: "Signal Cabin 3",
    status: "Monitored",
    riskScore: 64,
    reliabilityScore: 85,
    complianceStatus: "Ready",
    mtbf: 104,
    mttr: 2.8,
    failureModes: [
      "relay response delay",
      "intermittent signal fault"
    ],
    nextAction: "Review relay diagnostics and recent signal fault history"
  },
  {
    tag: "PM-003",
    name: "Point Machine Assembly",
    type: "Signalling Asset",
    location: "Turnout 12A",
    status: "Inspection due",
    riskScore: 73,
    reliabilityScore: 72,
    complianceStatus: "Partial",
    mtbf: 69,
    mttr: 4.8,
    failureModes: [
      "motor current anomaly",
      "point detection mismatch"
    ],
    nextAction: "Perform point-machine functional and detection test"
  },
  {
    tag: "BRG-004",
    name: "Bridge Structural Zone 4",
    type: "Bridge Asset",
    location: "Corridor A",
    status: "Inspection due",
    riskScore: 76,
    reliabilityScore: 68,
    complianceStatus: "At Risk",
    mtbf: 84,
    mttr: 7.6,
    failureModes: [
      "surface corrosion",
      "structural deterioration",
      "drainage deficiency"
    ],
    nextAction: "Schedule structural inspection and condition assessment"
  },
  {
    tag: "WHL-007",
    name: "Wheel Impact Monitoring Point",
    type: "Wayside Monitoring",
    location: "KM 42.6",
    status: "Operational",
    riskScore: 58,
    reliabilityScore: 87,
    complianceStatus: "Ready",
    mtbf: 126,
    mttr: 2.4,
    failureModes: [
      "high wheel-impact alert",
      "sensor drift"
    ],
    nextAction: "Correlate wheel-impact alarms with passing train records"
  },
  {
    tag: "TRM-006",
    name: "Track Recording and Monitoring Unit",
    type: "Monitoring",
    location: "Corridor A",
    status: "Operational",
    riskScore: 46,
    reliabilityScore: 91,
    complianceStatus: "Ready",
    mtbf: 138,
    mttr: 2.1,
    failureModes: [
      "measurement drift",
      "data acquisition interruption"
    ],
    nextAction: "Verify calibration and scheduled recording cycle"
  },
  {
    tag: "OCS-008",
    name: "Overhead Catenary Section",
    type: "Electrification",
    location: "Corridor A KM 40-48",
    status: "Monitored",
    riskScore: 61,
    reliabilityScore: 83,
    complianceStatus: "Ready",
    mtbf: 112,
    mttr: 4.0,
    failureModes: [
      "contact wire wear",
      "registration deviation"
    ],
    nextAction: "Review contact-wire wear and geometry measurements"
  },
  {
    tag: "EP-401",
    name: "Traction Electrical Panel",
    type: "Electrical Asset",
    location: "Traction Substation E-4",
    status: "Evidence review required",
    riskScore: 67,
    reliabilityScore: 79,
    complianceStatus: "Partial",
    mtbf: 98,
    mttr: 3.7,
    failureModes: [
      "protection relay alert",
      "inspection evidence gap"
    ],
    nextAction: "Review electrical inspection and protection test evidence"
  }
];

export const executiveMetrics = [
  { label: "Total Documents", value: "1,284", delta: "+18 this week", tone: "info" },
  { label: "Assets Indexed", value: "426", delta: "94% coverage", tone: "success" },
  { label: "Compliance Score", value: "82%", delta: "3 critical gaps", tone: "warning" },
  { label: "Critical Risks", value: "11", delta: "4 need action", tone: "critical" },
  { label: "Maintenance Alerts", value: "37", delta: "12 high severity", tone: "warning" },
  { label: "AI Queries", value: "2,918", delta: "97% cited", tone: "info" },
  { label: "Knowledge Coverage", value: "89%", delta: "+6% month over month", tone: "success" },
  { label: "Time Saved", value: "418h", delta: "$42k recovered", tone: "success" }
];

export const riskDistribution = assets.map((asset) => ({ name: asset.tag, risk: asset.riskScore, reliability: asset.reliabilityScore }));
export const downtimeTrend = [
  { month: "Jan", risk: 68, downtime: 42 },
  { month: "Feb", risk: 71, downtime: 38 },
  { month: "Mar", risk: 77, downtime: 51 },
  { month: "Apr", risk: 73, downtime: 33 },
  { month: "May", risk: 81, downtime: 48 },
  { month: "Jun", risk: 69, downtime: 28 }
];
export const alertSeverity = [
  { severity: "Critical", count: 11 },
  { severity: "High", count: 26 },
  { severity: "Medium", count: 54 },
  { severity: "Low", count: 91 }
];
export const queryBreakdown = [
  { name: "Maintenance RCA", value: 42 },
  { name: "Compliance", value: 23 },
  { name: "SOP Lookup", value: 18 },
  { name: "Inspection", value: 17 }
];
export const coverageHeatmap = [
  ["Track Sections", 92, 86, 88, 94],
  ["Turnouts", 84, 79, 82, 88],
  ["Signalling", 89, 83, 91, 87],
  ["Structures", 76, 82, 84, 80],
  ["Electrification", 81, 78, 86, 83]
];

export const entities = [
  ["TRK-001", "Rail Asset", 97, "rail_asset_register.csv", "Row 1", "TRK-001", "Approved"],
  ["rail surface defect", "Inspection Finding", 94, "rail_inspections.csv", "INSP-001", "TRK-001", "Approved"],
  ["track geometry deviation", "Condition Indicator", 93, "track_geometry_TRK-001.csv", "Section 4", "TRK-001", "Approved"],
  ["gross tonnage", "Operational Metric", 96, "rail_usage.csv", "2025-Q4", "TRK-001", "Approved"],
  ["SW-002", "Turnout Asset", 96, "rail_asset_register.csv", "Row 3", "SW-002", "Approved"],
  ["switch rail misalignment", "Inspection Finding", 91, "turnout_inspection_SW-002.pdf", "Finding 2", "SW-002", "Needs Review"],
  ["PM-003", "Point Machine", 95, "signalling_asset_register.csv", "Row 6", "PM-003", "Approved"],
  ["point detection mismatch", "Failure Mode", 90, "point_machine_history_PM-003.csv", "Event 14", "PM-003", "Needs Review"],
  ["SIG-004", "Signalling Asset", 95, "signalling_asset_register.csv", "Row 4", "SIG-004", "Approved"],
  ["BRG-004", "Bridge Asset", 96, "bridge_asset_register.csv", "Row 4", "BRG-004", "Approved"],
  ["surface corrosion", "Inspection Finding", 89, "BRG-004_structural_inspection_report.pdf", "Section 6", "BRG-004", "Needs Review"],
  ["track possession", "Safety Control", 94, "rail_worksite_safety_procedure.pdf", "Section 3", "TRK-001", "Approved"],
  ["ultrasonic rail testing", "Inspection Method", 96, "rail_inspection_standard.pdf", "Section 5", "TRK-001", "Approved"]
] as const;

export const documents = [
  {
    name: "rail_asset_register.csv",
    type: "Rail Asset Register",
    progress: 100,
    status: "Knowledge graph updated",
    confidence: 98
  },
  {
    name: "rail_inspections.csv",
    type: "Inspection Records",
    progress: 100,
    status: "Inspection evidence indexed",
    confidence: 97
  },
  {
    name: "rail_usage.csv",
    type: "Operational Usage Records",
    progress: 100,
    status: "Usage history indexed",
    confidence: 96
  },
  {
    name: "track_geometry_TRK-001.csv",
    type: "Track Geometry Record",
    progress: 100,
    status: "Geometry evidence indexed",
    confidence: 95
  },
  {
    name: "turnout_inspection_SW-002.pdf",
    type: "Turnout Inspection Report",
    progress: 100,
    status: "Inspection findings indexed",
    confidence: 95
  },
  {
    name: "point_machine_history_PM-003.csv",
    type: "Signalling Maintenance History",
    progress: 100,
    status: "Maintenance events indexed",
    confidence: 94
  },
  {
    name: "BRG-004_structural_inspection_report.pdf",
    type: "Bridge Structural Inspection",
    progress: 100,
    status: "Structural findings indexed",
    confidence: 94
  },
  {
    name: "rail_worksite_safety_procedure.pdf",
    type: "Rail Safety Procedure",
    progress: 100,
    status: "Safety controls indexed",
    confidence: 97
  },
  {
    name: "rail_inspection_standard.pdf",
    type: "Rail Inspection Standard",
    progress: 100,
    status: "Inspection requirements indexed",
    confidence: 96
  }
];

export const pipeline = ["Uploaded", "OCR", "Text Extraction", "Chunking", "Entity Extraction", "Embeddings", "Vector Storage", "Knowledge Graph"];

export const citations = [
  {
    title: "rail_inspections.csv",
    page: "INSP-001",
    confidence: 95,
    quote: "TRK-001 inspection identified a recurring rail surface defect near KM 45.6 with follow-up inspection required."
  },
  {
    title: "track_geometry_TRK-001.csv",
    page: "Section 4",
    confidence: 93,
    quote: "Track geometry monitoring identified progressive alignment and gauge variation within the TRK-001 section."
  },
  {
    title: "rail_usage.csv",
    page: "2025-Q4",
    confidence: 96,
    quote: "TRK-001 recorded increased cumulative gross tonnage during the review period."
  }
];

export const rcaTimeline = [
  {
    time: "2025-08-14",
    event: "Track geometry inspection identified minor alignment deviation on TRK-001."
  },
  {
    time: "2025-11-10",
    event: "Visual inspection recorded a recurring rail surface defect near KM 45.6."
  },
  {
    time: "2026-02-19",
    event: "Geometry trend review confirmed progressive deviation under increasing cumulative tonnage."
  },
  {
    time: "2026-06-18",
    event: "Preventive action assigned: ultrasonic rail testing, geometry verification, and targeted maintenance review."
  }
];

export const complianceRows = [
  {
    standard: "Railway Safety and Worksite Compliance",
    score: 88,
    gap: "Track-possession documentation incomplete for one maintenance activity",
    risk: "Medium"
  },
  {
    standard: "Track Inspection Compliance",
    score: 84,
    gap: "Follow-up geometry inspection evidence pending for TRK-001",
    risk: "High"
  },
  {
    standard: "Signalling Maintenance Compliance",
    score: 89,
    gap: "Point-machine verification record pending for PM-003",
    risk: "Medium"
  },
  {
    standard: "Rail Structural Inspection",
    score: 81,
    gap: "Detailed bridge condition assessment pending for BRG-004",
    risk: "High"
  },
  {
    standard: "Rail Environmental Compliance",
    score: 91,
    gap: "Track drainage trend review pending",
    risk: "Medium"
  },
  {
    standard: "Internal Railway Procedures",
    score: 94,
    gap: "Two inspection procedure acknowledgements pending",
    risk: "Low"
  }
];

export const lessons = [
  {
    title: "Repeated rail defects correlate with high cumulative gross tonnage",
    detail: "TRK-001 inspection history shows recurring rail defects together with increasing cumulative tonnage and progressive geometry deterioration. Prioritize ultrasonic rail testing and geometry verification before recurrence develops into a service-affecting defect.",
    severity: "High"
  },
  {
    title: "Turnout failures recur where inspection anomalies remain unresolved",
    detail: "SW-002 inspection history shows repeated turnout condition alerts where switch-rail alignment and point-machine observations remain unresolved. Escalate repeat findings for preventive intervention.",
    severity: "High"
  },
  {
    title: "Signalling anomalies require evidence correlation across maintenance events",
    detail: "SIG-004 and PM-003 records show that intermittent relay and point-detection anomalies should be correlated with maintenance history and functional-test evidence.",
    severity: "Critical"
  },
  {
    title: "Near-miss trends correlate with delayed track-possession documentation",
    detail: "Worksite safety records show that delayed possession and authorization evidence can increase operational risk. Verify possession, protection and authorization records before maintenance work begins.",
    severity: "Medium"
  }
];

export const reports = [
  {
    title: "TRK-001 Track Condition RCA",
    type: "RCA Report",
    status: "Ready",
    owner: "Rail Reliability",
    updated: "2026-08-21"
  },
  {
    title: "Rail Inspection Compliance Evidence Package",
    type: "Audit Package",
    status: "Needs Review",
    owner: "Rail Compliance",
    updated: "2026-08-21"
  },
  {
    title: "Rail Network Risk Summary",
    type: "Executive Summary",
    status: "Ready",
    owner: "Operations Manager",
    updated: "2026-08-21"
  },
  {
    title: "Preventive Track Maintenance Backlog",
    type: "Maintenance Report",
    status: "Ready",
    owner: "Maintenance Engineering",
    updated: "2026-08-21"
  }
];

export const demoQuestions = [
  {
    category: "Track RCA",
    question: "Why are defects recurring on TRK-001?"
  },
  {
    category: "Maintenance History",
    question: "Show the complete inspection and maintenance history of TRK-001."
  },
  {
    category: "Track Condition",
    question: "What is the latest geometry condition of TRK-001?"
  },
  {
    category: "Turnout",
    question: "What recurring issues have been identified on turnout SW-002?"
  },
  {
    category: "Signalling",
    question: "What maintenance evidence exists for point machine PM-003?"
  },
  {
    category: "Bridge Inspection",
    question: "What structural findings are recorded for BRG-004?"
  },
  {
    category: "Compliance",
    question: "Which railway assets have overdue inspections?"
  },
  {
    category: "Safety",
    question: "Which track-possession or worksite safety records require attention?"
  },
  {
    category: "Operational Usage",
    question: "What was the gross tonnage recorded for TRK-001 in 2025-Q4?"
  },
  {
    category: "Inspection",
    question: "What inspection evidence supports the current risk rating for TRK-001?"
  },
  {
    category: "RCA",
    question: "Generate an evidence-backed RCA for recurring TRK-001 rail defects."
  },
  {
    category: "Evidence Guardrail",
    question: "Can a maintenance action be approved without matching railway inspection or safety evidence?"
  }
];

export const navItems: Array<{ label: string; href: string; icon: LucideIcon }> = [
  { label: "Command Dashboard", href: "/platform/dashboard", icon: Gauge },
  { label: "AI Copilot", href: "/platform/copilot", icon: Activity },
  { label: "Documents", href: "/platform/documents", icon: FileSearch },
  { label: "Knowledge Graph", href: "/platform/graph", icon: Factory },
  { label: "Entity Intelligence", href: "/platform/entities", icon: BookOpen },
  { label: "Asset 360", href: "/platform/assets", icon: Zap },
  { label: "Maintenance", href: "/platform/maintenance", icon: Wrench },
  { label: "RCA Assistant", href: "/platform/rca", icon: ClipboardCheck },
  { label: "Compliance", href: "/platform/compliance", icon: ShieldCheck },
  { label: "Lessons Learned", href: "/platform/lessons", icon: AlertTriangle },
  { label: "Reports", href: "/platform/reports", icon: BadgeCheck },
  { label: "Evaluation Metrics", href: "/platform/evaluation", icon: BarChart3 },
  { label: "Admin Console", href: "/platform/admin", icon: Gauge }
];
