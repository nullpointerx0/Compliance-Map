import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Search, Eye, Filter, RefreshCw, ZoomIn, ZoomOut, Maximize2, ShieldAlert } from 'lucide-react';

import { API_BASE } from '../config';

const CITIES = [
  'Bengaluru', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 
  'Pune', 'Kolkata', 'Ahmedabad', 'Jaipur', 'Lucknow'
];

export default function NetworkGraph({ selectedCity: propSelectedCity }) {
  const [selectedCity, setSelectedCity] = useState(propSelectedCity || 'Bengaluru');
  const [minComponentSize, setMinComponentSize] = useState(2);
  const [edgeTypeFilter, setEdgeTypeFilter] = useState('all'); // 'all', 'shared_address', 'shared_license'
  const [searchQuery, setSearchQuery] = useState('');
  
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [selectedNode, setSelectedNode] = useState(null);
  const [componentDetails, setComponentDetails] = useState([]);
  const [loadingCompDetails, setLoadingCompDetails] = useState(false);
  
  const svgRef = useRef(null);
  const simulationRef = useRef(null);

  // Sync prop to local state
  useEffect(() => {
    if (propSelectedCity) {
      setSelectedCity(propSelectedCity);
    }
  }, [propSelectedCity]);

  // Fetch graph edges when city changes
  useEffect(() => {
    async function fetchGraphData() {
      setLoading(true);
      setError(null);
      setSelectedNode(null);
      setComponentDetails([]);
      try {
        const response = await fetch(`${API_BASE}/api/graph/edges?city=${selectedCity}`);
        if (!response.ok) throw new Error('Failed to load compliance network data');
        const data = await response.json();
        setGraphData(data);
      } catch (err) {
        console.error('NetworkGraph fetch failed:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchGraphData();
  }, [selectedCity]);

  // Fetch component details when a node is selected
  useEffect(() => {
    if (!selectedNode || selectedNode.component_id === null) return;
    
    async function fetchComponentDetails() {
      setLoadingCompDetails(true);
      try {
        const response = await fetch(`${API_BASE}/api/graph/component/${selectedNode.component_id}`);
        if (response.ok) {
          const data = await response.json();
          setComponentDetails(data);
        }
      } catch (err) {
        console.error('Failed to load component details', err);
      } finally {
        setLoadingCompDetails(false);
      }
    }
    
    fetchComponentDetails();
  }, [selectedNode]);

  // Initialize and run D3 force-directed simulation
  useEffect(() => {
    if (!svgRef.current || !graphData.nodes.length) return;

    // Filter nodes and links based on UI controls
    // 1. Filter links by edge type
    let filteredLinks = graphData.links.filter(d => {
      if (edgeTypeFilter === 'all') return true;
      return d.edge_type === edgeTypeFilter;
    });

    // 2. Identify which node IDs are connected with the filtered links
    const connectedNodeIds = new Set();
    filteredLinks.forEach(l => {
      connectedNodeIds.add(typeof l.source === 'object' ? l.source.id : l.source);
      connectedNodeIds.add(typeof l.target === 'object' ? l.target.id : l.target);
    });

    // 3. Filter nodes by min component size and search query
    // Node sizes: proportional to component_size (cluster size)
    let filteredNodes = graphData.nodes.filter(d => {
      const matchSize = d.component_size >= minComponentSize;
      if (!matchSize) return false;
      return true;
    });

    const activeNodeIds = new Set(filteredNodes.map(n => n.id));

    // Keep links only if both source and target nodes are in activeNodeIds
    filteredLinks = filteredLinks.filter(l => {
      const s = typeof l.source === 'object' ? l.source.id : l.source;
      const t = typeof l.target === 'object' ? l.target.id : l.target;
      return activeNodeIds.has(s) && activeNodeIds.has(t);
    });

    // Final clean up of nodes: only keep nodes if minComponentSize is 1, 
    // OR if the node is connected to at least one link in the active set
    if (minComponentSize > 1) {
      const nodeIdsWithActiveLinks = new Set();
      filteredLinks.forEach(l => {
        nodeIdsWithActiveLinks.add(typeof l.source === 'object' ? l.source.id : l.source);
        nodeIdsWithActiveLinks.add(typeof l.target === 'object' ? l.target.id : l.target);
      });
      filteredNodes = filteredNodes.filter(n => nodeIdsWithActiveLinks.has(n.id));
    }

    // Canvas dimensions
    const width = 800;
    const height = 600;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // clear canvas

    // Main group container supporting pan & zoom
    const container = svg.append('g').attr('class', 'graph-container');

    // Setup pan & zoom
    const zoom = d3.zoom()
      .scaleExtent([0.1, 8])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });
    
    svg.call(zoom);

    // Deep copy nodes and links for D3 mutation
    const nodes = filteredNodes.map(d => ({ ...d }));
    const links = filteredLinks.map(d => ({ ...d }));

    // Setup simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(60))
      .force('charge', d3.forceManyBody().strength(-120))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => Math.max(8, Math.sqrt(d.component_size) * 4) + 2));

    simulationRef.current = simulation;

    // Draw links
    const link = container.append('g')
      .attr('stroke-opacity', 0.6)
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke-width', 2)
      .attr('stroke', d => d.edge_type === 'shared_license' ? '#F59E0B' : '#3B82F6'); // orange vs blue

    // Draw nodes
    const node = container.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', 'node-group')
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        setSelectedNode(d);
        node.selectAll('circle').attr('stroke', '#1E293B').attr('stroke-width', 1.5);
        d3.select(event.currentTarget).select('circle')
          .attr('stroke', '#10B981')
          .attr('stroke-width', 3);
      })
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended)
      );

    // Circle style per compliance
    const nodeColor = (status) => {
      if (status === 'compliant') return '#10B981'; // Emerald Green
      if (status === 'expired') return '#EF4444'; // Red
      return '#6B7280'; // Unlicensed / grey
    };

    node.append('circle')
      .attr('r', d => Math.max(6, Math.sqrt(d.component_size) * 3))
      .attr('fill', d => nodeColor(d.compliance_status))
      .attr('stroke', '#1E293B')
      .attr('stroke-width', 1.5)
      .attr('opacity', 0.9);

    // Label showing short brand name if large component
    node.append('text')
      .attr('dy', d => Math.max(12, Math.sqrt(d.component_size) * 3 + 8))
      .attr('text-anchor', 'middle')
      .text(d => d.brand_name.length > 12 ? d.brand_name.substring(0, 10) + '..' : d.brand_name)
      .attr('fill', '#9CA3AF')
      .attr('font-size', '9px')
      .attr('font-family', 'sans-serif')
      .style('pointer-events', 'none');

    // Update positions on every tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('transform', d => `translate(${d.x}, ${d.y})`);
    });

    // Highlight search match
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      node.selectAll('circle')
        .attr('fill', d => d.brand_name.toLowerCase().includes(q) ? '#8B5CF6' : nodeColor(d.compliance_status)) // purple highlight
        .attr('r', d => d.brand_name.toLowerCase().includes(q) ? Math.max(12, Math.sqrt(d.component_size) * 4) : Math.max(6, Math.sqrt(d.component_size) * 3));
    }

    // Drag handlers
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Helper zoom functions
    window.zoomGraph = (factor) => {
      svg.transition().duration(300).call(zoom.scaleBy, factor);
    };

    window.resetGraphZoom = () => {
      svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
    };

    return () => {
      simulation.stop();
    };
  }, [graphData, edgeTypeFilter, minComponentSize, searchQuery]);

  return (
    <div className="flex flex-col lg:flex-row gap-6 w-full h-[calc(100vh-12rem)] min-h-[500px]">
      {/* Network Canvas & Filters */}
      <div className="flex-1 flex flex-col bg-darkCard border border-darkBorder rounded-xl p-4 overflow-hidden relative">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4 z-10">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2 text-white">
              <Maximize2 className="w-5 h-5 text-purple-400" />
              Compliance Network Graph
            </h2>
            <p className="text-xs text-gray-400">Emergent clustering of shared addresses and shared license networks</p>
          </div>
          
          {/* Controls Bar */}
          <div className="flex flex-wrap items-center gap-3">
            {/* City Selector */}
            <select
              value={selectedCity}
              onChange={(e) => setSelectedCity(e.target.value)}
              className="bg-darkBg border border-darkBorder text-gray-200 text-xs rounded-lg p-2 cursor-pointer outline-none focus:border-emerald-500"
            >
              {CITIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>

            {/* Edge Type Filter */}
            <select
              value={edgeTypeFilter}
              onChange={(e) => setEdgeTypeFilter(e.target.value)}
              className="bg-darkBg border border-darkBorder text-gray-200 text-xs rounded-lg p-2 cursor-pointer outline-none focus:border-emerald-500"
            >
              <option value="all">All Edges</option>
              <option value="shared_address">Shared Address Only</option>
              <option value="shared_license">Shared FSSAI License Only</option>
            </select>

            {/* Min Component Slider */}
            <div className="flex items-center gap-2 bg-darkBg border border-darkBorder rounded-lg px-2.5 py-1 text-xs">
              <span className="text-gray-400">Cluster Size &ge;</span>
              <input
                type="range"
                min="1"
                max="10"
                value={minComponentSize}
                onChange={(e) => setMinComponentSize(parseInt(e.target.value))}
                className="w-16 accent-purple-500 cursor-pointer h-1 rounded"
              />
              <span className="font-bold text-purple-400 font-mono w-4">{minComponentSize}</span>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search Brand Name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-darkBg border border-darkBorder text-gray-200 text-xs rounded-lg pl-8 pr-3 py-2 w-40 focus:ring-1 focus:ring-purple-500 focus:border-purple-500 outline-none"
              />
            </div>
          </div>
        </div>

        {/* Graph Render Container */}
        <div className="flex-1 w-full rounded-lg overflow-hidden relative border border-darkBorder/40 bg-darkBg/60">
          {loading && (
            <div className="absolute inset-0 bg-darkBg/75 backdrop-blur-sm z-50 flex items-center justify-center">
              <div className="flex flex-col items-center gap-2 text-purple-400 font-medium">
                <RefreshCw className="w-8 h-8 animate-spin" />
                <span>Generating Physics Layout...</span>
              </div>
            </div>
          )}
          {error && (
            <div className="absolute inset-0 bg-darkBg/90 z-50 flex items-center justify-center p-6 text-center">
              <div className="max-w-sm">
                <ShieldAlert className="w-12 h-12 text-red-500 mx-auto mb-3" />
                <h3 className="text-lg font-bold text-white mb-1">Failed to build network graph</h3>
                <p className="text-sm text-gray-400 mb-4">{error}</p>
              </div>
            </div>
          )}
          
          {/* Zoom Buttons overlay */}
          <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
            <button onClick={() => window.zoomGraph(1.3)} className="p-1.5 bg-darkCard border border-darkBorder hover:bg-darkBg text-gray-300 rounded shadow-md transition">
              <ZoomIn className="w-4 h-4" />
            </button>
            <button onClick={() => window.zoomGraph(0.7)} className="p-1.5 bg-darkCard border border-darkBorder hover:bg-darkBg text-gray-300 rounded shadow-md transition">
              <ZoomOut className="w-4 h-4" />
            </button>
            <button onClick={() => window.resetGraphZoom()} className="p-1.5 bg-darkCard border border-darkBorder hover:bg-darkBg text-gray-300 rounded shadow-md transition text-xs font-bold font-mono">
              FIT
            </button>
          </div>

          <svg ref={svgRef} className="w-full h-full" style={{ minHeight: '380px' }} />

          {/* Graph Legend overlay */}
          <div className="absolute bottom-4 left-4 z-10 bg-darkCard/90 border border-darkBorder backdrop-blur-md px-3 py-2.5 rounded-lg flex flex-col gap-1.5 text-xs shadow-lg">
            <span className="font-bold text-gray-300 mb-1">Nodes (Kitchens)</span>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#10B981]" />
              <span className="text-gray-400">Compliant</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#EF4444]" />
              <span className="text-gray-400">Expired License</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#6B7280]" />
              <span className="text-gray-400">Unlicensed (Type A)</span>
            </div>
            <span className="font-bold text-gray-300 mt-2 mb-1">Edges (Connections)</span>
            <div className="flex items-center gap-2">
              <span className="w-6 h-0.5 bg-[#3B82F6]" />
              <span className="text-gray-400">Shared Address</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-6 h-0.5 bg-[#F59E0B]" />
              <span className="text-gray-400">Shared License</span>
            </div>
          </div>
        </div>
      </div>

      {/* Network Detail Sidebar */}
      <div className="w-full lg:w-80 flex flex-col gap-4">
        {selectedNode ? (
          (() => {
            const nodeDetail = componentDetails.find(d => d.id === selectedNode.id) || {};
            const otherBrands = componentDetails.filter(d => d.id !== selectedNode.id);
            
            return (
              <div className="bg-darkCard border border-darkBorder rounded-xl p-5 flex flex-col h-full overflow-y-auto max-h-[calc(100vh-12rem)] shadow-lg">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs uppercase font-extrabold tracking-wider text-purple-400 px-2 py-0.5 rounded bg-purple-500/10 border border-purple-500/20">
                      Cluster ID: {selectedNode.component_id}
                    </span>
                    <span className="text-xs text-gray-400">Network Node</span>
                  </div>
                  
                  <h3 className="text-xl font-bold text-white mb-2 leading-tight">{selectedNode.brand_name}</h3>
                  
                  <div className="flex flex-wrap gap-2 mb-5">
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                      selectedNode.platform === 'swiggy' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/25' : 'bg-red-500/20 text-red-400 border border-red-500/25'
                    }`}>
                      {selectedNode.platform}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                      selectedNode.compliance_status === 'compliant' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/25' :
                      selectedNode.compliance_status === 'expired' ? 'bg-red-500/20 text-red-400 border border-red-500/25' :
                      'bg-gray-500/20 text-gray-400 border border-gray-500/25'
                    }`}>
                      {selectedNode.compliance_status}
                    </span>
                  </div>

                  {/* Anomaly Badge */}
                  <div className="mb-5">
                    <p className="text-[10px] text-gray-400 font-bold uppercase mb-1.5">Compliance Status</p>
                    {nodeDetail.anomaly_type ? (
                      <span className={`px-3 py-1 rounded text-xs font-bold block text-center ${
                        nodeDetail.anomaly_type === 'A_no_record' ? 'bg-red-500/15 text-red-400 border border-red-500/20' :
                        nodeDetail.anomaly_type === 'B_expired' ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20' :
                        'bg-purple-500/15 text-purple-400 border border-purple-500/20'
                      }`}>
                        {nodeDetail.anomaly_type === 'A_no_record' ? 'Type A — Unlicensed' :
                         nodeDetail.anomaly_type === 'B_expired' ? 'Type B — Expired License' :
                         'Type C — Shared License'}
                      </span>
                    ) : (
                      <span className="px-3 py-1 rounded text-xs font-bold block text-center bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
                        Active Compliant
                      </span>
                    )}
                  </div>

                  {/* FSSAI Match Stats */}
                  {selectedNode.compliance_status !== 'unlicensed' && (
                    <div className="bg-darkBg/40 border border-darkBorder/40 rounded-lg p-3 mb-5 text-xs">
                      <p className="text-[10px] text-gray-400 font-bold uppercase mb-2">FoSCoS Entity Resolving</p>
                      <div className="flex flex-col gap-2">
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Matched Name</span>
                          <span className="text-gray-200 font-medium">{nodeDetail.fssai_name || '-'}</span>
                        </div>
                        <div className="flex justify-between">
                          <div>
                            <span className="text-gray-400 block text-[9px] uppercase">License No</span>
                            <span className="text-gray-200 font-mono">{nodeDetail.license_no || '-'}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-gray-400 block text-[9px] uppercase">Confidence</span>
                            <span className="text-emerald-400 font-bold">{nodeDetail.confidence ? `${(nodeDetail.confidence * 100).toFixed(1)}%` : '-'}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Kitchen Physical Info */}
                  <div className="flex flex-col gap-3 mb-5 text-xs border-b border-darkBorder pb-4.5">
                    <div>
                      <p className="text-[10px] text-gray-400 font-bold uppercase mb-0.5">Physical Address</p>
                      <p className="text-gray-300 font-sans leading-relaxed">{selectedNode.address}</p>
                    </div>
                    <div className="flex justify-between">
                      <div>
                        <p className="text-[10px] text-gray-400 font-bold uppercase mb-0.5">Zone</p>
                        <p className="text-gray-300">{selectedNode.zone}, {selectedNode.city}</p>
                      </div>
                      <div className="text-right flex flex-col items-end">
                        <p className="text-[10px] text-gray-400 font-bold uppercase mb-0.5">Cluster Size</p>
                        <div className="flex items-center gap-1.5 justify-end">
                          {selectedNode.component_size >= 10 && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold tracking-wide bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse uppercase">
                              HIGH PRIORITY HUB
                            </span>
                          )}
                          {selectedNode.component_size >= 2 && selectedNode.component_size <= 4 && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold tracking-wide bg-gray-500/20 text-gray-400 border border-gray-500/30 uppercase">
                              LOW RISK
                            </span>
                          )}
                          <p className="text-purple-400 font-bold font-mono">{selectedNode.component_size} Brands</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Co-located Brands List */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-gray-300 mb-3">
                      Other Cluster Brands ({otherBrands.length})
                    </h4>
                    {loadingCompDetails ? (
                      <div className="flex items-center justify-center py-6 text-xs text-purple-400 gap-1.5">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Fetching cluster nodes...</span>
                      </div>
                    ) : (
                      <div className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-1">
                        {otherBrands.length > 0 ? (
                          otherBrands.map((brand) => (
                            <div key={brand.id} className="flex items-center justify-between p-2 rounded bg-darkBg/40 border border-darkBorder/40 text-xs">
                              <div className="truncate flex-1 pr-2">
                                <span className="font-semibold text-gray-300 truncate block">{brand.brand_name}</span>
                                <span className="text-[10px] text-gray-400 font-mono block">
                                  {brand.platform.toUpperCase()} • {brand.license_no || 'No License'}
                                </span>
                              </div>
                              <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                                brand.compliance_status === 'compliant' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/15' :
                                brand.compliance_status === 'expired' ? 'bg-red-500/10 text-red-400 border border-red-500/15' :
                                'bg-gray-500/10 text-gray-400 border border-gray-500/15'
                              }`}>
                                {brand.compliance_status.charAt(0).toUpperCase() + brand.compliance_status.slice(1)}
                              </span>
                            </div>
                          ))
                        ) : (
                          <p className="text-gray-500 text-xs italic">No other co-located brands in cluster.</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="mt-4 pt-4 border-t border-darkBorder text-[10px] text-gray-400 font-mono flex items-center justify-between">
                  <span>Node ID: #{selectedNode.id}</span>
                  <span className="flex items-center gap-1 text-purple-400">
                    <Eye className="w-3 h-3" /> Trace network
                  </span>
                </div>
              </div>
            );
          })()
        ) : (
          <div className="bg-darkCard border border-darkBorder rounded-xl p-5 flex items-center justify-center text-center text-gray-400 h-full shadow-lg">
            <p className="text-sm">Click a node in the graph layout to inspect physical license-sharing clusters and co-located virtual brands.</p>
          </div>
        )}
      </div>
    </div>
  );
}
