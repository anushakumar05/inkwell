import { useState, useEffect } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import api from "./lib/api";

export default function EvalsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/entries/trends/evals")
      .then(({ data }) => setData(data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Layout><p className="text-sm text-ink-500 italic font-serif">Reading the scores…</p></Layout>;
  if (!data || data.total_evals === 0) {
    return (
      <Layout>
        <p className="text-sm text-ink-500 italic font-serif">
          No evaluations yet. Ask the chat a question, or run the offline suite to populate this page.
        </p>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5 mb-6">
        <Card label="Total evals" value={data.total_evals} />
        <Card label="Live evals" value={data.live_count} subtle="from real chat" />
        <Card label="Test set runs" value={data.test_set_count} subtle="from offline suite" />
        <Card
          label="Avg faithfulness"
          value={data.avg_faithfulness.toFixed(2)}
          subtle={data.avg_faithfulness >= 0.85 ? "strong" : data.avg_faithfulness >= 0.7 ? "decent" : "needs work"}
          emphasis
        />
      </div>

      <div className="bg-paper-100 border border-paper-400 rounded-lg p-6 mb-6">
        <ScoreTrendChart recent={data.recent} />
      </div>

      <div className="bg-paper-100 border border-paper-400 rounded-lg p-6">
        <h3 className="font-serif text-xl text-forest mb-3">Recent evaluations</h3>
        <p className="text-xs text-ink-500 italic font-serif mb-4">
          Every chat response gets scored in the background. Test-set runs are tagged.
        </p>
        <div className="space-y-3">
          {data.recent.slice().reverse().map((r, i) => (
            <EvalRow key={i} r={r} />
          ))}
        </div>
      </div>
    </Layout>
  );
}

function Layout({ children }) {
  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h2 className="font-serif text-3xl text-forest">Evaluation</h2>
        <p className="text-sm text-ink-500 italic font-serif mt-1">
          Every chat response is scored by an LLM judge for faithfulness, answer relevance, and context relevance.
        </p>
      </div>
      {children}
    </div>
  );
}

function Card({ label, value, subtle, emphasis }) {
  return (
    <div className={`bg-paper-100 border rounded-lg p-5 ${emphasis ? "border-forest" : "border-paper-400"}`}>
      <p className="text-xs text-ink-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-medium ${emphasis ? "text-forest" : "text-ink-900"}`}>{value}</p>
      {subtle && <p className="text-xs text-ink-400 italic mt-0.5">{subtle}</p>}
    </div>
  );
}

function ScoreTrendChart({ recent }) {
  const data = recent.map((r, i) => ({
    n: i + 1,
    faithfulness: r.faithfulness,
    answer_relevance: r.answer_relevance,
    context_relevance: r.context_relevance,
  }));

  return (
    <div>
      <h3 className="font-serif text-xl text-forest mb-1">Score trend</h3>
      <p className="text-xs text-ink-500 italic font-serif mb-4">
        Last {data.length} evaluations · hover to see exact scores
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: -15, bottom: 0 }}>
          <XAxis dataKey="n" tick={{ fontSize: 11, fill: "#5a6b4a" }} stroke="#d8c9a3" />
          <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: "#5a6b4a" }} stroke="#d8c9a3" />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, background: "#fdfaf0", border: "1px solid #d8c9a3", color: "#2d4a2f" }}
            formatter={(value) => value.toFixed(2)}
          />
          <ReferenceLine y={0.8} stroke="#8aa56e" strokeDasharray="3 3" label={{ value: "0.80", fill: "#5a6b4a", fontSize: 10, position: "right" }} />
          <Line type="monotone" dataKey="faithfulness" stroke="#2d4a2f" strokeWidth={2.5} dot={{ r: 3, fill: "#2d4a2f" }} name="Faithfulness" />
          <Line type="monotone" dataKey="answer_relevance" stroke="#8aa56e" strokeWidth={2} dot={{ r: 2.5, fill: "#8aa56e" }} name="Answer rel." />
          <Line type="monotone" dataKey="context_relevance" stroke="#c8d4a8" strokeWidth={1.5} strokeDasharray="4 3" dot={{ r: 2, fill: "#c8d4a8" }} name="Context rel." />
        </LineChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-2 text-[11px] text-ink-500">
        <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-forest inline-block" />Faithfulness</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-sage-400 inline-block" />Answer relevance</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-sage-200 inline-block" />Context relevance</span>
      </div>
    </div>
  );
}

function EvalRow({ r }) {
  const scoreColor = (s) =>
    s >= 0.8 ? "text-forest" :
    s >= 0.5 ? "text-ink-500" :
    "text-ink-900";

  return (
    <div className="border border-paper-400 rounded p-3 bg-paper-50">
      <div className="flex items-start justify-between gap-3 mb-1">
        <p className="text-sm text-ink-900 font-serif flex-1">{r.question}</p>
        {r.is_test_set && (
          <span className="text-[10px] uppercase tracking-wider text-forest bg-sage-100 px-2 py-0.5 rounded-full font-medium shrink-0">
            test set
          </span>
        )}
      </div>
      <div className="flex gap-4 mt-2 text-xs">
        <span><span className="text-ink-500">F:</span> <span className={scoreColor(r.faithfulness)}>{r.faithfulness.toFixed(2)}</span></span>
        <span><span className="text-ink-500">A:</span> <span className={scoreColor(r.answer_relevance)}>{r.answer_relevance.toFixed(2)}</span></span>
        <span><span className="text-ink-500">C:</span> <span className={scoreColor(r.context_relevance)}>{r.context_relevance.toFixed(2)}</span></span>
        <span className="text-ink-400 ml-auto">{new Date(r.created_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</span>
      </div>
      {r.notes && <p className="text-xs text-ink-500 italic mt-2 leading-relaxed">{r.notes}</p>}
    </div>
  );
}