import React, { useState, useEffect } from 'react';
import { 
  Compass, Play, Layers, AlertTriangle, BarChart2, Zap, 
  Sun, Moon, Sliders, CheckCircle2, ShieldCheck, MapPin
} from 'lucide-react';

import Playground from './pages/Playground';
import BatchRun from './pages/BatchRun';
import ReviewQueue from './pages/ReviewQueue';
import MetricsDashboard from './pages/MetricsDashboard';
import ScalabilityPage from './pages/ScalabilityPage';
import ThresholdModal from './components/ThresholdModal';

export default function App() {
  const [activeTab, setActiveTab] = useState('playground');
  const [darkMode, setDarkMode] = useState(true);
  const [isThresholdModalOpen, setIsThresholdModalOpen] = useState(false);
  const [thresholds, setThresholds] = useState({ threshold_auto: 0.90, threshold_review: 0.70 });
  const [serverOnline, setServerOnline] = useState(false);
  const [reviewCount, setReviewCount] = useState(0);

  // Initialize theme
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Check health and review queue count
  const checkStatus = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) setServerOnline(true);
      
      const qRes = await fetch('/api/review/list');
      if (qRes.ok) {
        const qData = await qRes.json();
        setReviewCount(qData.queue_count || 0);
      }

      const tRes = await fetch('/api/config/thresholds');
      if (tRes.ok) {
        const tData = await tRes.json();
        setThresholds(tData);
      }
    } catch (e) {
      setServerOnline(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveThresholds = async (newThresholds) => {
    try {
      const res = await fetch('/api/config/thresholds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newThresholds)
      });
      if (res.ok) {
        const data = await res.json();
        setThresholds(data.thresholds);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">
      {/* Navigation Header */}
      <header className="sticky top-0 z-40 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
                <MapPin className="w-5 h-5 fill-white/20" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-black text-lg tracking-tight text-slate-900 dark:text-white">
                    Address<span className="text-emerald-600 dark:text-emerald-400">Match</span>
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 font-bold">
                    v1.0
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 font-medium hidden sm:block">
                  Physical Delivery Point Deduplication Engine
                </p>
              </div>
            </div>

            {/* Nav Tabs */}
            <nav className="flex items-center gap-1 sm:gap-2">
              <button
                onClick={() => setActiveTab('playground')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
                  activeTab === 'playground'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                <Compass className="w-4 h-4" />
                <span className="hidden md:inline">Playground</span>
              </button>

              <button
                onClick={() => setActiveTab('batch')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
                  activeTab === 'batch'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                <Layers className="w-4 h-4" />
                <span className="hidden md:inline">Batch Run</span>
              </button>

              <button
                onClick={() => setActiveTab('review')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition relative ${
                  activeTab === 'review'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                <AlertTriangle className="w-4 h-4" />
                <span className="hidden md:inline">Review Queue</span>
                {reviewCount > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-amber-500 text-white">
                    {reviewCount}
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab('metrics')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
                  activeTab === 'metrics'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                <BarChart2 className="w-4 h-4" />
                <span className="hidden md:inline">Metrics</span>
              </button>

              <button
                onClick={() => setActiveTab('scalability')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
                  activeTab === 'scalability'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                <Zap className="w-4 h-4" />
                <span className="hidden md:inline">Scalability (10M)</span>
              </button>
            </nav>

            {/* Utility Actions */}
            <div className="flex items-center gap-2">
              {/* Threshold Config Button */}
              <button
                onClick={() => setIsThresholdModalOpen(true)}
                title="Configure Thresholds"
                className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                <Sliders className="w-4 h-4" />
              </button>

              {/* Theme Toggle */}
              <button
                onClick={() => setDarkMode(!darkMode)}
                title="Toggle Theme"
                className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
              </button>

              {/* Server indicator */}
              <div 
                title={serverOnline ? "Backend Connected (FastAPI)" : "Backend Disconnected"}
                className={`w-2.5 h-2.5 rounded-full ml-1 ${serverOnline ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Page Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'playground' && <Playground />}
        {activeTab === 'batch' && <BatchRun onReviewNavigate={() => setActiveTab('review')} />}
        {activeTab === 'review' && <ReviewQueue />}
        {activeTab === 'metrics' && <MetricsDashboard />}
        {activeTab === 'scalability' && <ScalabilityPage />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 py-6 text-center text-xs text-slate-400">
        <p>AddressMatch — Local Indian Address Deduplication & Entity Resolution Engine</p>
        <p className="mt-1 text-[11px] text-slate-500">
          Zero external APIs • RapidFuzz component scoring • Consistency-checked Union-Find • Subquadratic bounded blocking
        </p>
      </footer>

      {/* Threshold Modal */}
      <ThresholdModal
        isOpen={isThresholdModalOpen}
        onClose={() => setIsThresholdModalOpen(false)}
        thresholds={thresholds}
        onSave={handleSaveThresholds}
      />
    </div>
  );
}
