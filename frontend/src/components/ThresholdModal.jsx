import React, { useState } from 'react';
import { Sliders, X, Check, RotateCcw } from 'lucide-react';

export default function ThresholdModal({ isOpen, onClose, thresholds, onSave }) {
  const [autoThresh, setAutoThresh] = useState(thresholds.threshold_auto || 0.90);
  const [reviewThresh, setReviewThresh] = useState(thresholds.threshold_review || 0.70);

  if (!isOpen) return null;

  const handleReset = () => {
    setAutoThresh(0.90);
    setReviewThresh(0.70);
  };

  const handleSave = () => {
    onSave({ threshold_auto: autoThresh, threshold_review: reviewThresh });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full shadow-2xl p-6 transition-all">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 rounded-lg">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white">Uncertainty Policy Thresholds</h3>
              <p className="text-xs text-slate-500">Tune decision boundaries for 3-tier clustering</p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="py-6 space-y-6">
          {/* AUTO_MERGE Slider */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                AUTO_MERGE Threshold
              </label>
              <span className="text-sm font-mono font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded">
                {(autoThresh * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min="0.75"
              max="1.0"
              step="0.01"
              value={autoThresh}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                setAutoThresh(val);
                if (val < reviewThresh) setReviewThresh(val);
              }}
              className="w-full accent-emerald-600 cursor-pointer h-2 bg-slate-200 dark:bg-slate-700 rounded-lg"
            />
            <p className="text-xs text-slate-500 mt-1">Pairs with score ≥ this without conflicts merge automatically.</p>
          </div>

          {/* REVIEW Slider */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                REVIEW Lower Bound
              </label>
              <span className="text-sm font-mono font-bold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded">
                {(reviewThresh * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min="0.40"
              max="0.90"
              step="0.01"
              value={reviewThresh}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                setReviewThresh(val);
                if (val > autoThresh) setAutoThresh(val);
              }}
              className="w-full accent-amber-500 cursor-pointer h-2 bg-slate-200 dark:bg-slate-700 rounded-lg"
            />
            <p className="text-xs text-slate-500 mt-1">Scores between this and Auto Merge (or missing fields) route to Review.</p>
          </div>

          {/* SEPARATE summary */}
          <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200/60 dark:border-slate-700/60 text-xs text-slate-600 dark:text-slate-400">
            <span className="font-semibold text-rose-500">SEPARATE:</span> Any pair below {(reviewThresh * 100).toFixed(0)}% or with any Hard Conflict (e.g., conflicting known flat numbers) is strictly separated.
          </div>
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-slate-800">
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset Defaults (90% / 70%)
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg shadow-sm transition"
            >
              <Check className="w-3.5 h-3.5" />
              Apply Thresholds
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
