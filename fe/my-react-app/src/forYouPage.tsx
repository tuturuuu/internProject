import { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import type { RootState } from "./store";
import { RefreshCw, MapPin, Star, Bookmark, Sparkles, Flame, ChevronRight, Settings2 } from "lucide-react";
import Navbar from "./components/Navbar";
import { useUser } from "@clerk/clerk-react";

type Model = "XGBoost" | "LightGBM" | "CatBoost" | "LLM" | "Parallel" | "Rerank";

const MODELS: Model[] = ["XGBoost", "LightGBM", "CatBoost", "LLM", "Parallel", "Rerank"];

const _RECO_IMG = [
  "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&h=400&fit=crop",
  "https://images.unsplash.com/photo-1424847651672-bf20a4b0982b?w=800&h=400&fit=crop",
  "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&h=400&fit=crop",
];

const TOP_MATCH = {
  name: "L'Artisan Modern Bistro",
  match: 98,
  location: "Upper East Side",
  cuisine: "Contemporary French",
  tags: ["High Value", "Consistent Quality"],
  image: "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1200&h=600&fit=crop",
  description: "A celebrated neighbourhood bistro blending Parisian technique with locally sourced ingredients.",
};



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
  const [recommended, setRecommended] = useState<any[]>([]);
  const [trending, setTrending] = useState<any[]>([]);
  const { isSignedIn, user } = useUser();

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/frontend/home");
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

  // compute current top match from recommendations when available
  const topMatch = recommended && recommended.length > 0
    ? {
        name: recommended[0].name || TOP_MATCH.name,
        match: recommended[0].match ?? TOP_MATCH.match,
        location: recommended[0].location || TOP_MATCH.location,
        cuisine: recommended[0].cuisine || TOP_MATCH.cuisine,
        tags: recommended[0].tags || TOP_MATCH.tags,
        image: recommended[0].image || TOP_MATCH.image,
        description: recommended[0].description || recommended[0].desc || TOP_MATCH.description || "",
      }
    : TOP_MATCH;

  const [activeModel, setActiveModel] = useState<Model>("XGBoost");
  const [k, setK] = useState(10);
  const [refreshing, setRefreshing] = useState(false);
  const [savedFlavors, setSavedFlavors] = useState<Set<string>>(new Set());

  const visited = useSelector((s: RootState) => s.history.visited);

  const handleRefresh = async () => {
    setRefreshing(true);

    // build history from redux visited
    const history = Array.isArray(visited) ? visited : [];
    const rankerMap: Record<string, string> = {
      XGBoost: "xgboost",
      LightGBM: "lightgbm",
      CatBoost: "catboost",
      LLM: "llm",
      Parallel: "xgboost",
      Rerank: "xgboost",
    };
    const ranker = rankerMap[activeModel] ?? "xgboost";

    try {
      const res = await fetch("/api/search/recommendations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          user_id: isSignedIn && user?.id ? user.id : undefined,
          history, 
          sample_size: 20, 
          ranker, 
          top_k: k 
        }),
      });
      if (res.ok) {
        const data = await res.json();
        console.log(data)
        // map recommendations into UI-friendly objects
        const mapped = (data.recommendations || []).map((r: any, i: number) => ({
          id: r.restaurant_id,
          name: r.name,
          match: Math.round((r.score ?? 0) * 100),
          rating: Math.round(((r.score ?? 0) * 5) * 10) / 10,
          description: r.name,
          metrics: [{ label: "Score", value: Math.round((r.score ?? 0) * 100) }],
          image: _RECO_IMG[i % _RECO_IMG.length],
        }));
        setRecommended(mapped);
      } else {
        console.error("Recommendations failed", await res.text());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
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
                  <img src={topMatch.image} alt={topMatch.name} className="w-full h-64 md:h-full object-cover" />
                  <div className="absolute top-4 left-4">
                    <MatchBadge pct={topMatch.match} size="lg" />
                  </div>
                </div>
                <div className="md:w-1/2 p-7 flex flex-col justify-center">
                  <h3 className="text-2xl font-extrabold mb-2">{topMatch.name}</h3>
                  <div className="flex items-center gap-1.5 text-gray-400 text-sm mb-4">
                    <MapPin size={13} />
                    <span>{topMatch.location} · {topMatch.cuisine}</span>
                  </div>
                  <div className="flex gap-2 flex-wrap mb-6">
                    {topMatch.tags.map((t: string) => (
                      <span key={t} className="bg-green-50 text-green-700 text-xs font-semibold px-3 py-1.5 rounded-full border border-green-100">{t}</span>
                    ))}
                  </div>
                  <p className="text-gray-500 text-sm leading-relaxed mb-6">
                    {topMatch.description ?? "A celebrated neighbourhood bistro blending Parisian technique with locally sourced ingredients. Chef Dupont's tasting menu changes weekly — expect the unexpected."}
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

            <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))" }}>
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
                      {r.tags.map((t: string) => (
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