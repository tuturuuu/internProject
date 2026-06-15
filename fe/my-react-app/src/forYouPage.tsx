import { useState, useEffect } from "react";
import { RefreshCw, MapPin, Star, Bookmark, Sparkles, Flame, ChevronRight, Zap, Settings2 } from "lucide-react";
import Navbar from "./components/Navbar";

type Model = "XGBoost" | "LightGBM" | "CatBoost" | "LLM" | "Parallel" | "Rerank";

const MODELS: Model[] = ["XGBoost", "LightGBM", "CatBoost", "LLM", "Parallel", "Rerank"];

const TOP_MATCH = {
  name: "L'Artisan Modern Bistro",
  match: 98,
  location: "Upper East Side",
  cuisine: "Contemporary French",
  tags: ["High Value", "Consistent Quality"],
  image: "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1200&h=600&fit=crop",
};

const [recommended, setRecommended] = useState<any[]>([]);
const [trending, setTrending] = useState<any[]>([]);

useEffect(() => {
  async function load() {
    try {
      const res = await fetch("http://localhost:8000/api/frontend/home");
      if (!res.ok) throw new Error("Failed to fetch");
      const data = await res.json();
      setTrending(data.trending || []);
      setRecommended(data.recommended || []);
    } catch (e) {
      console.error(e);
    }
  }
  load();
}, []);

const NEW_FLAVORS = [
  {
    id: "n1",
    name: "Neon Thai Kitchen",
    match: 89,
    alignLabel: "Flavor Alignment",
    desc: "Exploring bold spices and communal dining patterns you'd love.",
    tags: ["Spicy", "Social"],
    image: "https://images.unsplash.com/photo-1559314809-0d155014e29e?w=600&h=400&fit=crop",
  },
  {
    id: "n2",
    name: "Origami",
    match: 85,
    alignLabel: "Minimalist Match",
    desc: "Masterful omakase with a minimal, meditative footprint.",
    tags: ["Minimal", "Omakase"],
    image: "https://images.unsplash.com/photo-1553621042-f6e147245754?w=600&h=400&fit=crop",
  },
  {
    id: "n3",
    name: "The Verdant Room",
    match: 81,
    alignLabel: "Texture Match",
    desc: "Plant-forward small plates with a rotating seasonal tasting menu.",
    tags: ["Vegan", "Seasonal"],
    image: "https://images.unsplash.com/photo-1540914124281-342587941389?w=600&h=400&fit=crop",
  },
  {
    id: "n4",
    name: "Ember & Rye",
    match: 78,
    alignLabel: "Atmosphere Match",
    desc: "Fire-kissed proteins and a whisky list that rewards patience.",
    tags: ["Smoky", "Intimate"],
    image: "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&h=400&fit=crop",
  },
];

function MatchBadge({ pct, size = "sm" }: { pct: number; size?: "sm" | "lg" }) {
  const big = size === "lg";
  return (
    <span className={`inline-flex items-center gap-1 font-bold rounded-full bg-red-500 text-white ${big ? "text-base px-4 py-2" : "text-xs px-2.5 py-1"}`}>
      <Star size={big ? 14 : 11} className="fill-white text-white" />
      {pct}% Match
    </span>
  );
}

