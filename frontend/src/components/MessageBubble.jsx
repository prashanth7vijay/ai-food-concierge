import RecommendationCard from "./RecommendationCard";
import { AlertTriangle } from "lucide-react";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-ink px-4 py-2.5 text-sm text-paper">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start gap-3">
      <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-line bg-paper-raised px-4 py-2.5 text-sm text-ink">
        {message.content}
      </div>

      {message.errors?.length > 0 && (
        <div className="flex items-start gap-2 rounded-md border border-chili/40 bg-chili-soft/60 px-3 py-2 text-xs text-ink">
          <AlertTriangle size={14} className="mt-0.5 shrink-0 text-chili" />
          <span>{message.errors.join(" ")}</span>
        </div>
      )}

      {message.recommendations?.length > 0 && (
        <div className="grid w-full gap-3 sm:grid-cols-2">
          {message.recommendations.map((rec) => (
            <RecommendationCard key={rec.item.id} recommendation={rec} />
          ))}
        </div>
      )}
    </div>
  );
}
