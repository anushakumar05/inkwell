import { useState, useEffect } from "react";
import { signInWithEmailAndPassword, signOut, onAuthStateChanged } from "firebase/auth";
import MDEditor from "@uiw/react-md-editor";
import { auth } from "./lib/firebase";
import api from "./lib/api";

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

  if (authLoading) return <div className="p-8">Loading...</div>;
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
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form onSubmit={handleLogin} className="bg-white p-8 rounded-lg shadow w-96 space-y-4">
        <h1 className="text-2xl font-medium">Inkwell</h1>
        <p className="text-sm text-slate-500">Sign in to your journal.</p>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="w-full bg-slate-900 text-white py-2 rounded">Sign in</button>
      </form>
    </div>
  );
}

function JournalScreen({ user }) {
  const [entries, setEntries] = useState([]);
  const [content, setContent] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null); // null = not searching
  const [searching, setSearching] = useState(false);

  async function loadEntries() {
    const { data } = await api.get("/entries");
    setEntries(data);
  }

  useEffect(() => { loadEntries(); }, []);

  async function handleSave() {
    if (!content.trim()) return;
    setLoading(true);
    try {
      if (selectedId) {
        await api.patch(`/entries/${selectedId}`, { content });
      } else {
        await api.post("/entries", { content });
      }
      setContent("");
      setSelectedId(null);
      await loadEntries();
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const { data } = await api.get("/entries/search/semantic", {
        params: { q: searchQuery, limit: 10 },
      });
      setSearchResults(data);
    } finally {
      setSearching(false);
    }
  }

  function clearSearch() {
    setSearchQuery("");
    setSearchResults(null);
  }

  async function handleSelect(entry) {
    setSelectedId(entry.id || entry.entry_id);
    // search results only have a preview; fetch the full entry
    if (entry.entry_id && !entry.content) {
      const { data } = await api.get(`/entries/${entry.entry_id}`);
      setContent(data.content);
    } else {
      setContent(entry.content);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this entry?")) return;
    await api.delete(`/entries/${id}`);
    if (selectedId === id) { setContent(""); setSelectedId(null); }
    await loadEntries();
  }

  // Decide what to show in the left column: search results or all entries.
  const showingSearch = searchResults !== null;
  const listItems = showingSearch ? searchResults : entries;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b px-6 py-3 flex justify-between items-center">
        <h1 className="text-lg font-medium">Inkwell</h1>
        <div className="text-sm text-slate-500 flex items-center gap-4">
          <span>{user.email}</span>
          <button onClick={() => signOut(auth)} className="text-slate-700 hover:underline">
            Sign out
          </button>
        </div>
      </header>

      <div className="grid grid-cols-3 gap-6 p-6 max-w-7xl mx-auto">
        <aside className="col-span-1 space-y-2">
          {/* Search bar */}
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              placeholder="Search by meaning..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1 border rounded px-3 py-2 text-sm"
            />
            <button className="bg-slate-700 text-white px-3 rounded text-sm" disabled={searching}>
              {searching ? "..." : "Search"}
            </button>
          </form>

          {showingSearch && (
            <div className="flex justify-between items-center text-xs text-slate-500 px-1">
              <span>{searchResults.length} results for "{searchQuery}"</span>
              <button onClick={clearSearch} className="hover:underline">Clear</button>
            </div>
          )}

          {!showingSearch && (
            <button
              onClick={() => { setSelectedId(null); setContent(""); }}
              className="w-full bg-slate-900 text-white py-2 rounded text-sm"
            >
              + New entry
            </button>
          )}

          {listItems.map((item) => {
            const id = item.id || item.entry_id;
            const preview = item.content || item.preview;
            return (
              <div
                key={id}
                className={`bg-white p-3 rounded border cursor-pointer hover:border-slate-400 ${
                  selectedId === id ? "border-slate-900" : ""
                }`}
                onClick={() => handleSelect(item)}
              >
                <div className="flex justify-between items-center">
                  <p className="text-xs text-slate-500">
                    {new Date(item.created_at).toLocaleDateString()}
                  </p>
                  {showingSearch && (
                    <span className="text-xs text-slate-400">
                      {(item.score * 100).toFixed(0)}% match
                    </span>
                  )}
                </div>
                <p className="text-sm line-clamp-2 mt-1">{preview}</p>
                {!showingSearch && (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(id); }}
                    className="text-xs text-red-600 mt-1 hover:underline"
                  >
                    Delete
                  </button>
                )}
              </div>
            );
          })}

          {listItems.length === 0 && (
            <p className="text-sm text-slate-400 text-center py-8">
              {showingSearch ? "No matches found." : "No entries yet."}
            </p>
          )}
        </aside>

        <main className="col-span-2 bg-white p-6 rounded border">
          <div data-color-mode="light">
            <MDEditor value={content} onChange={setContent} height={400} preview="edit" />
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={handleSave}
              disabled={loading || !content.trim()}
              className="bg-slate-900 text-white px-4 py-2 rounded disabled:opacity-50"
            >
              {loading ? "Saving..." : selectedId ? "Update" : "Save"}
            </button>
            {selectedId && (
              <button
                onClick={() => { setSelectedId(null); setContent(""); }}
                className="px-4 py-2 rounded border"
              >
                Cancel
              </button>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}