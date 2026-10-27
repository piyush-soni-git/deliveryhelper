import React, { useState, useEffect } from 'react';
import { 
  TrendingDown, Cpu, Zap, HardDrive, Calculator, CheckCircle2, 
  HelpCircle, RefreshCw, BarChart2 
} from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, Legend, AreaChart, Area 
} from 'recharts';

export default function ScalabilityPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchScalability = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/benchmark/scalability');
      if (!res.ok) throw new Error("Failed to load scalability benchmark data");
      const resData = await res.json();
      setData(resData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScalability();
  }, []);

  const series = data?.series || [];

  // Format numbers for clean readability
  const formatCompact = (val) => {
    if (val >= 1e12) return `${(val / 1e12).toFixed(1)}T`;
    if (val >= 1e9) return `${(val / 1e9).toFixed(1)}B`;
    if (val >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
    if (val >= 1e3) return `${(val / 1e3).toFixed(0)}k`;
    return val;
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 mb-2">
          <Zap className="w-3.5 h-3.5" />
          Subquadratic Efficiency Audit
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          10M Record Scalability Benchmark
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Empirical and projected comparison showing AddressMatch candidate generation $O(N \cdot B)$ vs. naive $O(N^2/2)$ quadratic bottleneck across 10k, 100k, 1M, and 10M records.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Target Scale</span>
          <div className="text-3xl font-black text-slate-900 dark:text-white">
            10,000,000
          </div>
          <span className="text-xs text-slate-500">Free-text Indian addresses</span>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-rose-500">Naive N²/2 Comparisons</span>
          <div className="text-3xl font-black font-mono text-rose-600 dark:text-rose-400">
            50 Trillion
          </div>
          <span className="text-xs text-slate-500">≈ 15.8 years compute time</span>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-500">AddressMatch Candidates</span>
          <div className="text-3xl font-black font-mono text-emerald-600 dark:text-emerald-400">
            ~300 Million
          </div>
          <span className="text-xs text-slate-500">Multi-key bounded blocks</span>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Candidate Reduction</span>
          <div className="text-3xl font-black font-mono text-slate-900 dark:text-white">
            99.9994%
          </div>
          <span className="text-xs text-emerald-600 dark:text-emerald-400 font-bold">5 Orders of Magnitude!</span>
        </div>
      </div>

      {/* Comparisons Chart */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-emerald-500" />
            Pairwise Comparisons: Naive Quadratic $O(N^2)$ vs. AddressMatch $O(N \cdot B)$
          </h3>
          <p className="text-xs text-slate-500">
            Logarithmic scale comparisons demonstrating subquadratic growth of candidate pairs.
          </p>
        </div>

        <div className="h-80 w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={series} margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 12, fontWeight: 'bold' }} />
              <YAxis 
                scale="log" 
                domain={[1000, 100000000000000]} 
                tickFormatter={formatCompact} 
                tick={{ fontSize: 11 }} 
              />
              <Tooltip 
                formatter={(val) => Number(val).toLocaleString()}
                contentStyle={{ 
                  backgroundColor: '#0f172a', 
                  borderColor: '#334155', 
                  borderRadius: '12px', 
                  color: '#fff',
                  fontSize: '12px' 
                }}
              />
              <Legend verticalAlign="top" height={36} />
              <Area 
                type="monotone" 
                dataKey="naive_comparisons" 
                name="Naive Pairwise N²/2" 
                stroke="#f43f5e" 
                fill="#f43f5e" 
                fillOpacity={0.15} 
                strokeWidth={2.5} 
              />
              <Area 
                type="monotone" 
                dataKey="pipeline_comparisons" 
                name="AddressMatch Bounded Candidates O(N·B)" 
                stroke="#10b981" 
                fill="#10b981" 
                fillOpacity={0.25} 
                strokeWidth={3} 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Benchmark Data Table */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 font-bold text-xs uppercase tracking-wider text-slate-500">
          Empirical and Extrapolated Scaling Matrix
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/50 dark:bg-slate-950/50 text-slate-500 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-3 px-4 font-bold">Scale (N)</th>
                <th className="py-3 px-4 font-bold">Naive Comparisons</th>
                <th className="py-3 px-4 font-bold">AddressMatch Candidates</th>
                <th className="py-3 px-4 font-bold">Reduction Ratio</th>
                <th className="py-3 px-4 font-bold">Estimated Runtime</th>
                <th className="py-3 px-4 font-bold">Memory Footprint</th>
                <th className="py-3 px-4 font-bold">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
              {series.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-4 font-bold text-slate-900 dark:text-white">
                    {row.record_count.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-rose-600 dark:text-rose-400">
                    {row.naive_comparisons.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-emerald-600 dark:text-emerald-400 font-bold">
                    {row.pipeline_comparisons.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-slate-900 dark:text-white">
                    {row.reduction_percentage.toFixed(4)}%
                  </td>
                  <td className="py-3 px-4 text-slate-600 dark:text-slate-400 font-sans">
                    {row.runtime_seconds < 60 ? `${row.runtime_seconds.toFixed(2)}s` : `${(row.runtime_seconds/60).toFixed(1)} min`}
                  </td>
                  <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                    {row.memory_mb < 1024 ? `${row.memory_mb.toFixed(0)} MB` : `${(row.memory_mb/1024).toFixed(1)} GB`}
                  </td>
                  <td className="py-3 px-4 font-sans">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      row.is_empirical 
                        ? 'bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300' 
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                    }`}>
                      {row.is_empirical ? 'Empirical' : 'Extrapolated'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Algorithmic Complexity Explanation Box */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
        <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Calculator className="w-5 h-5 text-emerald-500" />
          Complexity Analysis: Expected vs. Worst-Case Cost
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 space-y-2">
            <h4 className="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              Expected Cost: O(N · B̄) Time, O(N) Space
            </h4>
            <p>
              In practical distributions, Indian addresses partition naturally across states, cities, and localities. 
              By unioning building+locality tokens, phonetic Soundex/Metaphone of roads, and MinHash LSH buckets, the average block size $\bar{B}$ stays bounded ($15 \le \bar{B} \le 45$).
            </p>
            <p>
              Candidate generation and scoring therefore scale linearly with respect to records multiplied by average block density, yielding subquadratic throughput that easily runs on local workstations.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 space-y-2">
            <h4 className="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-amber-500" />
              Worst-Case Cost & Guaranteed Sub-blocking
            </h4>
            <p>
              In the pathological worst-case (e.g. 100,000 addresses all belonging to the exact same high-density township without distinct names), unconstrained blocking would degrade to $O(N^2)$.
            </p>
            <p className="font-semibold text-slate-800 dark:text-slate-200">
              AddressMatch eliminates this via Hierarchical Sub-blocking (MAX_BLOCK_SIZE = 500):
            </p>
            <p>
              Whenever any partition exceeds 500 records, the engine triggers hierarchical sub-partitioning by <span className="font-bold text-emerald-600">flat_no</span>, then <span className="font-bold text-emerald-600">building</span>, then <span className="font-bold text-emerald-600">road</span>. This guarantees that block sizes remain strictly bounded, preventing quadratic combinatorial blowup.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
