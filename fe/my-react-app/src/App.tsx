import { useState, useEffect } from "react";
import { Star, Bookmark, MapPin, ChevronRight } from "lucide-react";
import Navbar from "./components/Navbar";

const cuisineFilters = ["All", "Sushi", "Italian", "French", "Mexican", "Thai", "Steakhouse", "Vegan"];

const initialTrendingRestaurants = [
  {
    id: 1,
    name: "Orizuru Sushi",
    type: "Modern Japanese",
    distance: "0.8 miles",
    rating: 4.9,
    price: "$$$",
    tags: ["Chef's Table", "Omakase"],
    image: "https://images.unsplash.com/photo-1553621042-f6e147245754?w=400&h=220&fit=crop",
  },
  {
    id: 2,
    name: "La Lanterna",
    type: "Authentic Italian",
    distance: "1.2 miles",
    rating: 4.7,
    price: "$$",
    tags: ["Handmade Pasta"],
    image: "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=220&fit=crop",
  },
  {
    id: 3,
    name: "Iron & Oak",
    type: "Modern Grill",
    distance: "2.5 miles",
    rating: 4.8,
    price: "$$$$",
    tags: ["Dry Aged", "Cocktails"],
    image: "https://images.unsplash.com/photo-1544025162-d76694265947?w=400&h=220&fit=crop",
  },
  {
    id: 4,
    name: "Verdant Kitchen",
    type: "Plant-Based",
    distance: "3.1 miles",
    rating: 4.6,
    price: "$$",
    tags: ["Sustainable"],
    image: "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&h=220&fit=crop",
  },
];



const initialRecommended = [
  {
    id: 1,
    name: "The Azure Terrace",
    reviews: 124,
    rating: 4,
    description:
      "Experience authentic coastal cuisine with ingredients sourced daily from local harbors. Chef Maria's signature…",
    metrics: [
      { label: "Flavor", value: 98 },
      { label: "Service", value: 92 },
    ],
    image: "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&h=400&fit=crop",
  },
  {
    id: 2,
    name: "Heritage Bistro",
    reviews: 89,
    rating: 4,
    description:
      "A refined take on classic French bistro fare. From the perfect onion soup to delicate soufflés, Heritage brings the soul of…",
    metrics: [
      { label: "Flavor", value: 95 },
      { label: "Value", value: 88 },
    ],
    image: "https://images.unsplash.com/photo-1424847651672-bf20a4b0982b?w=800&h=400&fit=crop",
  },
];


 
function StarRating({ rating, max = 5 }: { rating: number; max?: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: max }).map((_, i) => (
        <Star
          key={i}
          size={14}
          className={i < rating ? "fill-orange-400 text-orange-400" : "fill-gray-200 text-gray-200"}
        />
      ))}
    </div>
  );
}

