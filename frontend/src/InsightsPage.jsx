import { useState, useEffect } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import api from "./lib/api";

export default function InsightsPage() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h2 className="font-serif text-3xl text-forest">Insights</h2>
        <p className="text-sm text-ink-500 italic font-serif mt-1">Patterns surfaced from your writing.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 bg-paper-100 border border-paper-400 rounded-lg p-6">
          <BigMoodChart />
        </div>
        <div className="bg-paper-100 border border-paper-400 rounded-lg p-6">
          <QuickStats />
        </div>
        <div className="lg:col-span-3 bg-paper-100 border border-paper-400 rounded-lg p-6">
          <BigThemes />
        </div>
        <div className="lg:col-span-3 bg-paper-100 border border-paper-400 rounded-lg p-6">
          <FrequencyHeatmap />
        </div>
      </div>
    </div>
  );
}

function BigMoodChart() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/entries/trends/mood", { params: { days: 90 } })
      .then(({ data }) => {
        setData(data.map((p) => ({
          date: new Date(p.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
          valence: p.valence,
          energy: p.energy,
          emotion: p.dominant_emotion,
        })));
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-ink-500 italic font-serif">Reading the lines…</p>;
  if (data.length === 0) return <p className="text-sm text-ink-500 italic font-serif">Write a few entries to see the arc.</p>;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="font-serif text-xl text-forest">Mood over time</h3>
        <div className="flex gap-3 text-[11px] text-ink-500">
          <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-forest inline-block" />Valence</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-sage-400 inline-block" />Energy</span>
        </div>
      </div>
      <p className="text-xs text-ink-500 italic font-serif mb-4">90 days · hover for the dominant emotion of that entry</p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: -15, bottom: 0 }}>
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#5a6b4a" }} stroke="#d8c9a3" />
          <YAxis domain={[-1, 1]} tick={{ fontSize: 11, fill: "#5a6b4a" }} stroke="#d8c9a3" />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, background: "#fdfaf0", border: "1px solid #d8c9a3", color: "#2d4a2f" }}
            labelStyle={{ color: "#2d4a2f" }}
            formatter={(value) => value.toFixed(2)}
            labelFormatter={(label, payload) =>
              payload && payload[0] ? `${label} — ${payload[0].payload.emotion}` : label
            }
          />
          <ReferenceLine y={0} stroke="#d8c9a3" />
          <Line type="monotone" dataKey="valence" stroke="#2d4a2f" strokeWidth={2.5} dot={{ r: 3, fill: "#2d4a2f" }} />
          <Line type="monotone" dataKey="energy" stroke="#8aa56e" strokeWidth={2} strokeDasharray="4 3" dot={{ r: 2.5, fill: "#8aa56e" }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function QuickStats() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get("/entries"),
      api.get("/entries/trends/mood", { params: { days: 30 } }),
      api.get("/entries/trends/themes"),
    ]).then(([entriesRes, moodRes, themesRes]) => {
      const entries = entriesRes.data;
      const moods = moodRes.data;
      const themes = themesRes.data;
      const avgValence = moods.length
        ? moods.reduce((s, p) => s + p.valence, 0) / moods.length
        : 0;
      setStats({
        totalEntries: entries.length,
        last30: moods.length,
        avgValence,
        topTheme: themes[0]?.theme || "—",
      });
    });
  }, []);

  if (!stats) return <p className="text-sm text-ink-500 italic font-serif">…</p>;

  return (
    <div>
      <h3 className="font-serif text-xl text-forest mb-1">At a glance</h3>
      <p className="text-xs text-ink-500 italic font-serif mb-4">A quick summary</p>
      <div className="space-y-5">
        <Stat label="Total entries" value={stats.totalEntries} />
        <Stat label="Last 30 days" value={stats.last30} />
        <Stat
          label="Avg mood (30d)"
          value={(stats.avgValence >= 0 ? "+" : "") + stats.avgValence.toFixed(2)}
          subtle={stats.avgValence >= 0 ? "leaning positive" : "leaning low"}
        />
        <Stat label="Top theme" value={stats.topTheme} serif />
      </div>
    </div>
  );
}

