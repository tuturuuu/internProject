import { useState } from "react";
import { Link, NavLink } from "react-router";
import { Search } from "lucide-react";
import { useUser } from "@clerk/clerk-react";
import Sidebar from "./Sidebar";

const NAV_ITEMS = [
  { label: "Discover", to: "/" },
  { label: "History", to: "/history" },
  { label: "For You", to: "/foryou" },
  { label: "Dashboard", to: "/dashboard" },
];

export default function Navbar() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { isSignedIn, user } = useUser();

  const avatarUrl = isSignedIn && user?.imageUrl ? user.imageUrl : "https://i.pravatar.cc/64?img=12";

  return (
    <>
      <header className="sticky top-0 z-40 bg-white border-b border-gray-100 px-6 py-3 flex items-center gap-4">
        <button 
          onClick={() => setIsSidebarOpen(true)}
          className="w-8 h-8 rounded-full bg-gray-200 overflow-hidden shrink-0 block hover:opacity-80 transition-opacity cursor-pointer border border-gray-200"
          aria-label="Open sidebar menu"
        >
          <img src={avatarUrl} alt="avatar" className="w-full h-full object-cover" />
        </button>
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
        <button className="text-gray-500 hover:text-gray-800 ml-2 cursor-pointer">
          <Search size={18} />
        </button>
      </header>

      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
    </>
  );
}