export default function ForYouDesktop() {
  const [activeModel, setActiveModel] = useState<Model>("XGBoost");
  const [k, setK] = useState(10);
  const [refreshing, setRefreshing] = useState(false);
  const [savedFlavors, setSavedFlavors] = useState<Set<string>>(new Set());

  const handleRefresh = () => {
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 1200);
  };

  const toggleSave = (id: string) =>
    setSavedFlavors((prev) => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });

  return (
    <div className="min-h-screen bg-[#f7f6f4] font-sans text-gray-900">
      <Navbar />

      <div className="max-w-7xl mx-auto px-8 py-8 flex gap-7">

        {/* ── LEFT SIDEBAR — Settings ── */}
        <aside className="w-72 shrink-0 space-y-4 sticky top-20 self-start">
          <div className="bg-white rounded-2xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Settings2 size={15} className="text-red-500" />
              <h2 className="text-sm font-bold text-gray-800">Recommendation Settings</h2>
            </div>

            <p className="text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-2">Model</p>
            <div className="grid grid-cols-2 gap-1.5 mb-5">
              {MODELS.map((m) => (
                <button
                  key={m}
                  onClick={() => setActiveModel(m)}
                  className={`py-2 rounded-lg text-xs font-semibold transition-all ${activeModel === m ? "bg-red-500 text-white shadow-sm" : "bg-gray-100 text-gray-500 hover:bg-gray-200"}`}
                >
                  {m}
                </button>
              ))}
            </div>

            <div className="flex items-center justify-between mb-1.5">
              <p className="text-[10px] font-bold tracking-widest text-gray-400 uppercase">Results (k)</p>
              <span className="text-sm font-extrabold text-gray-800">{k}</span>
            </div>
            <input
              type="range" min={1} max={50} value={k}
              onChange={(e) => setK(Number(e.target.value))}
              className="w-full accent-red-500 h-1.5 rounded-full cursor-pointer mb-1"
            />
            <div className="flex justify-between text-[10px] text-gray-400 mb-5">
              <span>1</span><span>25</span><span>50</span>
            </div>

            <button
              onClick={handleRefresh}
              className="w-full bg-red-500 hover:bg-red-600 text-white text-sm font-bold py-3 rounded-xl flex items-center justify-center gap-2 transition-colors"
            >
              <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>

          {/* Refine Palate CTA */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-2 mb-2">
              <Flame size={15} className="text-red-500" />
              <h3 className="text-sm font-extrabold text-red-500">Refine Your Palate</h3>
            </div>
            <p className="text-gray-500 text-xs leading-relaxed mb-4">
              Benchmarks help us fine-tune your recommendations. Review your last meal to increase match accuracy.
            </p>
            <button className="w-full bg-red-500 hover:bg-red-600 text-white text-sm font-bold py-2.5 rounded-xl transition-colors">
              Bench Now
            </button>
          </div>
        </aside>

        {/* ── MAIN CONTENT ── */}
        <main className="flex-1 min-w-0 space-y-8">

          {/* Top Match */}
          <section>
            <div className="flex items-end justify-between mb-4">
              <div>
                <p className="text-[10px] font-bold tracking-widest text-red-500 uppercase mb-1">Based on Benchmarking</p>
                <h2 className="text-3xl font-extrabold tracking-tight">Your Top Match</h2>
              </div>
            </div>

            <div className="bg-white rounded-2xl overflow-hidden shadow-sm">
              <div className="flex flex-col md:flex-row">
                <div className="relative md:w-1/2">
                  <img src={TOP_MATCH.image} alt={TOP_MATCH.name} className="w-full h-64 md:h-full object-cover" />
                  <div className="absolute top-4 left-4">
                    <MatchBadge pct={TOP_MATCH.match} size="lg" />
                  </div>
                </div>
                <div className="md:w-1/2 p-7 flex flex-col justify-center">
                  <h3 className="text-2xl font-extrabold mb-2">{TOP_MATCH.name}</h3>
                  <div className="flex items-center gap-1.5 text-gray-400 text-sm mb-4">
                    <MapPin size={13} />
                    <span>{TOP_MATCH.location} · {TOP_MATCH.cuisine}</span>
                  </div>
                  <div className="flex gap-2 flex-wrap mb-6">
                    {TOP_MATCH.tags.map((t) => (
                      <span key={t} className="bg-green-50 text-green-700 text-xs font-semibold px-3 py-1.5 rounded-full border border-green-100">{t}</span>
                    ))}
                  </div>
                  <p className="text-gray-500 text-sm leading-relaxed mb-6">
                    A celebrated neighbourhood bistro blending Parisian technique with locally sourced ingredients. Chef Dupont's tasting menu changes weekly — expect the unexpected.
                  </p>
                  <button className="w-full bg-red-500 hover:bg-red-600 text-white text-sm font-bold py-3.5 rounded-xl transition-colors">
                    Reserve Table
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* Similar to Your Favorites */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-extrabold flex items-center gap-2">
                Similar to Your Favorites
                <Sparkles size={16} className="text-amber-400" />
              </h2>
              <button className="text-xs text-red-500 font-semibold flex items-center gap-0.5 hover:underline">
                See all <ChevronRight size={13} />
              </button>
            </div>

            <div className="grid grid-cols-3 gap-4">
              {recommended.map((r) => (
                <div key={r.id} className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                  <div className="relative">
                    <img src={r.image} alt={r.name} className="w-full h-40 object-cover" />
                    <div className="absolute bottom-3 left-3">
                      <MatchBadge pct={r.match} />
                    </div>
                  </div>
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-bold text-sm">{r.name}</p>
                        <p className="text-gray-400 text-xs mt-0.5">{r.subtitle}</p>
                      </div>
                      <div className="flex items-center gap-1 text-sm font-bold text-gray-700 shrink-0">
                        <Star size={12} className="fill-amber-400 text-amber-400" />
                        {r.rating}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* New Flavors for You */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-extrabold">New Flavors for You</h2>
              <button className="text-xs text-red-500 font-semibold flex items-center gap-0.5 hover:underline">
                See all <ChevronRight size={13} />
              </button>
            </div>

            <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
              {trending.map((r) => (
                <div key={r.id} className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col">
                  <div className="relative">
                    <img src={r.image} alt={r.name} className="w-full h-36 object-cover" />
                    <button
                      onClick={() => toggleSave(r.id)}
                      className="absolute top-2.5 right-2.5 w-7 h-7 bg-white/90 rounded-full flex items-center justify-center shadow-sm"
                    >
                      <Bookmark size={13} className={savedFlavors.has(r.id) ? "fill-red-500 text-red-500" : "text-gray-400"} />
                    </button>
                  </div>
                  <div className="p-3.5 flex flex-col flex-1">
                    <p className="font-bold text-sm mb-1">{r.name}</p>
                    <div className="flex items-center gap-1.5 mb-1">
                      <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-red-400 rounded-full" style={{ width: `${r.match}%` }} />
                      </div>
                      <span className="text-[10px] font-bold text-red-500">{r.match}%</span>
                    </div>
                    <p className="text-[10px] text-gray-400 font-semibold mb-1.5">{r.alignLabel}</p>
                    <p className="text-xs text-gray-500 leading-snug mb-3 flex-1">{r.desc}</p>
                    <div className="flex gap-1 flex-wrap">
                      {r.tags.map((t) => (
                        <span key={t} className="bg-gray-100 text-gray-500 text-[10px] font-semibold px-2 py-0.5 rounded-full">{t}</span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}