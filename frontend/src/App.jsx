import { useState, useEffect, useRef } from "react";
import { signInWithEmailAndPassword, signOut, onAuthStateChanged } from "firebase/auth";
import MDEditor from "@uiw/react-md-editor";
import { auth } from "./lib/firebase";
import api from "./lib/api";
import ChatPanel from "./ChatPanel";
import InsightsPage from "./InsightsPage";
import EvalsPage from "./EvalsPage";

export default function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setAuthLoading(false);
    });
    return unsub;
  }, []);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper-200">
        <p className="text-ink-500 font-serif italic">Opening your journal…</p>
      </div>
    );
  }
  if (!user) return <LoginScreen />;
  return <JournalScreen user={user} />;
}

function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-200 px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="font-serif text-5xl text-forest mb-2">Inkwell</h1>
          <p className="text-ink-500 italic font-serif">A place to think on the page.</p>
        </div>
        <form onSubmit={handleLogin} className="bg-paper-100 p-8 rounded-lg border border-paper-400 space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-paper-50 border border-paper-400 rounded px-3 py-2.5 text-ink-900 placeholder-ink-400 focus:outline-none focus:border-forest transition-colors"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-paper-50 border border-paper-400 rounded px-3 py-2.5 text-ink-900 placeholder-ink-400 focus:outline-none focus:border-forest transition-colors"
          />
          {error && <p className="text-sm text-forest">{error}</p>}
          <button className="w-full bg-forest text-paper-100 py-2.5 rounded font-medium hover:bg-forest-dark transition-colors">
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}

