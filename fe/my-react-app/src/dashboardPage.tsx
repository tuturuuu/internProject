import Navbar from "./components/Navbar";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Cell,
} from "recharts";
import {
  Shield, Zap, Target, Lightbulb, BarChart2, AlignLeft,
  CircleDot,
} from "lucide-react";

// ── Data ───────────────────────────────────────────────────────────────────
const STAT_CARDS = [
  {
    label: "BEST TOP-10 QUALITY",
    icon: <Shield size={32} className="text-gray-200" />,
    value: "0.7939",
    sub: "NDCG@10 Score",
    tag: "Sequential Rerank",
    tagColor: "bg-gray-100 text-gray-600",
  },
  {
    label: "FASTEST MODEL",
    icon: <Zap size={32} className="text-gray-200" />,
    value: "3.21",
    unit: "ms",
    sub: "XGB Latency",
    tag: "CatBoost Standalone",
    tagColor: "bg-orange-100 text-orange-700",
  },
  {
    label: "BEST TOP-K BLEND",
    icon: <CircleDot size={32} className="text-gray-200" />,
    value: "0.7423",
    sub: "NDCG@3 Score",
    tag: "Parallel Blend",
    tagColor: "bg-red-500 text-white",
  },
];

const PIPELINES = [
  { algorithm: "combined", name: "Parallel Blend", ndcg3: 0.7423, ndcg5: 0.7363, ndcg10: 0.7786, latency: "-", status: "BEST TOP-K", statusColor: "bg-red-500 text-white" },
  { algorithm: "gbt -> llm", name: "Sequential Rerank", ndcg3: 0.7163, ndcg5: 0.7323, ndcg10: 0.7939, latency: "2,152.25ms", status: "BEST NDCG@10", statusColor: "bg-green-100 text-green-700" },
  { algorithm: "xgboost", name: "Standalone", ndcg3: 0.7371, ndcg5: 0.7199, ndcg10: 0.7813, latency: "25.03ms", status: "BASELINE", statusColor: "bg-gray-100 text-gray-600" },
  { algorithm: "lightgbm", name: "Standalone", ndcg3: 0.6433, ndcg5: 0.676, ndcg10: 0.739, latency: "15.42ms", status: "TREE MODEL", statusColor: "bg-gray-100 text-gray-600" },
  { algorithm: "llm", name: "Standalone", ndcg3: 0.6494, ndcg5: 0.6426, ndcg10: 0.7133, latency: "4,509.62ms", status: "SLOWEST", statusColor: "bg-red-100 text-red-600" },
  { algorithm: "catboost", name: "Standalone", ndcg3: 0.555, ndcg5: 0.5748, ndcg10: 0.6677, latency: "3.21ms", status: "FASTEST", statusColor: "bg-orange-100 text-orange-700" },
];

const LATENCY_DATA = [
  { name: "LLM Standalone", api: 4493.84, local: 15.78, total: 4509.62 },
  { name: "Sequential GBT -> LLM", api: 2133.95, local: 18.3, total: 2152.25 },
  { name: "XGBoost Standalone", api: 0, local: 25.03, total: 25.03 },
  { name: "LightGBM Standalone", api: 0, local: 15.42, total: 15.42 },
  { name: "CatBoost Standalone", api: 0, local: 3.21, total: 3.21 },
];

const TOPK_CHART = [
  { name: "Combined", ndcg3: 0.7423, ndcg5: 0.7363, ndcg10: 0.7786 },
  { name: "Sequential", ndcg3: 0.7163, ndcg5: 0.7323, ndcg10: 0.7939 },
  { name: "XGBoost", ndcg3: 0.7371, ndcg5: 0.7199, ndcg10: 0.7813 },
  { name: "LightGBM", ndcg3: 0.6433, ndcg5: 0.676, ndcg10: 0.739 },
  { name: "LLM", ndcg3: 0.6494, ndcg5: 0.6426, ndcg10: 0.7133 },
  { name: "CatBoost", ndcg3: 0.555, ndcg5: 0.5748, ndcg10: 0.6677 },
];

