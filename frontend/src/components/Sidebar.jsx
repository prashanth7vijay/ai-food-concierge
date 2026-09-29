import { ChefHat, MessageCircle, Bookmark, Info } from "lucide-react";

const NAV_ITEMS = [
  { key: "chat", label: "Concierge", icon: MessageCircle },
  { key: "saved", label: "Saved", icon: Bookmark },
  { key: "about", label: "About", icon: Info },
];

export default function Sidebar({ active, onNavigate }) {
  return (
    <aside className="flex h-full w-16 flex-col items-center gap-6 border-r border-ink-soft/40 bg-ink py-5 sm:w-56 sm:items-stretch sm:px-4">
      <div className="flex items-center gap-2 px-1 sm:px-1">
        <ChefHat className="text-turmeric" size={24} />
        <span className="hidden font-display text-lg text-paper sm:inline">Food Concierge</span>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => onNavigate(key)}
            className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
              active === key
                ? "bg-paper/10 text-paper"
                : "text-paper/60 hover:bg-paper/5 hover:text-paper/90"
            }`}
          >
            <Icon size={18} />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </nav>

      <div className="hidden rounded-md border border-paper/15 px-3 py-2 text-[11px] leading-snug text-paper/50 sm:block">
        Demo data — not live availability.
      </div>
    </aside>
  );
}
