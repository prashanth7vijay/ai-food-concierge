const PROMPTS = [
  "Spicy vegetarian food under ₹400",
  "Something light for dinner",
  "Show me highly rated biryani",
  "I usually prefer North Indian food",
];

export default function SuggestedPrompts({ onPick }) {
  return (
    <div className="mx-auto max-w-md text-center">
      <h2 className="font-display text-2xl text-ink">What are you in the mood for?</h2>
      <p className="mt-2 text-sm text-ink-soft">
        Describe what you'd like, in your own words — I'll narrow it down.
      </p>
      <div className="mt-5 flex flex-wrap justify-center gap-2">
        {PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => onPick(p)}
            className="rounded-full border border-line bg-paper-raised px-3 py-1.5 text-xs text-ink-soft transition-colors hover:border-chili hover:text-ink"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
