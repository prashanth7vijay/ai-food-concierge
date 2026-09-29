import { Bookmark, X } from "lucide-react";
import { useAppState } from "../context/AppStateContext";

export default function SavedItemsPanel() {
  const { savedItems, removeSavedItem } = useAppState();

  return (
    <div>
      <h3 className="font-display text-sm text-ink-soft">Saved</h3>
      {savedItems.length === 0 ? (
        <p className="mt-2 text-xs text-ink-soft/80">
          Nothing saved yet — tap "Save" on a recommendation to keep it here.
        </p>
      ) : (
        <ul className="mt-2 space-y-2">
          {savedItems.map(({ saved_item_id, item }) => (
            <li
              key={saved_item_id}
              className="flex items-center justify-between gap-2 rounded-md border border-line bg-paper-raised px-2.5 py-2 text-xs"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{item.name}</p>
                <p className="truncate text-ink-soft">
                  {item.restaurant_name} · ₹{item.price}
                </p>
              </div>
              <button
                onClick={() => removeSavedItem(saved_item_id)}
                aria-label={`Remove ${item.name} from saved`}
                className="shrink-0 text-ink-soft/60 hover:text-chili"
              >
                <X size={13} />
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 flex items-center gap-1 text-[11px] text-ink-soft/60">
        <Bookmark size={11} /> Saved items are stored per browser, on this demo account.
      </p>
    </div>
  );
}
