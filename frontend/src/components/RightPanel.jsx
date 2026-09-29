import PreferencesPanel from "./PreferencesPanel";
import AgentActivityPanel from "./AgentActivityPanel";
import CompareTray from "./CompareTray";
import SavedItemsPanel from "./SavedItemsPanel";

export default function RightPanel() {
  return (
    <aside className="hidden w-72 shrink-0 flex-col gap-6 overflow-y-auto border-l border-line bg-paper-raised/60 px-4 py-6 lg:flex">
      <PreferencesPanel />
      <div className="h-px bg-line" />
      <AgentActivityPanel />
      <div className="h-px bg-line" />
      <CompareTray />
      <div className="h-px bg-line" />
      <SavedItemsPanel />
    </aside>
  );
}