const OBSERVATIONS = [
  {
    icon: <AlignLeft size={14} className="text-gray-400 mt-0.5 shrink-0" />,
    title: "Baseline Analysis",
    body: "XGBoost is the strongest standalone tree baseline with 0.7371 NDCG@3 and 0.7813 NDCG@10.",
  },
  {
    icon: <BarChart2 size={14} className="text-gray-400 mt-0.5 shrink-0" />,
    title: "Speed vs. Quality",
    body: "CatBoost is the fastest at 3.21ms, but it also has the weakest standalone tree quality at 0.6677 NDCG@10.",
  },
  {
    icon: <AlignLeft size={14} className="text-gray-400 mt-0.5 shrink-0" />,
    title: "Impact of Reranking",
    body: "Sequential reranking has the best NDCG@10, while the parallel blend performs best at NDCG@3 and NDCG@5.",
  },
];

// ── Custom latency bar label ───────────────────────────────────────────────
function LatencyRow({ row }: { row: typeof LATENCY_DATA[0] }) {
  const maxMs = 4510;
  const apiW  = (row.api   / maxMs) * 100;
  const locW  = (row.local / maxMs) * 100;

  return (
    <div className="mb-5">
      <div className="flex justify-between text-sm mb-1.5">
        <span className="font-medium text-gray-700">{row.name}</span>
        <span className="font-bold text-gray-800">{row.total.toLocaleString()}ms</span>
      </div>
      <div className="flex h-5 rounded-full overflow-hidden bg-gray-100">
        {row.api > 0 && (
          <div className="bg-red-400 h-full transition-all" style={{ width: `${apiW}%` }} />
        )}
        <div className="bg-emerald-700 h-full transition-all" style={{ width: `${locW}%` }} />
      </div>
    </div>
  );
}