function Stat({ label, value, subtle, serif }) {
  return (
    <div>
      <p className="text-xs text-ink-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`${serif ? "font-serif" : ""} text-2xl text-forest font-medium`}>{value}</p>
      {subtle && <p className="text-xs text-ink-400 italic mt-0.5">{subtle}</p>}
    </div>
  );
}

function BigThemes() {
  const [themes, setThemes] = useState([]);

  useEffect(() => {
    api.get("/entries/trends/themes").then(({ data }) => setThemes(data));
  }, []);

  if (themes.length === 0) {
    return <p className="text-sm text-ink-500 italic font-serif">No themes yet — write more entries.</p>;
  }

  const max = themes[0].count;

  return (
    <div>
      <h3 className="font-serif text-xl text-forest mb-1">What you write about</h3>
      <p className="text-xs text-ink-500 italic font-serif mb-4">Most frequent themes appear larger and brighter</p>
      <div className="flex flex-wrap gap-2">
        {themes.map(({ theme, count }) => {
          const intensity = count / max;
          const cls =
            intensity > 0.66
              ? "bg-forest text-paper-100 text-base px-4 py-1.5"
              : intensity > 0.33
              ? "bg-sage-400 text-forest text-sm px-3 py-1"
              : "bg-sage-100 text-forest text-xs px-2.5 py-1";
          return (
            <span key={theme} className={`${cls} rounded-full font-medium`}>
              {theme}
              <span className="ml-2 opacity-70 font-normal">{count}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

function FrequencyHeatmap() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/entries/trends/frequency", { params: { days: 90 } })
      .then(({ data }) => setData(data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-ink-500 italic font-serif">Counting the days…</p>;

  const counts = Object.fromEntries(data.map((d) => [d.date, d.count]));

  const today = new Date();
  const days = [];
  for (let i = 89; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    days.push({ date: d, key, count: counts[key] || 0 });
  }

  const weeks = [];
  let week = new Array(days[0].date.getDay()).fill(null);
  for (const day of days) {
    week.push(day);
    if (week.length === 7) { weeks.push(week); week = []; }
  }
  if (week.length) {
    while (week.length < 7) week.push(null);
    weeks.push(week);
  }

  const dayLabels = ["S", "M", "T", "W", "T", "F", "S"];

  // 5-tier scale walking from cream → deep forest. None blend into paper-200 background.
  function colorFor(count) {
    if (count === 0) return "bg-sage-50";   // #e6dfc4 — empty (cream, distinct from paper bg)
    if (count === 1) return "bg-sage-200";  // #c8d4a8 — pale sage
    if (count === 2) return "bg-sage-400";  // #8aa56e — sage
    if (count === 3) return "bg-sage-600";  // #5a7a4a — forest
    return "bg-forest";                      // #2d4a2f — deep forest
  }

  return (
    <div>
      <h3 className="font-serif text-xl text-forest mb-1">When you write</h3>
      <p className="text-xs text-ink-500 italic font-serif mb-4">90 days · each square is a day, darker green means more entries</p>

      <div className="flex gap-2">
        <div className="flex flex-col gap-1.5 pt-0.5">
          {dayLabels.map((d, i) => (
            <div key={i} className="text-xs text-ink-500 h-5 flex items-center w-4 font-medium">{d}</div>
          ))}
        </div>

        <div className="flex gap-1.5 overflow-x-auto">
          {weeks.map((w, wi) => (
            <div key={wi} className="flex flex-col gap-1.5">
              {w.map((day, di) => (
                <div
                  key={di}
                  className={`w-5 h-5 rounded-sm ${day ? colorFor(day.count) : "bg-transparent"} transition-all hover:ring-2 hover:ring-forest`}
                  title={day ? `${day.key} — ${day.count} ${day.count === 1 ? "entry" : "entries"}` : ""}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 mt-4 text-xs text-ink-500">
        <span>less</span>
        <span className="w-4 h-4 bg-sage-50 rounded-sm" />
        <span className="w-4 h-4 bg-sage-200 rounded-sm" />
        <span className="w-4 h-4 bg-sage-400 rounded-sm" />
        <span className="w-4 h-4 bg-sage-600 rounded-sm" />
        <span className="w-4 h-4 bg-forest rounded-sm" />
        <span>more</span>
      </div>
    </div>
  );
}