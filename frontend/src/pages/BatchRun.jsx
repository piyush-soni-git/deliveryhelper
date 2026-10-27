import React, { useState, useEffect } from 'react';
import { 
  Play, Upload, Download, Search, Filter, Layers, CheckCircle2, 
  AlertTriangle, XCircle, Database, Sparkles, RefreshCw, ChevronLeft, ChevronRight, FileSpreadsheet
} from 'lucide-react';

export default function BatchRun({ onReviewNavigate }) {
  const [source, setSource] = useState('canonical');
  const [numRecords, setNumRecords] = useState(500);
  const [maxBlockSize, setMaxBlockSize] = useState(500);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  // Filters & Pagination
  const [tierFilter, setTierFilter] = useState('ALL');
  const [groupFilter, setGroupFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);

  const [csvFile, setCsvFile] = useState(null);

  // Run pipeline initially on canonical benchmark
  useEffect(() => {
    runPipeline('canonical');
  }, []);

  const runPipeline = async (chosenSource = source) => {
    setLoading(true);
    setError(null);
    try {
      if (chosenSource === 'uploaded' && csvFile) {
        const formData = new FormData();
        formData.append('file', csvFile);
        formData.append('max_block_size', maxBlockSize.toString());

        const res = await fetch('/api/batch/upload-csv', {
          method: 'POST',
          body: formData,
        });
        if (!res.ok) throw new Error("CSV processing failed");
        const resData = await res.json();
        setData(resData);
      } else {
        const res = await fetch('/api/batch/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source: chosenSource,
            num_records: chosenSource === 'canonical' ? 4 : numRecords,
            max_block_size: maxBlockSize,
            seed: 42
          })
        });
        if (!res.ok) throw new Error("Batch pipeline run failed");
        const resData = await res.json();
        setData(resData);
      }
      setCurrentPage(1);
    } catch (err) {
      setError(err.message || "Failed to execute pipeline");
    } finally {
      setLoading(false);
    }
  };

  const exportCSV = () => {
    if (!data || !data.records) return;
    const headers = ["Record ID", "Group ID", "Representative ID", "Representative Address", "Tier", "Raw Address"];
    const rows = data.records.map(r => [
      r.id,
      r.group_id,
      r.representative_id,
      `"${r.representative_address.replace(/"/g, '""')}"`,
      r.tier,
      `"${r.raw_address.replace(/"/g, '""')}"`
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `addressmatch_results_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Filtered Records
  const filteredRecords = (data?.records || []).filter(r => {
    const matchesTier = (tierFilter === 'ALL' || r.tier === tierFilter);
    const matchesGroup = (groupFilter === 'ALL' || r.group_id === groupFilter);
    const matchesSearch = !searchTerm || 
      r.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.raw_address.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.group_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.representative_address.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesTier && matchesGroup && matchesSearch;
  });

  const totalPages = Math.ceil(filteredRecords.length / pageSize) || 1;
  const paginatedRecords = filteredRecords.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  // Unique Group IDs for filter
  const uniqueGroups = Array.from(new Set((data?.records || []).map(r => r.group_id))).sort();

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 mb-2">
            <Layers className="w-3.5 h-3.5" />
            Batch Clustering Pipeline
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Batch Run & Deduplication Table
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Run end-to-end normalization, multi-key candidate blocking, consistency-checked clustering, and representative assignment.
          </p>
        </div>

        {data?.records && (
          <button
            onClick={exportCSV}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-bold text-slate-700 dark:text-slate-300 hover:border-emerald-500 shadow-sm transition"
          >
            <Download className="w-4 h-4 text-emerald-500" />
            Export Results (CSV)
          </button>
        )}
      </div>

      {/* Control Panel */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-end">
          {/* Source Selection */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Data Source</label>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full text-sm font-semibold p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="canonical">Canonical Reference (A101-A104)</option>
              <option value="synthetic">Synthetic Generator (Hard Negatives)</option>
              <option value="uploaded">Upload Custom CSV</option>
            </select>
          </div>

          {/* Size or CSV Upload */}
          {source === 'synthetic' ? (
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Dataset Size</label>
              <select
                value={numRecords}
                onChange={(e) => setNumRecords(parseInt(e.target.value))}
                className="w-full text-sm font-semibold p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value={100}>100 Addresses (~250 pairs)</option>
                <option value={500}>500 Addresses (~5k pairs)</option>
                <option value={1000}>1,000 Addresses (~18k pairs)</option>
                <option value={2500}>2,500 Addresses (~60k pairs)</option>
                <option value={5000}>5,000 Addresses (~140k pairs)</option>
              </select>
            </div>
          ) : source === 'uploaded' ? (
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">CSV File (id, address)</label>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setCsvFile(e.target.files[0])}
                className="w-full text-xs p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
          ) : (
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Benchmark Set</label>
              <div className="text-xs font-medium text-slate-600 dark:text-slate-400 p-2.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800">
                Lotus Apartments (A101-A104)
              </div>
            </div>
          )}

          {/* Max Block Size Slider */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="font-bold uppercase tracking-wider text-slate-500">MAX_BLOCK_SIZE</span>
              <span className="font-mono font-bold text-emerald-600">{maxBlockSize}</span>
            </div>
            <input
              type="range"
              min={50}
              max={1000}
              step={50}
              value={maxBlockSize}
              onChange={(e) => setMaxBlockSize(parseInt(e.target.value))}
              className="w-full accent-emerald-600 cursor-pointer h-2 bg-slate-200 dark:bg-slate-800 rounded-lg"
            />
          </div>

          {/* Trigger Button */}
          <div>
            <button
              onClick={() => runPipeline(source)}
              disabled={loading || (source === 'uploaded' && !csvFile)}
              className="w-full flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm text-white bg-emerald-600 hover:bg-emerald-500 active:scale-95 disabled:opacity-50 transition shadow-md shadow-emerald-600/20"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  Execute Pipeline
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 rounded-xl text-sm flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            {error}
          </div>
        )}
      </div>

      {/* KPI Summary Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Records</span>
            <div className="text-2xl font-black text-slate-900 dark:text-white mt-1">
              {data.record_count.toLocaleString()}
            </div>
            <span className="text-xs text-slate-500 mt-1 block">Input entity count</span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Physical Delivery Points</span>
            <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-1">
              {data.group_count.toLocaleString()}
            </div>
            <span className="text-xs text-slate-500 mt-1 block">Unique resolved clusters</span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Blocking Reduction</span>
            <div className="text-2xl font-black text-slate-900 dark:text-white mt-1 font-mono">
              {(data.blocking_summary?.reduction_ratio * 100).toFixed(1)}%
            </div>
            <span className="text-xs text-slate-500 mt-1 block">
              {data.blocking_summary?.candidate_comparisons.toLocaleString()} of {data.blocking_summary?.naive_comparisons.toLocaleString()} pairs
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Review Queue</span>
            <div className="flex items-center justify-between mt-1">
              <span className={`text-2xl font-black ${data.review_queue_count > 0 ? 'text-amber-500' : 'text-slate-400'}`}>
                {data.review_queue_count}
              </span>
              {data.review_queue_count > 0 && (
                <button
                  onClick={onReviewNavigate}
                  className="text-xs font-bold text-amber-600 dark:text-amber-400 hover:underline flex items-center gap-1"
                >
                  Inspect &rarr;
                </button>
              )}
            </div>
            <span className="text-xs text-slate-500 mt-1 block">Uncertain / transitive pairs</span>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      {data?.records && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row gap-4 justify-between items-center">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            {/* Search */}
            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Search Record ID, address, group..."
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                className="w-full pl-9 pr-3 py-2 text-xs font-medium rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            {/* Tier Filter */}
            <select
              value={tierFilter}
              onChange={(e) => { setTierFilter(e.target.value); setCurrentPage(1); }}
              className="text-xs font-bold p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
            >
              <option value="ALL">All Tiers</option>
              <option value="AUTO_MERGE">AUTO_MERGE</option>
              <option value="REVIEW">REVIEW</option>
              <option value="SEPARATE">SEPARATE</option>
            </select>

            {/* Group Filter */}
            <select
              value={groupFilter}
              onChange={(e) => { setGroupFilter(e.target.value); setCurrentPage(1); }}
              className="text-xs font-bold p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white max-w-[150px] truncate"
            >
              <option value="ALL">All Groups ({uniqueGroups.length})</option>
              {uniqueGroups.map(gid => (
                <option key={gid} value={gid}>{gid}</option>
              ))}
            </select>
          </div>

          <div className="text-xs font-medium text-slate-500">
            Showing <span className="font-bold text-slate-900 dark:text-white">{filteredRecords.length}</span> of {data.records.length} records
          </div>
        </div>
      )}

      {/* Results Table */}
      {data?.records && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 text-slate-500 font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">Record ID</th>
                  <th className="py-3.5 px-4 min-w-[260px]">Raw Free-Text Address</th>
                  <th className="py-3.5 px-4">Group ID</th>
                  <th className="py-3.5 px-4 min-w-[240px]">Representative Real Address</th>
                  <th className="py-3.5 px-4">Tier Status</th>
                  <th className="py-3.5 px-4">Parsed Components</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-700 dark:text-slate-300">
                {paginatedRecords.length > 0 ? (
                  paginatedRecords.map((row) => (
                    <tr key={row.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition">
                      {/* Record ID */}
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-900 dark:text-white">
                        {row.id}
                      </td>

                      {/* Raw Address */}
                      <td className="py-3.5 px-4 font-medium">
                        {row.raw_address}
                      </td>

                      {/* Group ID */}
                      <td className="py-3.5 px-4 font-mono">
                        <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-bold text-emerald-600 dark:text-emerald-400">
                          {row.group_id}
                        </span>
                      </td>

                      {/* Representative */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5">
                          {row.is_representative && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500 text-white shrink-0">
                              CANONICAL
                            </span>
                          )}
                          <span className="truncate">{row.representative_address}</span>
                        </div>
                      </td>

                      {/* Tier Badge */}
                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-1 rounded-full font-bold text-[10px] uppercase tracking-wider inline-flex items-center gap-1 ${
                          row.tier === 'AUTO_MERGE' 
                            ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300'
                            : row.tier === 'REVIEW'
                            ? 'bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                        }`}>
                          {row.tier === 'AUTO_MERGE' && <CheckCircle2 className="w-3 h-3 text-emerald-500" />}
                          {row.tier === 'REVIEW' && <AlertTriangle className="w-3 h-3 text-amber-500" />}
                          {row.tier === 'SEPARATE' && <XCircle className="w-3 h-3 text-slate-400" />}
                          {row.tier}
                        </span>
                      </td>

                      {/* Extracted pills */}
                      <td className="py-3.5 px-4">
                        <div className="flex flex-wrap gap-1">
                          {row.components.flat_no.value && (
                            <span className="px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 text-[10px] font-mono">
                              F:{row.components.flat_no.value}
                            </span>
                          )}
                          {row.components.building.value && (
                            <span className="px-1.5 py-0.5 rounded bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 text-[10px]">
                              B:{row.components.building.value}
                            </span>
                          )}
                          {row.components.pin.value && (
                            <span className="px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 text-[10px] font-mono">
                              P:{row.components.pin.value}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      No records match the active filter criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
            <div>
              Page <span className="font-bold text-slate-900 dark:text-white">{currentPage}</span> of {totalPages}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