export default function TasteSync() {
  const [trendingRestaurants, setTrendingRestaurants] = useState(initialTrendingRestaurants);
  const [recommended, setRecommended] = useState(initialRecommended);

  useEffect(() => {
   // Try fetching data from backend; fall back to the initial static data if unavailable
   fetch('/api/frontend/trending')
     .then((r) => (r.ok ? r.json() : Promise.reject()))
     .then((data) => setTrendingRestaurants(data))
     .catch(() => {});

   fetch('/api/frontend/recommended')
     .then((r) => (r.ok ? r.json() : Promise.reject()))
     .then((data) => setRecommended(data))
     .catch(() => {});
  }, []);

  const [activeFilter, setActiveFilter] = useState("All");
  const [saved, setSaved] = useState<Set<number>>(new Set());

  const toggleSave = (id: number) => {
    setSaved((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-white font-sans text-gray-900">
      <Navbar />

      <main className="max-w-5xl mx-auto px-6 pb-20">
        {/* Hero */}
        <section className="pt-12 pb-6">
          <h1 className="text-4xl font-bold tracking-tight mb-2">Find your next meal</h1>
          <p className="text-gray-500 text-base">Explore the city's finest dining experiences curated for your unique palate.</p>
        </section>

        {/* Cuisine Filters */}
        <div className="flex flex-wrap gap-2 mb-10">
          {cuisineFilters.map((f) => (
            <button
              key={f}
              onClick={() => setActiveFilter(f)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                activeFilter === f
                  ? "bg-red-500 text-white border-red-500"
                  : "bg-white text-gray-700 border-gray-300 hover:border-gray-400"
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Trending Now */}
        <section className="mb-12">
          <div className="flex items-baseline justify-between mb-1">
            <h2 className="text-xl font-bold">Trending Now</h2>
            <button className="text-sm text-red-500 font-medium flex items-center gap-0.5 hover:underline">
              View all <ChevronRight size={14} />
            </button>
          </div>
          <p className="text-gray-400 text-sm mb-5">The most talked-about tables this week.</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {trendingRestaurants.map((r) => (
              <div key={r.id} className="rounded-xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-md transition-shadow bg-white">
                <div className="relative">
                  <img src={r.image} alt={r.name} className="w-full h-36 object-cover" />
                  <span className="absolute top-2 right-2 bg-white text-gray-800 text-xs font-semibold rounded-full px-2 py-0.5 flex items-center gap-1 shadow-sm">
                    <Star size={11} className="fill-amber-400 text-amber-400" />
                    {r.rating}
                  </span>
                </div>
                <div className="p-3">
                  <div className="flex justify-between items-start mb-0.5">
                    <span className="font-semibold text-sm leading-tight">{r.name}</span>
                    <span className="text-gray-400 text-xs ml-1 shrink-0">{r.price}</span>
                  </div>
                  <p className="text-gray-400 text-xs mb-2">{r.type} • {r.distance}</p>
                  <div className="flex flex-wrap gap-1">
                    {r.tags.map((t) => (
                      <span key={t} className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">{t}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Recommended for You */}
        <section className="bg-gray-50 rounded-2xl p-6 mb-12">
          <h2 className="text-xl font-bold mb-0.5">Recommended for You</h2>
          <p className="text-gray-400 text-sm mb-6">Based on your love for Mediterranean and Seafood.</p>
          <div className="grid md:grid-cols-2 gap-5">
            {recommended.map((r) => (
              <div key={r.id} className="bg-white rounded-xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                <img src={r.image} alt={r.name} className="w-full h-48 object-cover" />
                <div className="p-4">
                  <div className="flex justify-between items-start mb-1">
                    <h3 className="font-bold text-lg">{r.name}</h3>
                    <button
                      onClick={() => toggleSave(r.id)}
                      className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
                    >
                      <Bookmark
                        size={16}
                        className={saved.has(r.id) ? "fill-red-500 text-red-500" : "text-gray-400"}
                      />
                    </button>
                  </div>
                  <div className="flex items-center gap-2 mb-3">
                    <StarRating rating={r.rating} />
                    <span className="text-gray-400 text-xs">({r.reviews} Reviews)</span>
                  </div>
                  <p className="text-gray-500 text-sm mb-4 leading-relaxed">{r.description}</p>
                  <div className="space-y-2">
                    {r.metrics.map((m) => (
                      <div key={m.label}>
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>{m.label}</span>
                          <span>{m.value}%</span>
                        </div>
                        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-amber-400 rounded-full"
                            style={{ width: `${m.value}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Map FAB */}
      <button className="fixed bottom-24 right-6 w-12 h-12 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center shadow-lg transition-colors z-40">
        <MapPin size={20} />
      </button>

      {/* CTA Footer */}
      <footer className="border-t border-gray-100 px-6 py-8">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-gray-900">Ready to explore?</p>
            <p className="text-gray-400 text-sm">Join 10k+ foodies discovering new flavors daily.</p>
          </div>
          <div className="flex gap-3">
            <button className="bg-red-500 hover:bg-red-600 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors">
              Create Free Account
            </button>
            <button className="bg-white border border-gray-300 hover:border-gray-400 text-gray-700 text-sm font-medium px-5 py-2.5 rounded-lg transition-colors">
              Sign In
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}