function JournalScreen({ user }) {
  const [tab, setTab] = useState("write");

  const [entries, setEntries] = useState([]);
  const [content, setContent] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);

  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);

  const editorRef = useRef(null);

  async function loadEntries() {
    const { data } = await api.get("/entries");
    setEntries(data);
  }
  useEffect(() => { loadEntries(); }, []);

  async function handleSave() {
    if (!content.trim()) return;
    setLoading(true);
    try {
      if (selectedId) await api.patch(`/entries/${selectedId}`, { content });
      else await api.post("/entries", { content });
      setContent("");
      setSelectedId(null);
      await loadEntries();
    } finally { setLoading(false); }
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const { data } = await api.get("/entries/search/semantic", { params: { q: searchQuery, limit: 10 } });
      setSearchResults(data);
    } finally { setSearching(false); }
  }

  function clearSearch() { setSearchQuery(""); setSearchResults(null); }

  async function handleSelect(entry) {
    setSelectedId(entry.id || entry.entry_id);
    if (entry.entry_id && !entry.content) {
      const { data } = await api.get(`/entries/${entry.entry_id}`);
      setContent(data.content);
    } else { setContent(entry.content); }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this entry?")) return;
    await api.delete(`/entries/${id}`);
    if (selectedId === id) { setContent(""); setSelectedId(null); }
    await loadEntries();
  }

  async function handleCitationClick(entryId) {
    const { data } = await api.get(`/entries/${entryId}`);
    setSelectedId(entryId);
    setContent(data.content);
    setChatOpen(false);
    setTab("write");
    setTimeout(() => editorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
  }

  const showingSearch = searchResults !== null;
  const listItems = showingSearch ? searchResults : entries;

  // Tab button — green bar under the active tab (mockup detail)
  const TabButton = ({ id, label }) => (
    <button
      onClick={() => setTab(id)}
      className={`relative px-1 pb-3.5 text-sm transition-colors ${
        tab === id ? "text-forest font-medium" : "text-ink-400 hover:text-ink-700"
      }`}
    >
      {label}
      {tab === id && (
        <span className="absolute -bottom-px -left-1 -right-1 h-[3px] bg-sage-600 rounded-t-sm" />
      )}
    </button>
  );

  return (
    <div className="min-h-screen bg-paper-200 text-ink-900">
      {/* Header — toasted parchment background, forest-green brand + tabs */}
      <header className="border-b border-paper-400 bg-paper-300 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-3.5 flex justify-between items-center">
          <div className="flex items-center gap-8">
            <span className="font-serif text-xl text-forest font-medium">Inkwell</span>
            <nav className="flex gap-6">
              <TabButton id="write" label="Write" />
              <TabButton id="insights" label="Insights" />
              <TabButton id="chat" label="Chat" />
              <TabButton id="evals" label="Evals" />
            </nav>
          </div>
          <div className="flex items-center gap-4 text-sm">
            {/* ✦ Ask button — green outline (mockup detail) */}
            <button
              onClick={() => setChatOpen(true)}
              className="px-3 py-1.5 rounded-full bg-paper-100 border border-forest text-forest hover:bg-sage-100 transition-colors text-xs font-medium"
            >
              ✦ Ask
            </button>
            <span className="text-ink-500 hidden sm:inline text-xs">{user.email}</span>
            <button onClick={() => signOut(auth)} className="text-ink-500 hover:text-forest transition-colors text-xs">
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* WRITE tab */}
      {tab === "write" && (
        <div className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-8">
          {/* Sidebar */}
          <aside className="space-y-3">
            <form onSubmit={handleSearch} className="relative">
              <input
                type="text"
                placeholder="Search by meaning…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-paper-100 border border-paper-400 rounded-full pl-4 pr-10 py-2 text-sm text-ink-900 placeholder-ink-400 focus:outline-none focus:border-forest transition-colors"
              />
              <button
                type="submit"
                disabled={searching}
                className="absolute right-1 top-1 w-7 h-7 rounded-full bg-forest text-paper-100 text-xs hover:bg-forest-dark transition-colors flex items-center justify-center font-medium"
              >
                {searching ? "…" : "→"}
              </button>
            </form>

            {showingSearch && (
              <div className="flex justify-between items-center text-xs text-ink-500 px-2">
                <span className="italic">{searchResults.length} found</span>
                <button onClick={clearSearch} className="hover:text-forest transition-colors">Clear</button>
              </div>
            )}

            {!showingSearch && (
              <button
                onClick={() => { setSelectedId(null); setContent(""); }}
                className="w-full bg-forest text-paper-100 py-2.5 rounded text-sm hover:bg-forest-dark transition-colors font-medium"
              >
                + New entry
              </button>
            )}

            {/* Entries — selected row gets sage-100 background + 3px forest bar on left (mockup detail) */}
            <div className="space-y-1">
              {listItems.map((item) => {
                const id = item.id || item.entry_id;
                const preview = item.content || item.preview;
                const isSelected = selectedId === id;
                return (
                  <div
                    key={id}
                    onClick={() => handleSelect(item)}
                    className={`group relative p-3 pl-4 cursor-pointer transition-all rounded ${
                      isSelected
                        ? "bg-sage-100 border-l-[3px] border-l-forest rounded-l-none"
                        : "border-l-[3px] border-l-transparent hover:bg-paper-100"
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <p className={`text-xs font-medium ${isSelected ? "text-ink-500" : "text-ink-400"}`}>
                        {new Date(item.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                      </p>
                      {showingSearch && (
                        <span className="text-xs text-forest font-medium">
                          {(item.score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <p className={`text-sm line-clamp-2 font-serif leading-snug ${isSelected ? "text-forest" : "text-ink-700"}`}>
                      {preview}
                    </p>
                    {!showingSearch && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(id); }}
                        className="text-xs text-ink-400 group-hover:text-forest transition-colors mt-1.5"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                );
              })}
              {listItems.length === 0 && (
                <p className="text-sm text-ink-500 text-center py-12 italic font-serif">
                  {showingSearch ? "No matches found." : "Your first entry awaits."}
                </p>
              )}
            </div>
          </aside>

          {/* Editor canvas — cream inner surface, forest title, parchment outer */}
          <main ref={editorRef} className="scroll-mt-4">
            <div className="bg-paper-100 rounded-lg border border-paper-400 p-8">
              <div className="flex items-baseline justify-between mb-5">
                <h2 className="font-serif text-2xl text-forest">
                  {selectedId ? "Editing" : "New entry"}
                </h2>
                <p className="text-xs text-ink-500 italic">
                  {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
                </p>
              </div>
              <div data-color-mode="light">
                <MDEditor value={content} onChange={setContent} height={460} preview="edit" />
              </div>
              <div className="mt-5 flex gap-2 items-center">
                <button
                  onClick={handleSave}
                  disabled={loading || !content.trim()}
                  className="bg-forest text-paper-100 px-5 py-2 rounded hover:bg-forest-dark transition-colors disabled:opacity-40 text-sm font-medium"
                >
                  {loading ? "Saving…" : selectedId ? "Update" : "Save"}
                </button>
                {selectedId && (
                  <button
                    onClick={() => { setSelectedId(null); setContent(""); }}
                    className="px-5 py-2 rounded border border-paper-400 text-ink-500 hover:bg-paper-200 transition-colors text-sm"
                  >
                    Cancel
                  </button>
                )}
                {content.trim() && (
                  <span className="text-xs text-ink-400 italic ml-2">
                    draft · {content.trim().split(/\s+/).length} words
                  </span>
                )}
              </div>
            </div>
          </main>
        </div>
      )}

      {/* INSIGHTS tab */}
      {tab === "insights" && <InsightsPage />}

      {/* EVALS tab */}
      {tab === "evals" && <EvalsPage />}

      {/* CHAT tab */}
      {tab === "chat" && (
        <div className="max-w-3xl mx-auto px-6 py-8">
          <div className="mb-4">
            <h2 className="font-serif text-2xl text-forest">Ask the journal</h2>
            <p className="text-sm text-ink-500 italic font-serif">Answers are grounded in your own past entries.</p>
          </div>
          <div className="bg-paper-100 border border-paper-400 rounded-lg h-[600px]">
            <ChatPanel
              messages={chatMessages}
              setMessages={setChatMessages}
              onCitationClick={handleCitationClick}
            />
          </div>
        </div>
      )}

      {/* Chat drawer */}
      {chatOpen && (
        <div className="fixed inset-0 z-20 flex justify-end" onClick={() => setChatOpen(false)}>
          <div className="absolute inset-0 bg-forest/20 backdrop-blur-sm" />
          <div
            className="relative w-full max-w-md bg-paper-200 border-l border-paper-400 shadow-2xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center px-5 py-4 border-b border-paper-400 bg-paper-300">
              <div>
                <h3 className="font-serif text-xl text-forest">Ask the journal</h3>
                <p className="text-xs text-ink-500 italic">Quick consultation</p>
              </div>
              <button
                onClick={() => setChatOpen(false)}
                className="w-8 h-8 rounded-full text-ink-500 hover:bg-paper-100 transition-colors flex items-center justify-center"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <ChatPanel
                messages={chatMessages}
                setMessages={setChatMessages}
                onCitationClick={handleCitationClick}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}