import { useMemo, useState } from "react";
import { X, Scale } from "lucide-react";
import { useAppState } from "../context/AppStateContext";
import { api } from "../api/client";

export default function CompareTray() {
  const { compareIds, toggleCompare, clearCompare, messages } = useAppState();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const stagedItems = useMemo(() => {
    const allRecs = messages.flatMap((m) => m.recommendations || []);
    return compareIds
      .map((id) => allRecs.find((r) => r.item.id === id)?.item)
      .filter(Boolean);
  }, [compareIds, messages]);

  const runCompare = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.compareItems(compareIds);
      setSummary(result.summary);
    } catch (err) {
      setError(err.message || "Couldn't compare those items.");
    } finally {
      setLoading(false);
    }
  };

  if (compareIds.length === 0) {
    return (
      <div>
        <h3 className="font-display text-sm text-ink-soft">Compare</h3>
        <p className="mt-2 text-xs text-ink-soft/80">
          Add two or more dishes from the chat to compare them side by side.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h3 className="font-display text-sm text-ink-soft">Compare ({compareIds.length})</h3>
        <button onClick={clearCompare} className="text-xs text-ink-soft/70 hover:text-chili">
          Clear
        </button>
      </div>

      <ul className="mt-2 space-y-1.5">
        {stagedItems.map((item) => (
          <li key={item.id} className="flex items-center justify-between gap-2 text-xs">
            <span className="truncate text-ink">{item.name}</span>
            <button
              onClick={() => toggleCompare(item.id)}
              aria-label={`Remove ${item.name} from compare`}
              className="shrink-0 text-ink-soft/60 hover:text-chili"
            >
              <X size={12} />
            </button>
          </li>
        ))}
      </ul>

      <button
        onClick={runCompare}
        disabled={compareIds.length < 2 || loading}
        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-md bg-plum px-3 py-1.5 text-xs font-medium text-paper disabled:opacity-40"
      >
        <Scale size={13} />
        {loading ? "Comparing…" : "Compare now"}
      </button>

      {error && <p className="mt-2 text-xs text-chili">{error}</p>}

      {summary && (
        <dl className="mt-3 space-y-1 rounded-md bg-plum-soft px-2.5 py-2 text-[11px] text-ink">
          <div>Cheapest: {stagedItems.find((i) => i.id === summary.cheapest_id)?.name}</div>
          <div>Highest rated: {stagedItems.find((i) => i.id === summary.highest_rated_id)?.name}</div>
          <div>Likely lighter: {stagedItems.find((i) => i.id === summary.likely_lighter_id)?.name}</div>
        </dl>
      )}
    </div>
  );
}
