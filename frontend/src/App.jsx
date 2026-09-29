import { useState } from "react";
import { AppStateProvider } from "./context/AppStateContext";
import Sidebar from "./components/Sidebar";
import ChatPanel from "./components/ChatPanel";
import RightPanel from "./components/RightPanel";
import SavedItemsPanel from "./components/SavedItemsPanel";

function AboutPane() {
  return (
    <div className="mx-auto max-w-xl px-8 py-10 text-sm text-ink-soft">
      <h2 className="font-display text-2xl text-ink">About this demo</h2>
      <p className="mt-3">
        AI Food Concierge is a portfolio project demonstrating an agentic recommendation
        system: a LangGraph agent plans which tools to call, deterministic backend logic
        does the filtering, ranking, and persistence, and the language model never touches
        the database directly.
      </p>
      <p className="mt-3">
        All restaurant and menu data shown here is synthetic demo data created for this
        project — nothing is scraped or sourced from any live delivery platform.
      </p>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState("chat");

  return (
    <AppStateProvider>
      <div className="flex h-screen w-full overflow-hidden bg-paper">
        <Sidebar active={view} onNavigate={setView} />

        {view === "chat" && (
          <>
            <ChatPanel />
            <RightPanel />
          </>
        )}

        {view === "saved" && (
          <div className="flex-1 overflow-y-auto px-8 py-10">
            <div className="mx-auto max-w-md">
              <SavedItemsPanel />
            </div>
          </div>
        )}

        {view === "about" && <AboutPane />}
      </div>
    </AppStateProvider>
  );
}
