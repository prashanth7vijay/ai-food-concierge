import { useAppState } from "../context/AppStateContext";

const ROWS = [
  { key: "is_vegetarian", label: "Vegetarian", format: (v) => (v === null ? "—" : v ? "Yes" : "No") },
  { key: "spice_level", label: "Spice level", format: (v) => (v ? v[0].toUpperCase() + v.slice(1) : "—") },
  { key: "max_budget", label: "Max budget", format: (v) => (v ? `₹${v}` : "—") },
  { key: "preferred_cuisine", label: "Preferred cuisine", format: (v) => v || "—" },
];

export default function PreferencesPanel() {
  const { preferences } = useAppState();
  const hasAny = preferences && Object.values(preferences).some((v) => v !== null && v !== undefined);

  return (
    <div>
      <h3 className="font-display text-sm text-ink-soft">Your preferences</h3>
      {!hasAny ? (
        <p className="mt-2 text-xs text-ink-soft/80">
          Nothing learned yet — mention a lasting preference (e.g. "I usually prefer spicy food")
          and I'll remember it.
        </p>
      ) : (
        <dl className="mt-2 space-y-1.5">
          {ROWS.map(({ key, label, format }) => (
            <div key={key} className="flex items-center justify-between text-xs">
              <dt className="text-ink-soft">{label}</dt>
              <dd className="font-medium text-ink">{format(preferences?.[key])}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
