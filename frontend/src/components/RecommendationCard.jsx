import { Flame, Leaf, Plus, Check, Bookmark, Info } from "lucide-react";
import { useAppState } from "../context/AppStateContext";

const SPICE_LABEL = { mild: "Mild", medium: "Medium", spicy: "Spicy" };

export default function RecommendationCard({ recommendation }) {
  const { item, reason } = recommendation;
  const { compareIds, toggleCompare, saveItem } = useAppState();
  const inCompare = compareIds.includes(item.id);

  return (
    <div
      className="flex gap-3 rounded-lg border border-line bg-paper-raised p-4 shadow-[2px_2px_0_0_var(--color-line)]"
      style={{
        borderLeft: `4px solid ${item.is_vegetarian ? "var(--color-curry)" : "var(--color-chili)"}`,
      }}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-display text-lg leading-tight text-ink">{item.name}</h3>
            <p className="text-sm text-ink-soft">{item.restaurant_name}</p>
          </div>
          <span className="whitespace-nowrap font-mono text-sm font-medium text-ink">
            ₹{item.price}
          </span>
        </div>

        <p className="mt-2 line-clamp-2 text-sm text-ink-soft">{item.description}</p>

        <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="inline-flex items-center gap-1 rounded-full bg-turmeric-soft px-2 py-0.5 text-ink">
            ★ {item.rating.toFixed(1)}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-chili-soft px-2 py-0.5 text-ink">
            <Flame size={12} /> {SPICE_LABEL[item.spice_level] ?? item.spice_level}
          </span>
          {item.is_vegetarian && (
            <span className="inline-flex items-center gap-1 rounded-full bg-curry-soft px-2 py-0.5 text-ink">
              <Leaf size={12} /> Veg
            </span>
          )}
          <span className="rounded-full bg-line/50 px-2 py-0.5 text-ink-soft">{item.cuisine}</span>
        </div>

        <p className="mt-3 flex items-start gap-1.5 text-xs text-ink-soft">
          <Info size={13} className="mt-0.5 shrink-0" />
          <span>{reason}</span>
        </p>

        <div className="mt-3 flex items-center gap-2">
          <button
            onClick={() => toggleCompare(item.id)}
            className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors ${
              inCompare
                ? "border-plum bg-plum-soft text-plum"
                : "border-line text-ink-soft hover:border-plum"
            }`}
          >
            {inCompare ? <Check size={13} /> : <Plus size={13} />}
            Compare
          </button>
          <button
            onClick={() => saveItem(item.id)}
            className="inline-flex items-center gap-1 rounded-md border border-line px-2.5 py-1.5 text-xs font-medium text-ink-soft transition-colors hover:border-turmeric"
          >
            <Bookmark size={13} />
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
