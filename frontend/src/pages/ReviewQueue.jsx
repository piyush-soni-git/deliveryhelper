import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, XCircle, AlertTriangle, ShieldCheck, RefreshCw, 
  ArrowRight, GitCompare, Building, MapPin, Hash, Sparkles 
} from 'lucide-react';

export default function ReviewQueue() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState({});
  const [feedbackMessage, setFeedbackMessage] = useState(null);

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/review/list');
      if (!res.ok) throw new Error("Failed to fetch review queue");
      const data = await res.json();
      setItems(data.items || []);
    } catch (err) {
      setError(err.message || "Network error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleDecision = async (id1, id2, decision) => {
    const key = `${id1}_${id2}`;
    setActionLoading(prev => ({ ...prev, [key]: true }));
    try {
      const res = await fetch('/api/review/decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id1, id2, decision })
      });
      if (!res.ok) throw new Error("Decision submission failed");
      const data = await res.json();

      // Update state locally
      setItems(prev => prev.map(item => {
        if ((item.id1 === id1 && item.id2 === id2) || (item.id1 === id2 && item.id2 === id1)) {
          return { ...item, decision };
        }
        return item;
      }));

      setFeedbackMessage({
        type: decision === 'APPROVE' ? 'success' : 'info',
        text: decision === 'APPROVE' 
          ? `Approved! Merged records ${id1} and ${id2} into a single delivery point group.` 
          : `Rejected! Confirmed separate delivery points for ${id1} and ${id2}.`
      });

      setTimeout(() => setFeedbackMessage(null), 4000);
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const pendingItems = items.filter(i => !i.decision);
  const resolvedItems = items.filter(i => !!i.decision);

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 mb-2">
            <AlertTriangle className="w-3.5 h-3.5" />
            Human-in-the-Loop Verification
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Uncertain Review Queue
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Pairs routed here due to missing critical delivery fields, moderate similarity (70–90%), or transitive chain conflicts. Your feedback updates the clustering graph immediately.
          </p>
        </div>

        <button
          onClick={fetchQueue}
          disabled={loading}
          className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-emerald-500 transition shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Queue ({pendingItems.length})
        </button>
      </div>

      {feedbackMessage && (
        <div className={`p-4 rounded-xl text-sm font-medium border flex items-center gap-2 transition animate-in fade-in ${
          feedbackMessage.type === 'success' 
            ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200' 
            : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200'
        }`}>
          <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
          {feedbackMessage.text}
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 rounded-xl text-sm flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          {error}
        </div>
      )}

      {/* Main Review Items */}
      {loading && items.length === 0 ? (
        <div className="py-20 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
          <p className="text-sm">Loading review items...</p>
        </div>
      ) : pendingItems.length === 0 && resolvedItems.length === 0 ? (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-12 text-center shadow-sm space-y-3">
          <div className="w-12 h-12 rounded-full bg-emerald-50 dark:bg-emerald-950 flex items-center justify-center mx-auto text-emerald-600 dark:text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white">Review Queue is Clear!</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            All processed address candidate pairs have been automatically categorized into AUTO_MERGE or SEPARATE. Run a batch with synthetic data or lower thresholds to generate candidate reviews.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {pendingItems.map((item) => {
            const pairKey = `${item.id1}_${item.id2}`;
            const isActing = actionLoading[pairKey];

            return (
              <div 
                key={pairKey}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-5 transition"
              >
                {/* Header with Reason and Score */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-2.5">
                    <span className="p-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400">
                      <AlertTriangle className="w-4 h-4" />
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm text-slate-900 dark:text-white">
                          {item.id1}
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-mono font-bold text-sm text-slate-900 dark:text-white">
                          {item.id2}
                        </span>
                      </div>
                      <span className="text-xs font-semibold text-amber-600 dark:text-amber-400 mt-0.5 block">
                        Reason: {item.reason}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Similarity</span>
                      <div className="font-mono font-black text-lg text-slate-900 dark:text-white">
                        {(item.score * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>

                {/* Side by Side Comparison Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Record 1 */}
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 space-y-3">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-mono font-bold text-slate-500">{item.id1}</span>
                      <span className="text-[10px] uppercase font-bold text-slate-400">Record 1</span>
                    </div>
                    <div className="text-xs font-medium text-slate-900 dark:text-white leading-relaxed">
                      {item.address1}
                    </div>
                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200/50 dark:border-slate-800/60 text-[11px]">
                      <div>
                        <span className="text-slate-400 block text-[10px] font-bold">FLAT</span>
                        <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                          {item.components1?.flat_no?.value || <span className="italic text-slate-400">None</span>}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px] font-bold">BUILDING</span>
                        <span className="font-semibold text-slate-700 dark:text-slate-300 truncate block">
                          {item.components1?.building?.value || <span className="italic text-slate-400">None</span>}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px] font-bold">ROAD</span>
                        <span className="font-semibold text-slate-700 dark:text-slate-300 truncate block">
                          {item.components1?.road?.value || <span className="italic text-slate-400">None</span>}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px] font-bold">PIN</span>
                        <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                          {item.components1?.pin?.value || <span className="italic text-slate-400">None</span>}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Record 2 */}
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 space-y-3">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-mono font-bold text-slate-500">{item.id2}</span>
                      <span className="text-[10px] uppercase font-bold text-slate-400">Record 2</span>
                    </div>
                    <div className="text-xs font-medium text-slate-900 dark:text-white leading-relaxed">
                      {item.address2}
                    </div>
                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200/50 dark:border-slate-800/60 text-[11px]">
                      <div>
                        <span className="text-slate-400 block text-[10px] font-bold">FLAT</span>
                        <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                          {item.components2?.flat_no?.value || <span className="italic text-slate-400">None</span>}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px] font-bold">BUILDING</span>
                        <span className="font-semibold text-slate-700 dark:text-slate-300 truncate block">
                          {item.components2?.building?.value || <span className="italic text-slate-400">None</span>}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px] font-bold">ROAD</span>
                        <span className="font-semibold text-slate-700 dark:text-slate-300 truncate block">
                          {item.components2?.road?.value || <span className="italic text-slate-400">None</span>}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px] font-bold">PIN</span>
                        <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                          {item.components2?.pin?.value || <span className="italic text-slate-400">None</span>}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Conflict Tags */}
                {item.conflict_flags?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {item.conflict_flags.map((flag, i) => (
                      <span key={i} className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300">
                        {flag}
                      </span>
                    ))}
                  </div>
                )}

                {/* Decision Actions */}
                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    onClick={() => handleDecision(item.id1, item.id2, 'REJECT')}
                    disabled={isActing}
                    className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900 transition disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4" />
                    Reject (Keep Separate)
                  </button>
                  <button
                    onClick={() => handleDecision(item.id1, item.id2, 'APPROVE')}
                    disabled={isActing}
                    className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Approve (Merge Delivery Point)
                  </button>
                </div>
              </div>
            );
          })}

          {/* Already Resolved Section */}
          {resolvedItems.length > 0 && (
            <div className="pt-6 border-t border-slate-200 dark:border-slate-800 space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Resolved Decisions ({resolvedItems.length})
              </h3>
              <div className="space-y-2">
                {resolvedItems.map((r, idx) => (
                  <div key={idx} className="p-3 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold">{r.id1} & {r.id2}</span>
                      <span className="text-slate-400 truncate max-w-xs">{r.address1}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                      r.decision === 'APPROVE' 
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' 
                        : 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300'
                    }`}>
                      {r.decision}D
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
