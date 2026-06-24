import { useState, useMemo, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import type { RootState, AppDispatch } from "./store";
import { toggleVisited, setVisited } from "./store/historySlice";
import { Search, Star, Check, ChevronRight, ChevronLeft, SlidersHorizontal, X, ChevronDown } from "lucide-react";
import Navbar from "./components/Navbar";
import { useUser } from "@clerk/clerk-react";

// ── Types ──────────────────────────────────────────────────────────────────
interface Restaurant {
  id: string;
  name: string;
  cuisine: string;
  tags: string[];
  price_range: string;
  rating: number;
  open: boolean;
  prep_time: string;
  image?: string;
}

const CUISINE_FILTERS = ["All Cuisines", "Italian", "Japanese", "Modern American", "French", "Thai", "Mexican", "Steakhouse"];
const SORT_OPTIONS = [
  { label: "Rating: High to Low", value: "rating_desc" },
  { label: "Rating: Low to High", value: "rating_asc" },
  { label: "Name: A–Z", value: "name_asc" },
  { label: "Name: Z–A", value: "name_desc" },
  { label: "Price: Low to High", value: "price_asc" },
  { label: "Price: High to Low", value: "price_desc" },
];
const PAGE_SIZE = 6;

// ── Helpers ────────────────────────────────────────────────────────────────
const priceToNum = (p: string) => (p.match(/\$/g) || []).length;

const UNSPLASH: Record<string, string> = {
  Italian: "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&h=380&fit=crop",
  Japanese: "https://images.unsplash.com/photo-1553621042-f6e147245754?w=600&h=380&fit=crop",
  "Modern American": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&h=380&fit=crop",
  French: "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&h=380&fit=crop",
  Thai: "https://images.unsplash.com/photo-1559314809-0d155014e29e?w=600&h=380&fit=crop",
  Mexican: "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=380&fit=crop",
  Steakhouse: "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&h=380&fit=crop",
};
const getImg = (r: Restaurant) => r.image ?? UNSPLASH[r.cuisine] ?? "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=380&fit=crop";

// ── Sub-components ─────────────────────────────────────────────────────────
function StarRating({ rating }: { rating: number }) {
  return (
    <span className="inline-flex items-center gap-1 bg-white/90 text-gray-800 text-xs font-semibold rounded-full px-2 py-1 shadow-sm">
      <Star size={11} className="fill-amber-400 text-amber-400" />
      {rating.toFixed(1)}
    </span>
  );
}

function RestaurantCard({
  restaurant,
  visited,
  onToggle,
}: {
  restaurant: Restaurant;
  visited: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="bg-white rounded-xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-md transition-shadow flex flex-col">
      <div className="relative">
        <img src={getImg(restaurant)} alt={restaurant.name} className="w-full h-48 object-cover" />
        <div className="absolute top-3 right-3">
          <StarRating rating={restaurant.rating} />
        </div>
        {!restaurant.open && (
          <div className="absolute top-3 left-3 bg-gray-900/70 text-white text-xs px-2 py-0.5 rounded-full">
            Closed
          </div>
        )}
      </div>
      <div className="p-4 flex flex-col flex-1">
        <div className="mb-1">
          <p className="text-[10px] font-semibold tracking-widest text-gray-400 uppercase mb-0.5">
            {restaurant.cuisine} · {restaurant.price_range}
          </p>
          <h3 className="font-bold text-base leading-tight">{restaurant.name}</h3>
        </div>
        <div className="flex flex-wrap gap-1 mb-3 mt-1">
          {restaurant.tags.slice(0, 3).map((t) => (
            <span key={t} className="bg-gray-100 text-gray-500 text-[10px] px-2 py-0.5 rounded-full capitalize">{t}</span>
          ))}
        </div>
        <p className="text-gray-400 text-xs mb-4">⏱ {restaurant.prep_time} avg wait</p>
        <button
          onClick={onToggle}
          className={`mt-auto w-full py-2.5 rounded-lg text-sm font-medium border transition-all ${
            visited
              ? "bg-red-500 text-white border-red-500"
              : "bg-white text-gray-700 border-gray-300 hover:border-gray-400"
          }`}
        >
          {visited ? (
            <span className="flex items-center justify-center gap-1.5">
              <Check size={14} /> Visited
            </span>
          ) : (
            "I've been here"
          )}
        </button>
      </div>
    </div>
  );
}

// ── Benchmarks Popup ───────────────────────────────────────────────────────
function BenchmarksPopup({
  visited,
  restaurants,
  onConfirm,
}: {
  visited: Set<string>;
  restaurants: Restaurant[];
  onConfirm: () => void;
}) {
  const visitedList = restaurants.filter((r) => visited.has(r.id));
  const preview = visitedList.slice(0, 2);
  const extra = visitedList.length - 2;

  return (
    <div className="fixed bottom-6 right-6 z-50 bg-white rounded-xl shadow-2xl border border-gray-100 p-4 w-72">
      <p className="text-[10px] font-bold tracking-widest text-gray-400 mb-2">YOUR BENCHMARKS</p>
      <div className="space-y-1 mb-3">
        {preview.map((r) => (
          <div key={r.id} className="flex justify-between text-sm">
            <span className="font-medium text-gray-800">{r.name}</span>
            <span className="text-gray-400">{r.cuisine}</span>
          </div>
        ))}
        {extra > 0 && <p className="text-xs text-gray-400">+ {extra} more…</p>}
      </div>
      <div className="border-t border-gray-100 pt-3">
        <button
          onClick={onConfirm}
          className="w-full bg-red-500 hover:bg-red-600 text-white font-semibold text-sm py-2.5 rounded-lg transition-colors"
        >
          Confirm Benchmarks
        </button>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────
export default function BenchmarksPage() {
  const [activeCuisine, setActiveCuisine] = useState("All Cuisines");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("rating_desc");
  const [sortOpen, setSortOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [confirmed, setConfirmed] = useState(false);
  const TARGET = 10;

  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const { isSignedIn, user } = useUser();

  const RANDOM_IMAGES = [
    "https://images.unsplash.com/photo-1553621042-f6e147245754?w=600&h=380&fit=crop",
    "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&h=380&fit=crop",
    "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&h=380&fit=crop",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=380&fit=crop",
    "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&h=380&fit=crop",
    "https://images.unsplash.com/photo-1559314809-0d155014e29e?w=600&h=380&fit=crop",
    "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=380&fit=crop",
  ];

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/frontend/businesses");
        if (!res.ok) throw new Error("Failed to fetch businesses");
        const data = await res.json();
        const mapped: Restaurant[] = data.map((b: any, i: number) => ({
          id: b.id ?? String(i + 1),
          name: b.name ?? `Business ${i + 1}`,
          cuisine: b.cuisine ?? "Various",
          tags: b.tags ?? [],
          price_range: b.price_range ?? b.price ?? "$",
          rating: b.rating ?? 4.5,
          open: b.open ?? true,
          prep_time: b.prep_time ?? "15 min",
          image: RANDOM_IMAGES[Math.floor(Math.random() * RANDOM_IMAGES.length)],
        }));
        setRestaurants(mapped);
      } catch (e) {
        console.error(e);
      }
    }
    load();
  }, []);

  const dispatch = useDispatch<AppDispatch>();
  const visited = useSelector((s: RootState) => s.history.visited);

  // Load history from Redis on mount/signin
  useEffect(() => {
    if (isSignedIn && user?.id) {
      async function loadRedisHistory() {
        try {
          const res = await fetch(`/api/frontend/history?user_id=${user?.id}`);
          if (res.ok) {
            const data = await res.json();
            if (data.history) {
              dispatch(setVisited(data.history));
            }
          }
        } catch (e) {
          console.error("Failed to load user history from Redis:", e);
        }
      }
      loadRedisHistory();
    }
  }, [isSignedIn, user?.id, dispatch]);

  const handleConfirmBenchmarks = async () => {
    setConfirmed(true);
    if (isSignedIn && user?.id) {
      try {
        await fetch("/api/frontend/history", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: user?.id,
            history: visited,
          }),
        });
      } catch (e) {
        console.error("Failed to save user history to Redis:", e);
      }
    }
  };
  const visitedSet = useMemo(() => new Set(visited), [visited]);

  const toggleVisit = (id: string) => {
    dispatch(toggleVisited(id));
  };

  const filtered = useMemo(() => {
    let list = [...restaurants];
    if (activeCuisine !== "All Cuisines") list = list.filter((r) => r.cuisine === activeCuisine);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (r) => r.name.toLowerCase().includes(q) || r.cuisine.toLowerCase().includes(q) || r.tags.some((t) => t.includes(q))
      );
    }
    list.sort((a, b) => {
      if (sort === "rating_desc") return b.rating - a.rating;
      if (sort === "rating_asc") return a.rating - b.rating;
      if (sort === "name_asc") return a.name.localeCompare(b.name);
      if (sort === "name_desc") return b.name.localeCompare(a.name);
      if (sort === "price_asc") return priceToNum(a.price_range) - priceToNum(b.price_range);
      if (sort === "price_desc") return priceToNum(b.price_range) - priceToNum(a.price_range);
      return 0;
    });
    return list;
  }, [activeCuisine, search, sort, restaurants]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const progress = Math.min((visited.length / TARGET) * 100, 100);
  const sortLabel = SORT_OPTIONS.find((o) => o.value === sort)?.label ?? "Sort";

  const handleFilterChange = (f: string) => { setActiveCuisine(f); setPage(1); };
  const handleSearch = (v: string) => { setSearch(v); setPage(1); };

  return (
    <div className="min-h-screen bg-white font-sans text-gray-900">
      <Navbar />

      <main className="max-w-5xl mx-auto px-6 pb-32">
        {/* Header */}
        <section className="pt-10 pb-6 flex items-start justify-between gap-8">
          <div className="flex-1">
            <h1 className="text-4xl font-bold tracking-tight mb-2">Set Your Benchmarks</h1>
            <p className="text-gray-500 text-sm max-w-md">
              Help TasteSync understand your palate. Select at least {TARGET} restaurants you've visited to establish your personal flavor profile.
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-[10px] font-bold tracking-widest text-red-500 mb-1">PROGRESS</p>
            <p className="text-4xl font-extrabold tracking-tight">
              {visited.length}<span className="text-gray-300">/{TARGET}</span>
            </p>
            <p className="text-xs text-gray-400">Benchmarks</p>
          </div>
        </section>

        {/* Progress bar */}
        <div className="h-2 bg-gray-100 rounded-full mb-8 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${progress}%`,
              background: "linear-gradient(90deg, #ef4444 0%, #b45309 50%, #15803d 100%)",
            }}
          />
        </div>

        {/* Controls */}
        <div className="flex flex-col gap-3 mb-6">
          {/* Filter pills */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-gray-500 mr-1">Filter by Cuisine:</span>
            {CUISINE_FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => handleFilterChange(f)}
                className={`px-3.5 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                  activeCuisine === f
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Search + Sort */}
          <div className="flex gap-3 mt-1">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                value={search}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Search by name, cuisine, or tag…"
                className="w-full pl-9 pr-9 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-200"
              />
              {search && (
                <button onClick={() => handleSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  <X size={14} />
                </button>
              )}
            </div>

            {/* Sort dropdown */}
            <div className="relative">
              <button
                onClick={() => setSortOpen((v) => !v)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-gray-200 text-sm font-medium text-gray-700 hover:border-gray-400 bg-white whitespace-nowrap"
              >
                <SlidersHorizontal size={14} className="text-gray-400" />
                {sortLabel}
                <ChevronDown size={13} className="text-gray-400" />
              </button>
              {sortOpen && (
                <div className="absolute right-0 top-full mt-1 bg-white border border-gray-100 rounded-xl shadow-xl z-20 min-w-48 py-1 overflow-hidden">
                  {SORT_OPTIONS.map((o) => (
                    <button
                      key={o.value}
                      onClick={() => { setSort(o.value); setSortOpen(false); setPage(1); }}
                      className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 transition-colors ${sort === o.value ? "text-red-500 font-semibold" : "text-gray-700"}`}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Result count */}
        <p className="text-xs text-gray-400 mb-4">
          Showing {paginated.length} of {filtered.length} restaurants
          {search && ` for "${search}"`}
        </p>

        {/* Grid */}
        {paginated.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
            {paginated.map((r) => (
              <RestaurantCard
                key={r.id}
                restaurant={r}
                visited={visitedSet.has(r.id)}
                onToggle={() => toggleVisit(r.id)}
              />
            ))}
          </div>
        ) : (
          <div className="py-20 text-center">
            <p className="text-gray-300 text-5xl mb-4">🍽</p>
            <p className="text-gray-500 font-medium">No restaurants found</p>
            <p className="text-gray-400 text-sm mt-1">Try a different search or filter.</p>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-10">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg border border-gray-200 text-gray-500 disabled:opacity-30 hover:border-gray-400 transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            {Array.from({ length: totalPages }).map((_, i) => (
              <button
                key={i}
                onClick={() => setPage(i + 1)}
                className={`w-9 h-9 rounded-lg text-sm font-medium border transition-colors ${
                  page === i + 1
                    ? "bg-red-500 text-white border-red-500"
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                }`}
              >
                {i + 1}
              </button>
            ))}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 rounded-lg border border-gray-200 text-gray-500 disabled:opacity-30 hover:border-gray-400 transition-colors"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}
      </main>

      {/* Benchmarks popup — show when ≥2 visited */}
      {visited.length >= 2 && !confirmed && (
        <BenchmarksPopup
          visited={visitedSet}
          restaurants={restaurants}
          onConfirm={handleConfirmBenchmarks}
        />
      )}

      {confirmed && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-600 text-white rounded-xl shadow-2xl px-5 py-4 flex items-center gap-3">
          <Check size={18} />
          <div>
            <p className="font-semibold text-sm">Benchmarks confirmed!</p>
            <p className="text-xs text-green-200">Your flavor profile is being built.</p>
          </div>
          <button onClick={() => setConfirmed(false)} className="ml-2 text-green-200 hover:text-white">
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}