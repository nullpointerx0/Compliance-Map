import React, { useEffect, useState, useMemo, useRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import { FileDown, Search, Filter, ShieldAlert, Check, RefreshCw } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const CITIES = [
  'Bengaluru', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 
  'Pune', 'Kolkata', 'Ahmedabad', 'Jaipur', 'Lucknow'
];

export default function AnomalyTable() {
  const [rowData, setRowData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [totalRecords, setTotalRecords] = useState(0);
  
  // Filtering & Pagination State
  const [city, setCity] = useState('');
  const [platform, setPlatform] = useState('');
  const [anomalyType, setAnomalyType] = useState('');
  const [severity, setSeverity] = useState('');
  const [minComponentSize, setMinComponentSize] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  
  const gridRef = useRef();

  // Construct query parameters
  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    if (city) params.append('city', city);
    if (platform) params.append('platform', platform);
    if (anomalyType) params.append('anomaly_type', anomalyType);
    if (severity) params.append('severity', severity);
    if (minComponentSize) params.append('min_component_size', minComponentSize);
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());
    return params.toString();
  }, [city, platform, anomalyType, severity, minComponentSize, page, pageSize]);

  // Fetch paginated data
  useEffect(() => {
    async function fetchAnomalies() {
      setLoading(true);
      try {
        const response = await fetch(`${API_BASE}/api/anomalies?${queryParams}`);
        if (response.ok) {
          const data = await response.json();
          console.log('Fetched anomalies response:', data);
          setRowData(data.data || []);
          setTotalRecords(data.total_records || 0);
        }
      } catch (err) {
        console.error('Error fetching anomalies', err);
      } finally {
        setLoading(false);
      }
    }
    fetchAnomalies();
  }, [queryParams]);

  // Handle filter changes (Reset page to 1)
  const handleFilterChange = (setter, value) => {
    setter(value);
    setPage(1);
  };

  // Export filtered query to CSV
  const handleExport = () => {
    // Generate identical query params but omit page & page_size to get the entire list
    const params = new URLSearchParams();
    if (city) params.append('city', city);
    if (platform) params.append('platform', platform);
    if (anomalyType) params.append('anomaly_type', anomalyType);
    if (severity) params.append('severity', severity);
    if (minComponentSize) params.append('min_component_size', minComponentSize);
    
    window.open(`${API_BASE}/api/anomalies/export?${params.toString()}`);
  };

  // Custom cell renderers for AG Grid
  const platformRenderer = (params) => {
    const isSwiggy = params.value?.toLowerCase() === 'swiggy';
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
        isSwiggy ? 'bg-orange-500/10 text-orange-400 border border-orange-500/15' : 'bg-red-500/10 text-red-400 border border-red-500/15'
      }`}>
        {params.value}
      </span>
    );
  };

  const anomalyTypeRenderer = (params) => {
    const val = params.value;
    let text = 'Unknown';
    let classes = 'bg-gray-500/10 text-gray-400 border border-gray-500/15';
    
    if (val === 'A_no_record') {
      text = 'Type A — Unlicensed';
      classes = 'bg-red-500/10 text-red-400 border border-red-500/15';
    } else if (val === 'B_expired') {
      text = 'Type B — Expired';
      classes = 'bg-amber-500/10 text-amber-400 border border-amber-500/15';
    } else if (val === 'C_multi_brand') {
      text = 'Type C — Shared License';
      classes = 'bg-purple-500/10 text-purple-400 border border-purple-500/15';
    }
    
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${classes}`}>
        {text}
      </span>
    );
  };

  const severityRenderer = (params) => {
    const isHigh = params.value?.toLowerCase() === 'high';
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
        isHigh ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
      }`}>
        {params.value}
      </span>
    );
  };

  // AG Grid column configurations
  const columnDefs = useMemo(() => [
    { field: 'brand_name', headerName: 'Brand Name', minWidth: 160, sortable: true, filter: true },
    { field: 'platform', headerName: 'Platform', width: 100, cellRenderer: platformRenderer },
    { field: 'city', headerName: 'City', width: 110, sortable: true },
    { field: 'zone', headerName: 'Zone', width: 120 },
    { field: 'anomaly_type', headerName: 'Anomaly Type', width: 170, cellRenderer: anomalyTypeRenderer },
    { field: 'severity', headerName: 'Severity', width: 100, cellRenderer: severityRenderer },
    { field: 'fssai_name', headerName: 'FSSAI Match Name', minWidth: 160, valueFormatter: p => p.value || '-' },
    { field: 'license_no', headerName: 'License Number', width: 140, valueFormatter: p => p.value || '-', cellClass: 'font-mono' },
    { field: 'confidence', headerName: 'Confidence', width: 110, valueFormatter: p => p.value ? `${(p.value * 100).toFixed(1)}%` : '0%' },
    { field: 'status', headerName: 'Status', width: 110, valueFormatter: p => p.value?.toUpperCase() || '-' },
    { field: 'expiry_date', headerName: 'Expiry Date', width: 125, valueFormatter: p => p.value || '-' },
    { field: 'component_size', headerName: 'Cluster Size', width: 115, type: 'numericColumn', cellClass: 'font-mono text-purple-400 font-bold' }
  ], []);

  const defaultColDef = useMemo(() => ({
    resizable: true,
    flex: 1,
    minWidth: 90
  }), []);

  const totalPages = Math.ceil(totalRecords / pageSize) || 1;

  return (
    <div className="flex flex-col bg-darkCard border border-darkBorder rounded-xl p-5 w-full h-[calc(100vh-12rem)] min-h-[500px] overflow-hidden">
      
      {/* Header and Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2 text-white">
            <ShieldAlert className="w-5 h-5 text-red-500" />
            Compliance Anomaly Directory
          </h2>
          <p className="text-xs text-gray-400">Filter, sort, search, and export the official city-level kitchen audit database</p>
        </div>
        
        <button
          onClick={handleExport}
          className="flex items-center gap-1.5 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg transition shadow-md"
        >
          <FileDown className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Filters Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-4 bg-darkBg/40 border border-darkBorder/40 p-3 rounded-lg text-xs">
        {/* City Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-gray-400 font-semibold">City</label>
          <select
            value={city}
            onChange={(e) => handleFilterChange(setCity, e.target.value)}
            className="bg-darkBg border border-darkBorder text-gray-200 rounded p-1.5 outline-none"
          >
            <option value="">All Cities</option>
            {CITIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Platform Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-gray-400 font-semibold">Platform</label>
          <select
            value={platform}
            onChange={(e) => handleFilterChange(setPlatform, e.target.value)}
            className="bg-darkBg border border-darkBorder text-gray-200 rounded p-1.5 outline-none"
          >
            <option value="">All Platforms</option>
            <option value="swiggy">Swiggy</option>
            <option value="zomato">Zomato</option>
          </select>
        </div>

        {/* Anomaly Type Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-gray-400 font-semibold">Anomaly Type</label>
          <select
            value={anomalyType}
            onChange={(e) => handleFilterChange(setAnomalyType, e.target.value)}
            className="bg-darkBg border border-darkBorder text-gray-200 rounded p-1.5 outline-none"
          >
            <option value="">All Anomalies</option>
            <option value="A_no_record">Type A — Unlicensed</option>
            <option value="B_expired">Type B — Expired License</option>
            <option value="C_multi_brand">Type C — Shared License</option>
          </select>
        </div>

        {/* Severity Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-gray-400 font-semibold">Severity</label>
          <select
            value={severity}
            onChange={(e) => handleFilterChange(setSeverity, e.target.value)}
            className="bg-darkBg border border-darkBorder text-gray-200 rounded p-1.5 outline-none"
          >
            <option value="">All Severities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
          </select>
        </div>

        {/* Min Component Size Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-gray-400 font-semibold">Min Cluster Size</label>
          <select
            value={minComponentSize}
            onChange={(e) => handleFilterChange(setMinComponentSize, e.target.value)}
            className="bg-darkBg border border-darkBorder text-gray-200 rounded p-1.5 outline-none"
          >
            <option value="">Any Size</option>
            <option value="2">2+ Shared nodes</option>
            <option value="5">5+ Shared nodes</option>
            <option value="10">10+ Shared nodes</option>
          </select>
        </div>
      </div>

      {/* Grid Canvas */}
      <div className="flex-1 w-full relative ag-theme-quartz-dark rounded-lg overflow-hidden border border-darkBorder/40">
        {loading && (
          <div className="absolute inset-0 bg-darkBg/60 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-emerald-400 font-medium">
              <RefreshCw className="w-8 h-8 animate-spin" />
              <span>Querying Database Records...</span>
            </div>
          </div>
        )}
        
        <AgGridReact
          ref={gridRef}
          rowData={rowData || []}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          animateRows={true}
          headerHeight={44}
          rowHeight={40}
        />
      </div>

      {/* Pagination controls footer */}
      <div className="flex items-center justify-between border-t border-darkBorder mt-4 pt-3.5 text-xs text-gray-400 font-sans">
        <div className="flex items-center gap-3">
          <span>Page <strong>{page}</strong> of <strong>{totalPages}</strong></span>
          <span className="text-gray-500">|</span>
          <span>Showing {rowData.length} of {totalRecords} total anomalies</span>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 bg-darkBg border border-darkBorder text-gray-300 hover:bg-darkBorder/30 rounded font-semibold disabled:opacity-40 transition"
          >
            Previous
          </button>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 bg-darkBg border border-darkBorder text-gray-300 hover:bg-darkBorder/30 rounded font-semibold disabled:opacity-40 transition"
          >
            Next
          </button>
        </div>
      </div>

    </div>
  );
}
