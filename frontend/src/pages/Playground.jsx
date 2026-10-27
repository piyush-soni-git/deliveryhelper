import React, { useState } from 'react';
import { 
  GitCompare, ArrowRight, CheckCircle2, AlertTriangle, XCircle, 
  HelpCircle, Sparkles, Building, MapPin, Hash, Compass, Info, ShieldAlert
} from 'lucide-react';

const PRESETS = [
  {
    name: "Canonical: A101 vs A102 (Same Flat)",
    desc: "Flat 402 in Lotus Apts with abbreviation variation",
    addr1: "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017",
    addr2: "402, Lotus Apts, JLN Marg, Jaipur - 302017"
  },
  {
    name: "Hard Negative: A101 vs A103 (Different Flats)",
    desc: "Flat 402 vs Flat 403 in the same apartment tower (Must Separate!)",
    addr1: "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017",
    addr2: "Flat 403, Lotus Apartments, JLN Road, Jaipur 302017"
  },
  {
    name: "Cross-Script: English vs Hindi Devanagari",
    desc: "English text vs Devanagari script transliteration",
    addr1: "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017",
    addr2: "फ्लैट नं 402, कमल अपार्टमेंट, जेएलएन मार्ग, जयपुर ३०२०१७"
  },
  {
    name: "Uncertain: Missing Flat Number",
    desc: "A101 vs general building address (Routes to Review Queue)",
    addr1: "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017",
    addr2: "Lotus Apartments, JLN Road, Jaipur 302017"
  },
  {
    name: "Soft Conflict: PIN Typo (302017 vs 302018)",
    desc: "Same flat & road, but minor postal code discrepancy",
    addr1: "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017",
    addr2: "Flat 402, Lotus Apartments, JLN Road, Jaipur 302018"
  }
];

