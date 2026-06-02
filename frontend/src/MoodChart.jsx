import { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import api from "./lib/api";

export default function MoodChart() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const { data } = await api.get("/entries/trends/mood", { params: { days: 60 } });
        // Format dates for display and keep the raw scores.
        const formatted = data.map((p) => ({
          date: new Date(p.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
          valence: p.valence,
          energy: p.energy,
          emotion: p.dominant_emotion,
        }));
        setData(formatted);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <p className="text-sm text-slate-400">Loading mood trends...</p>;
  if (data.length === 0) {
    return <p className="text-sm text-slate-400">No mood data yet. Write a few entries!</p>;
  }

  return (
    <div className="bg-white p-4 rounded border">
      <h2 className="text-sm font-medium mb-3">Mood over time</h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis domain={[-1, 1]} tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
            formatter={(value, name) => [value.toFixed(2), name]}
            labelFormatter={(label, payload) =>
                payload && payload[0] ? `${label} — ${payload[0].payload.emotion}` : label
            }
          />
          {/* Zero line so positive/negative is visually obvious */}
          <ReferenceLine y={0} stroke="#cbd5e1" />
          <Line type="monotone" dataKey="valence" stroke="#0f766e" strokeWidth={2} dot={{ r: 3 }} name="Valence" />
          <Line type="monotone" dataKey="energy" stroke="#7c3aed" strokeWidth={2} dot={{ r: 3 }} strokeDasharray="4 2" name="Energy" />
        </LineChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-2 text-xs text-slate-500">
        <span><span className="inline-block w-3 h-0.5 bg-teal-700 align-middle mr-1"></span>Valence (positive/negative)</span>
        <span><span className="inline-block w-3 h-0.5 bg-violet-600 align-middle mr-1"></span>Energy (calm/activated)</span>
      </div>
    </div>
  );
}