// ── Main ───────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const filter = "ALL PIPELINES";

  return (
    <div className="min-h-screen bg-[#f7f6f4] font-sans text-gray-900">

      {/* Nav */}
      <Navbar />

      <div className="max-w-6xl mx-auto px-8 py-8 space-y-7">

        {/* Page title */}
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight mb-1">Search Performance Overview</h1>
          <p className="text-gray-500 text-sm">Benchmarking NDCG@3, NDCG@5, NDCG@10, and latency across the ranking pipelines.</p>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-3 gap-5">
          {STAT_CARDS.map((c) => (
            <div key={c.label} className="bg-white rounded-2xl p-5 shadow-sm flex items-start justify-between">
              <div>
                <p className="text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-2">{c.label}</p>
                <p className="text-4xl font-extrabold tracking-tight leading-none mb-0.5">
                  {c.value}
                  {c.unit && <span className="text-xl font-bold text-gray-400 ml-1">{c.unit}</span>}
                </p>
                <p className="text-xs text-gray-400 mb-3">{c.sub}</p>
                <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full ${c.tagColor}`}>{c.tag}</span>
              </div>
              <div className="opacity-20 mt-1">{c.icon}</div>
            </div>
          ))}
        </div>

        {/* Middle row: Leaderboard + Observations */}
        <div className="grid grid-cols-3 gap-5">

          {/* Algorithm Leaderboard (2/3) */}
          <div className="col-span-2 bg-white rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-bold">Algorithm Leaderboard</h2>
              <span className="text-[10px] font-bold tracking-widest text-gray-500 border border-gray-200 rounded px-2 py-1">{filter}</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    {["ALGORITHM", "PIPELINE", "NDCG@3", "NDCG@5", "NDCG@10", "LATENCY", "STATUS"].map((h) => (
                      <th key={h} className="text-[10px] font-bold tracking-widest text-gray-400 text-left pb-2 pr-4">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {PIPELINES.map((p, i) => (
                    <tr key={`${p.algorithm}-${p.name}`} className={`border-b border-gray-50 ${i === PIPELINES.length - 1 ? "border-0" : ""}`}>
                      <td className="py-3 pr-4 font-semibold text-sm text-gray-800 capitalize">{p.algorithm}</td>
                      <td className="py-3 pr-4 text-sm text-gray-600">{p.name}</td>
                      <td className="py-3 pr-4 text-sm text-gray-600">{p.ndcg3.toFixed(4)}</td>
                      <td className="py-3 pr-4 text-sm text-gray-600">{p.ndcg5.toFixed(4)}</td>
                      <td className="py-3 pr-4 text-sm font-bold text-gray-800">{p.ndcg10.toFixed(4)}</td>
                      <td className={`py-3 pr-4 text-sm ${p.latency.includes(",") ? "text-red-500 font-semibold" : "text-gray-600"}`}>{p.latency}</td>
                      <td className="py-3">
                        <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${p.statusColor}`}>{p.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Latency Breakdown */}
            <div className="mt-6 pt-5 border-t border-gray-100">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold mb-0.5">Latency Breakdown</h3>
                  <p className="text-xs text-gray-400">Reported OpenAI time vs local model compute</p>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-red-400 inline-block" />API Call</span>
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-700 inline-block" />Local Compute</span>
                </div>
              </div>
              {LATENCY_DATA.map((row) => <LatencyRow key={row.name} row={row} />)}
            </div>
          </div>

          {/* Observations (1/3) */}
          <div className="bg-white rounded-2xl p-5 shadow-sm flex flex-col">
            <div className="flex items-center gap-2 mb-5">
              <Lightbulb size={16} className="text-gray-500" />
              <h2 className="text-base font-bold">Observations</h2>
            </div>

            <div className="space-y-5 flex-1">
              {OBSERVATIONS.map((o) => (
                <div key={o.title} className="flex gap-2.5">
                  {o.icon}
                  <div>
                    <p className="text-xs font-bold text-gray-700 mb-0.5">{o.title}</p>
                    <p className="text-xs text-gray-500 leading-relaxed">{o.body}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Strategy Rec */}
            <div className="mt-5 pt-4 border-t border-gray-100">
              <div className="flex items-center gap-1.5 mb-2">
                <Target size={12} className="text-red-500" />
                <p className="text-[10px] font-bold tracking-widest text-red-500 uppercase">Strategy Rec</p>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed italic">
                Use "Combined" when top-ranked results matter most, "Sequential Rerank" for deeper top-10 ranking quality, and "XGBoost" when speed and stability matter.
              </p>
            </div>
          </div>
        </div>

        {/* Top-K Accuracy chart */}
        <div className="bg-white rounded-2xl p-7 shadow-sm">
          <h2 className="text-base font-bold text-center mb-8">Top-K Accuracy Comparison</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={TOPK_CHART} barCategoryGap="35%" barGap={4}>
              <XAxis
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fill: "#9ca3af" }}
              />
              <YAxis
                domain={[0.5, 0.82]}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 11, fill: "#9ca3af" }}
                tickFormatter={(v) => v.toFixed(2)}
              />
              <Tooltip
                formatter={(value: unknown) => typeof value === "number" ? value.toFixed(4) : String(value)}
                contentStyle={{ borderRadius: "12px", border: "1px solid #f3f4f6", fontSize: 12 }}
              />
              <Legend
                iconType="circle"
                iconSize={10}
                wrapperStyle={{ fontSize: 12, paddingTop: 24 }}
              />
              <Bar dataKey="ndcg3" name="NDCG@3" radius={[6, 6, 0, 0]}>
                {TOPK_CHART.map((_, i) => (
                  <Cell key={i} fill={["#d4a99a", "#c4a882", "#9db8ad", "#b0a89e", "#b7a6c9", "#d1a1a1"][i]} />
                ))}
              </Bar>
              <Bar dataKey="ndcg5" name="NDCG@5" radius={[6, 6, 0, 0]}>
                {TOPK_CHART.map((_, i) => (
                  <Cell key={i} fill={["#c57d56", "#9f7f4e", "#4f8f7a", "#78716c", "#7c6fa0", "#b85f5f"][i]} />
                ))}
              </Bar>
              <Bar dataKey="ndcg10" name="NDCG@10" radius={[6, 6, 0, 0]}>
                {TOPK_CHART.map((_, i) => (
                  <Cell key={i} fill={["#b45309", "#92400e", "#065f46", "#44403c", "#5b4b8a", "#991b1b"][i]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