export default function Playground() {
  const [addr1, setAddr1] = useState(PRESETS[0].addr1);
  const [addr2, setAddr2] = useState(PRESETS[0].addr2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleCompare = async (a1 = addr1, a2 = addr2) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/playground/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address1: a1, address2: a2 })
      });
      if (!res.ok) throw new Error("Failed to evaluate addresses");
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message || "Network error occurred");
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = (preset) => {
    setAddr1(preset.addr1);
    setAddr2(preset.addr2);
    handleCompare(preset.addr1, preset.addr2);
  };

  const getTierBadge = (tier) => {
    switch (tier) {
      case "AUTO_MERGE":
        return {
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-500" />,
          bg: "bg-emerald-50 dark:bg-emerald-950/50 border-emerald-200 dark:border-emerald-800",
          text: "text-emerald-700 dark:text-emerald-300",
          label: "AUTO MERGE (Confirmed Same Delivery Point)"
        };
      case "REVIEW":
        return {
          icon: <AlertTriangle className="w-5 h-5 text-amber-500" />,
          bg: "bg-amber-50 dark:bg-amber-950/50 border-amber-200 dark:border-amber-800",
          text: "text-amber-700 dark:text-amber-300",
          label: "HUMAN REVIEW REQUIRED (Uncertain Delivery Point)"
        };
      case "SEPARATE":
      default:
        return {
          icon: <XCircle className="w-5 h-5 text-rose-500" />,
          bg: "bg-rose-50 dark:bg-rose-950/50 border-rose-200 dark:border-rose-800",
          text: "text-rose-700 dark:text-rose-300",
          label: "SEPARATE (Never Merge / Hard Conflict)"
        };
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 mb-2">
          <Sparkles className="w-3.5 h-3.5" />
          Live Interactive Matcher
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Address Comparison Playground
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Type or select two free-text Indian addresses to inspect normalization, extracted components, RapidFuzz scoring, conflict verification, and uncertainty tier verdict.
        </p>
      </div>

      {/* Preset Pills */}
      <div className="flex flex-wrap gap-2 pt-1">
        {PRESETS.map((p, idx) => (
          <button
            key={idx}
            onClick={() => applyPreset(p)}
            className="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-emerald-500 dark:hover:border-emerald-500 text-slate-700 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 transition shadow-sm text-left"
          >
            {p.name}
          </button>
        ))}
      </div>

      {/* Inputs Side by Side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Address 1 */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Record A</span>
            <span className="text-xs text-slate-400 font-mono">Reference Candidate</span>
          </div>
          <textarea
            rows={3}
            value={addr1}
            onChange={(e) => setAddr1(e.target.value)}
            placeholder="Enter first free-text Indian address..."
            className="w-full text-sm font-medium p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 resize-none"
          />
        </div>

        {/* Address 2 */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Record B</span>
            <span className="text-xs text-slate-400 font-mono">Target Candidate</span>
          </div>
          <textarea
            rows={3}
            value={addr2}
            onChange={(e) => setAddr2(e.target.value)}
            placeholder="Enter second free-text Indian address..."
            className="w-full text-sm font-medium p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 resize-none"
          />
        </div>
      </div>

      {/* Compare Button */}
      <div className="flex justify-center">
        <button
          onClick={() => handleCompare()}
          disabled={loading || !addr1.trim() || !addr2.trim()}
          className="flex items-center gap-2 px-8 py-3 rounded-xl font-bold text-white bg-emerald-600 hover:bg-emerald-500 active:scale-95 disabled:opacity-50 transition shadow-lg shadow-emerald-600/20"
        >
          <GitCompare className="w-5 h-5" />
          {loading ? "Evaluating Entities..." : "Compare Delivery Points"}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 rounded-xl text-sm flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          {error}
        </div>
      )}

      {/* Match Results */}
      {result && (
        <div className="space-y-6 pt-4 animate-in fade-in duration-300">
          {/* Prominent Verdict Card */}
          {(() => {
            const badge = getTierBadge(result.tier);
            return (
              <div className={`p-6 rounded-2xl border ${badge.bg} shadow-md`}>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white dark:bg-slate-900 rounded-xl shadow-sm">
                      {badge.icon}
                    </div>
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider opacity-75">Pipeline Verdict</span>
                      <h2 className={`text-xl font-extrabold ${badge.text}`}>
                        {badge.label}
                      </h2>
                    </div>
                  </div>
                  <div className="text-right flex items-center gap-4">
                    <div>
                      <div className="text-xs font-medium text-slate-500">Composite Score</div>
                      <div className="text-3xl font-black font-mono tracking-tight text-slate-900 dark:text-white">
                        {(result.match_result.score * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-200/60 dark:border-slate-800/60 text-sm font-medium text-slate-700 dark:text-slate-300">
                  <span className="font-bold text-slate-900 dark:text-white">Explanation: </span>
                  {result.match_result.explanation || result.tier_reason}
                </div>
              </div>
            );
          })()}

          {/* Conflict Flags Banner (if present) */}
          {result.match_result.conflict_flags.length > 0 && (
            <div className="p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 rounded-xl">
              <div className="flex items-center gap-2 font-bold text-amber-900 dark:text-amber-200 text-sm mb-2">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                Active Constraint & Conflict Flags:
              </div>
              <div className="flex flex-wrap gap-2">
                {result.match_result.conflict_flags.map((flag, i) => (
                  <span 
                    key={i}
                    className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold ${
                      flag.startsWith("HARD_CONFLICT") 
                        ? "bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-800" 
                        : "bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-800"
                    }`}
                  >
                    {flag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Component Extraction Side-by-Side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Record A Components */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
              <div className="flex justify-between items-center pb-2 border-b border-slate-100 dark:border-slate-800">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Record A Extracted Structure</h3>
                <span className="text-xs font-mono text-emerald-600 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded">Parsed</span>
              </div>
              <div className="text-xs text-slate-500 font-mono bg-slate-50 dark:bg-slate-950 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 break-all">
                <span className="font-bold text-slate-400">Normalized: </span>
                {result.address1.normalized}
              </div>
              <div className="space-y-2 text-xs">
                {Object.entries(result.address1.components).map(([k, v]) => {
                  if (k === "raw_normalized") return null;
                  return (
                    <div key={k} className="flex justify-between items-center py-1.5 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-950/50">
                      <span className="font-semibold text-slate-500 uppercase">{k.replace('_', ' ')}</span>
                      <div className="flex items-center gap-2">
                        <span className={`font-mono font-bold ${v.value ? 'text-slate-900 dark:text-white' : 'text-slate-400 italic'}`}>
                          {v.value || 'None'}
                        </span>
                        {v.value && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300">
                            {(v.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Record B Components */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
              <div className="flex justify-between items-center pb-2 border-b border-slate-100 dark:border-slate-800">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Record B Extracted Structure</h3>
                <span className="text-xs font-mono text-emerald-600 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded">Parsed</span>
              </div>
              <div className="text-xs text-slate-500 font-mono bg-slate-50 dark:bg-slate-950 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 break-all">
                <span className="font-bold text-slate-400">Normalized: </span>
                {result.address2.normalized}
              </div>
              <div className="space-y-2 text-xs">
                {Object.entries(result.address2.components).map(([k, v]) => {
                  if (k === "raw_normalized") return null;
                  return (
                    <div key={k} className="flex justify-between items-center py-1.5 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-950/50">
                      <span className="font-semibold text-slate-500 uppercase">{k.replace('_', ' ')}</span>
                      <div className="flex items-center gap-2">
                        <span className={`font-mono font-bold ${v.value ? 'text-slate-900 dark:text-white' : 'text-slate-400 italic'}`}>
                          {v.value || 'None'}
                        </span>
                        {v.value && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300">
                            {(v.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Component Similarity Breakdown Bars */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
              <Info className="w-4 h-4 text-emerald-500" />
              Per-Component Similarity Breakdown (RapidFuzz)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
              {Object.entries(result.match_result.breakdown).map(([component, simVal]) => {
                const pct = simVal !== null ? (simVal * 100) : null;
                return (
                  <div key={component} className="p-3.5 bg-slate-50 dark:bg-slate-950/70 rounded-xl border border-slate-100 dark:border-slate-800 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-bold text-slate-600 dark:text-slate-300 uppercase">{component}</span>
                      <span className="font-mono font-bold text-slate-900 dark:text-white">
                        {pct !== null ? `${pct.toFixed(0)}%` : 'N/A (Missing)'}
                      </span>
                    </div>
                    <div className="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          pct === null ? 'bg-slate-400' :
                          pct >= 85 ? 'bg-emerald-500' :
                          pct >= 60 ? 'bg-amber-500' : 'bg-rose-500'
                        }`}
                        style={{ width: `${pct !== null ? pct : 0}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
