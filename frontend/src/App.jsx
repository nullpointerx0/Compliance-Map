import React, { useState, useEffect } from 'react';
import CityMap from './components/CityMap';
import NetworkGraph from './components/NetworkGraph';
import AnomalyTable from './components/AnomalyTable';
import Analytics from './components/Analytics';
import { 
  Map, Network, Database, BarChart3, AlertTriangle, ShieldCheck, 
  ShieldAlert, RefreshCw, Layers, Award 
} from 'lucide-react';

import { API_BASE } from './config';

function App() {
  const [activeTab, setActiveTab] = useState('map');
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [backendOnline, setBackendOnline] = useState(true);

  // Fetch top-level global audit statistics and check health
  useEffect(() => {
    async function checkHealthAndFetchStats() {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);

      try {
        const response = await fetch(`${API_BASE}/api/stats/overview`, {
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (response.ok) {
          const data = await response.json();
          setStats(data);
          setBackendOnline(true);
        } else {
          setBackendOnline(false);
          console.error('Failed to load global compliance metrics: backend returned non-OK status');
        }
      } catch (err) {
        clearTimeout(timeoutId);
        console.error('Backend connection failed:', err);
        setBackendOnline(false);
      } finally {
        setLoading(false);
      }
    }
    checkHealthAndFetchStats();
  }, []);

  return (
    <div className="min-h-screen bg-[#090D16] text-gray-100 flex flex-col font-sans">
      {!backendOnline && (
        <div className="w-full bg-red-600/90 border-b border-red-500 text-white py-2.5 px-6 text-center text-xs font-bold flex items-center justify-center gap-2 z-[2000] uppercase tracking-wide">
          <span>⚠ Backend offline — start uvicorn before using the dashboard</span>
        </div>
      )}
      
      {/* Top Banner Navigation */}
      <header className="border-b border-darkBorder bg-darkCard/50 backdrop-blur-md sticky top-0 z-[1000] px-6 py-4 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl">
            <Layers className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
              GHOST KITCHEN COMPLIANCE MONITOR
              <span className="text-[10px] font-mono tracking-widest text-emerald-400 bg-emerald-500/10 border border-emerald-500/25 px-2 py-0.5 rounded font-extrabold uppercase">
                Academic Audit
              </span>
            </h1>
            <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">
              BT232AT • Bio Safety Standards & Ethics • RV College of Engineering
            </p>
          </div>
        </div>

        {/* Tab Selector buttons */}
        <div className="flex bg-darkBg border border-darkBorder p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('map')}
            className={`flex items-center gap-1.5 px-4.5 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'map' 
                ? 'bg-emerald-500 text-white shadow-lg' 
                : 'text-gray-400 hover:text-white hover:bg-darkBorder/30'
            }`}
          >
            <Map className="w-4 h-4" />
            City Map
          </button>
          
          <button
            onClick={() => setActiveTab('network')}
            className={`flex items-center gap-1.5 px-4.5 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'network' 
                ? 'bg-purple-600 text-white shadow-lg' 
                : 'text-gray-400 hover:text-white hover:bg-darkBorder/30'
            }`}
          >
            <Network className="w-4 h-4" />
            Compliance Network
          </button>

          <button
            onClick={() => setActiveTab('directory')}
            className={`flex items-center gap-1.5 px-4.5 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'directory' 
                ? 'bg-red-500 text-white shadow-lg' 
                : 'text-gray-400 hover:text-white hover:bg-darkBorder/30'
            }`}
          >
            <Database className="w-4 h-4" />
            Anomaly Directory
          </button>

          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex items-center gap-1.5 px-4.5 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'analytics' 
                ? 'bg-amber-500 text-white shadow-lg' 
                : 'text-gray-400 hover:text-white hover:bg-darkBorder/30'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            Analytics Hub
          </button>
        </div>
      </header>

      {/* Main View Container */}
      <main className="flex-1 p-6 flex flex-col items-center justify-start w-full max-w-7xl mx-auto gap-6">
        
        {/* Real-time counters sub-bar */}
        {!loading && stats && (
          <div className="w-full grid grid-cols-2 md:grid-cols-5 gap-3.5 border border-darkBorder bg-darkCard/20 p-3 rounded-xl text-xs">
            <div className="flex flex-col gap-0.5 px-2">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Total Scraped</span>
              <span className="text-sm font-extrabold text-white font-mono">{stats.total_listings} Listings</span>
            </div>
            <div className="flex flex-col gap-0.5 border-l border-darkBorder/50 px-4">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Active Compliance
              </span>
              <span className="text-sm font-extrabold text-emerald-400 font-mono">{stats.compliance_rate}%</span>
            </div>
            <div className="flex flex-col gap-0.5 border-l border-darkBorder/50 px-4">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5 text-red-400" /> Unlicensed (A)
              </span>
              <span className="text-sm font-extrabold text-red-400 font-mono">{stats.anomalies.type_a}</span>
            </div>
            <div className="flex flex-col gap-0.5 border-l border-darkBorder/50 px-4">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Expired (B)
              </span>
              <span className="text-sm font-extrabold text-amber-400 font-mono">{stats.anomalies.type_b}</span>
            </div>
            <div className="flex flex-col gap-0.5 border-l border-darkBorder/50 px-4">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider flex items-center gap-1">
                <Award className="w-3.5 h-3.5 text-purple-400" /> Shared License (C)
              </span>
              <span className="text-sm font-extrabold text-purple-400 font-mono">{stats.anomalies.type_c}</span>
            </div>
          </div>
        )}

        {/* Tab contents */}
        <div className="w-full flex-1">
          {activeTab === 'map' && <CityMap />}
          {activeTab === 'network' && <NetworkGraph />}
          {activeTab === 'directory' && <AnomalyTable />}
          {activeTab === 'analytics' && <Analytics />}
        </div>
      </main>

      <footer className="border-t border-darkBorder py-4 px-6 text-center text-[10px] text-gray-400 bg-darkCard/10 font-mono">
        <p>&copy; {new Date().getFullYear()} RV College of Engineering - Bio Safety Standards (BT232AT). Prepared under MIT License guidelines.</p>
      </footer>

    </div>
  );
}

export default App;
