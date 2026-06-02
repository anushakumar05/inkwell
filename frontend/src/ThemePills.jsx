import { useState, useEffect } from "react";
import api from "./lib/api";

export default function ThemePills({ limit = 8 }) {
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const { data } = await api.get("/entries/trends/themes");
        setThemes(data.slice(0, limit));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [limit]);

  if (loading) {
    return <p className="text-xs text-slate-400">Loading themes...</p>;
  }
  if (themes.length === 0) {
    return null; // nothing to show yet, stay quiet
  }

  // Pick the max count once so we can size pills proportionally.
  const maxCount = themes[0].count;

  return (
    <div className="bg-white p-4 rounded border">
      <h2 className="text-sm font-medium mb-3">Recurring themes</h2>
      <div className="flex flex-wrap gap-2">
        {themes.map(({ theme, count }) => {
          // Bigger count = darker, slightly larger pill. Subtle but communicates frequency.
          const intensity = count / maxCount; // 0 to 1
          const opacityClass =
            intensity > 0.66 ? "bg-slate-800 text-white"
            : intensity > 0.33 ? "bg-slate-200 text-slate-800"
            : "bg-slate-100 text-slate-600";
          return (
            <span
              key={theme}
              className={`${opacityClass} text-xs px-3 py-1 rounded-full`}
              title={`Appears in ${count} ${count === 1 ? "entry" : "entries"}`}
            >
              {theme}
              <span className="ml-1.5 opacity-70">{count}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}