import { useState, useEffect } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import api from "./lib/api";

export default function MoodChart() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const { data } = await api.get("/entries/trends/mood", { params: { days: 60 } });
        const formatted = data.map((p) => ({
          date: new Date(p.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
          valence: p.valence,
          energy: p.energy,
          emotion: p.dominant_emotion,
        }));
        setData(formatted);
      } finally { setLoading(false); }
    }
    load();
  }, []);

  if (loading) return <p className="text-xs text-ink-500 italic font-serif">Reading the lines…</p>;
  if (data.length === 0) {
    return <p className="text-xs text-ink-500 italic font-serif">Write a few entries to see your mood arc.</p>;
  }

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <h3 className="font-serif text-base text-ink-900">Mood over time</h3>
        <div className="flex gap-3 text-[10px] text-ink-500">
          <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-accent inline-block" />Valence</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-ink-500 inline-block border-t border-dashed border-ink-500" />Energy</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: -25, bottom: 0 }}>
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#857d74" }} stroke="#e8dab8" />
          <YAxis domain={[-1, 1]} tick={{ fontSize: 10, fill: "#857d74" }} stroke="#e8dab8" />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, background: "#fdfbf6", border: "1px solid #e8dab8" }}
            formatter={(value) => value.toFixed(2)}
            labelFormatter={(label, payload) =>
              payload && payload[0] ? `${label} — ${payload[0].payload.emotion}` : label
            }
          />
          <ReferenceLine y={0} stroke="#e8dab8" />
          <Line type="monotone" dataKey="valence" stroke="#9e3b1a" strokeWidth={2} dot={{ r: 2.5, fill: "#9e3b1a" }} />
          <Line type="monotone" dataKey="energy" stroke="#857d74" strokeWidth={1.5} strokeDasharray="4 3" dot={{ r: 2, fill: "#857d74" }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}