import { useEffect, useRef } from "react";
import { NavLink } from "react-router";
import { 
  X, Compass, Clock, Sparkles, BarChart2, LogIn, UserPlus, Heart
} from "lucide-react";
import { 
  SignedIn, SignedOut, SignInButton, SignUpButton, UserButton, useUser 
} from "@clerk/clerk-react";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const NAV_ITEMS = [
  { label: "Discover", to: "/", icon: <Compass size={18} /> },
  { label: "History", to: "/history", icon: <Clock size={18} /> },
  { label: "For You", to: "/foryou", icon: <Sparkles size={18} /> },
  { label: "Dashboard", to: "/dashboard", icon: <BarChart2 size={18} /> },
];

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const sidebarRef = useRef<HTMLDivElement>(null);
  const { user } = useUser();

  // Close sidebar on escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  // Close when clicking outside of the sidebar panel
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      onClick={handleBackdropClick}
      className={`fixed inset-0 z-50 flex justify-start bg-black/40 backdrop-blur-xs transition-opacity duration-300 ${
        isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
      }`}
    >
      <div
        ref={sidebarRef}
        className={`w-80 h-full bg-[#f8f9fa] shadow-2xl flex flex-col transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="p-5 border-b border-gray-100 bg-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Heart size={20} className="text-red-500 fill-red-500" />
            <span className="text-xl font-extrabold text-red-500 tracking-tight">TasteSync</span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close menu"
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>

        {/* User Authentication Status Section */}
        <div className="p-6 bg-white border-b border-gray-100">
          <SignedOut>
            <div className="space-y-4">
              <div>
                <p className="text-sm font-bold text-gray-800">Your Culinary Journey Awaits</p>
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                  Sign in to personalize your flavor profile, track your culinary benchmarks, and discover restaurants tailored for your palate.
                </p>
              </div>
              <div className="space-y-2">
                <SignInButton mode="modal">
                  <button className="w-full flex items-center justify-center gap-2 bg-red-500 hover:bg-red-600 text-white text-sm font-bold py-2.5 px-4 rounded-xl transition-all duration-200 shadow-md shadow-red-500/10 active:scale-[0.98] cursor-pointer">
                    <LogIn size={15} />
                    Sign In
                  </button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <button className="w-full flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-gray-700 text-sm font-bold py-2.5 px-4 rounded-xl transition-all duration-200 border border-gray-200 active:scale-[0.98] cursor-pointer">
                    <UserPlus size={15} />
                    Create Account
                  </button>
                </SignUpButton>
              </div>
            </div>
          </SignedOut>

          <SignedIn>
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 overflow-hidden">
                <div className="w-10 h-10 rounded-full bg-gray-100 overflow-hidden shrink-0 border border-gray-200">
                  {user?.imageUrl ? (
                    <img src={user.imageUrl} alt="User Avatar" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full bg-gray-200 flex items-center justify-center text-gray-500 font-bold">
                      {user?.firstName?.[0] || "?"}
                    </div>
                  )}
                </div>
                <div className="overflow-hidden">
                  <p className="text-sm font-bold text-gray-800 truncate">
                    {user?.fullName || "TasteSync Foodie"}
                  </p>
                  <p className="text-[11px] text-gray-400 truncate">
                    {user?.primaryEmailAddress?.emailAddress}
                  </p>
                </div>
              </div>
              <div className="shrink-0 scale-110">
                <UserButton afterSignOutUrl="/" />
              </div>
            </div>
          </SignedIn>
        </div>

        {/* Navigation Section */}
        <nav className="flex-1 p-5 space-y-1.5 overflow-y-auto">
          <p className="text-[10px] font-bold tracking-widest text-gray-400 uppercase px-3 mb-2">
            Navigation
          </p>
          {NAV_ITEMS.map(({ label, to, icon }) => (
            <NavLink
              key={label}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3.5 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                  isActive
                    ? "bg-red-50 text-red-500"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-100/70"
                }`
              }
            >
              {icon}
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-5 border-t border-gray-100 bg-white text-center">
          <p className="text-[10px] text-gray-400">
            TasteSync &copy; 2026. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
}
