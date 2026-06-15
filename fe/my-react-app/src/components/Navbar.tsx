import { Link, NavLink } from "react-router";
import { Search } from "lucide-react";

const NAV_ITEMS = [
  { label: "Discover", to: "/" },
  { label: "History", to: "/history" },
  { label: "For You", to: "/foryou" },
  { label: "Profile", to: "/profile" },
];

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-100 px-6 py-3 flex items-center gap-4">
      <Link to="/" className="w-8 h-8 rounded-full bg-gray-200 overflow-hidden shrink-0 block">
        <img src="https://i.pravatar.cc/64?img=12" alt="avatar" className="w-full h-full object-cover" />
      </Link>
      <Link to="/" className="text-red-500 font-bold text-xl tracking-tight">
        TasteSync
      </Link>
      <div className="flex-1" />
      <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
        {NAV_ITEMS.map(({ label, to }) => (
          <NavLink
            key={label}
            to={to}
            className={({ isActive }) =>
              isActive ? "text-red-500" : "text-gray-500 hover:text-gray-800"
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <button className="text-gray-500 hover:text-gray-800 ml-2">
        <Search size={18} />
      </button>
    </header>
  );
}