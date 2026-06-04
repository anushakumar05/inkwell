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
      } finally { setLoading(false); }
    }
    load();
  }, [limit]);

  if (loading) return <p className="text-xs text-ink-500 italic font-serif">Listening for patterns…</p>;
  if (themes.length === 0) return null;

  const maxCount = themes[0].count;

  return (
    <div>
      <h3 className="font-serif text-base text-ink-900 mb-2">Recurring themes</h3>
      <div className="flex flex-wrap gap-1.5">
        {themes.map(({ theme, count }) => {
          const intensity = count / maxCount;
          const cls =
            intensity > 0.66
              ? "bg-ink-900 text-cream-50"
              : intensity > 0.33
              ? "bg-cream-200 text-ink-900"
              : "bg-cream-100 text-ink-700";
          return (
            <span
              key={theme}
              className={`${cls} text-xs px-2.5 py-1 rounded-full font-medium`}
              title={`${count} ${count === 1 ? "entry" : "entries"}`}
            >
              {theme}
              <span className="ml-1.5 opacity-60 font-normal">{count}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}