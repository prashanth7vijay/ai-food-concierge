import { useAppState } from "../context/AppStateContext";
import { Check, X } from "lucide-react";

export default function AgentActivityPanel() {
  const { activity } = useAppState();

  return (
    <div>
      <h3 className="font-display text-sm text-ink-soft">Agent activity</h3>
      {activity.length === 0 ? (
        <p className="mt-2 text-xs text-ink-soft/80">
          Send a message and I'll show the steps I take here.
        </p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {activity.map((event, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-ink-soft">
              {event.status === "failed" ? (
                <X size={13} className="mt-0.5 shrink-0 text-chili" />
              ) : (
                <Check size={13} className="mt-0.5 shrink-0 text-curry" />
              )}
              <span>{event.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
