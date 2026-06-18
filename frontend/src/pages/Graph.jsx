import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import { GitBranch, Loader, RotateCcw } from 'lucide-react'
import { api } from '../lib/api'

const NODE_RADIUS = 6
const COLORS = {
  default: '#6366f1',
  hub: '#a78bfa',
  selected: '#f59e0b',
}

function Legend() {
  return (
    <div className="absolute bottom-3 left-3 bg-dark-surface/90 border border-dark-border rounded-lg px-3 py-2 text-[10px] text-dark-subtle space-y-1">
      <div className="flex items-center gap-1.5">
        <div className="w-3 h-3 rounded-full bg-[#a78bfa]" />
        Hub (&gt;3 connections)
      </div>
      <div className="flex items-center gap-1.5">
        <div className="w-3 h-3 rounded-full bg-[#6366f1]" />
        Concept
      </div>
      <div className="flex items-center gap-1.5">
        <div className="w-3 h-3 rounded-full bg-[#f59e0b]" />
        Selected
      </div>
    </div>
  )
}

export default function Graph() {
  const svgRef = useRef(null)
  const simulationRef = useRef(null)
  const zoomRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)
  const [nodeCount, setNodeCount] = useState(0)
  const [edgeCount, setEdgeCount] = useState(0)

  const resetZoom = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current).transition().duration(400).call(zoomRef.current.transform, d3.zoomIdentity)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function build() {
      try {
        const data = await api.graph()
        if (cancelled) return

        const nodes = (data.nodes || []).map((n) => ({ ...n }))
        const links = (data.edges || []).map((e) => ({ ...e }))

        setNodeCount(nodes.length)
        setEdgeCount(links.length)
        setLoading(false)

        if (nodes.length === 0) return

        const svg = d3.select(svgRef.current)
        svg.selectAll('*').remove()

        const width = svgRef.current.clientWidth || 800
        const height = svgRef.current.clientHeight || 600

        const g = svg.append('g')

        const zoom = d3.zoom()
          .scaleExtent([0.15, 5])
          .on('zoom', (e) => g.attr('transform', e.transform))
        zoomRef.current = zoom
        svg.call(zoom)

        // Degree for hub detection
        const degree = {}
        links.forEach((l) => {
          degree[l.source] = (degree[l.source] || 0) + 1
          degree[l.target] = (degree[l.target] || 0) + 1
        })

        const sim = d3.forceSimulation(nodes)
          .force('link', d3.forceLink(links).id((d) => d.id).distance(90).strength(0.5))
          .force('charge', d3.forceManyBody().strength(-150))
          .force('center', d3.forceCenter(width / 2, height / 2))
          .force('collision', d3.forceCollide(NODE_RADIUS + 5))
        simulationRef.current = sim

        const link = g.append('g')
          .selectAll('line')
          .data(links)
          .join('line')
          .attr('stroke', '#374151')
          .attr('stroke-opacity', 0.5)
          .attr('stroke-width', (d) => Math.min(3, 1 + (d.weight || 0) * 0.4))

        const nodeG = g.append('g')
          .selectAll('g')
          .data(nodes)
          .join('g')
          .attr('cursor', 'pointer')
          .call(
            d3.drag()
              .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
              .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y })
              .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null })
          )
          .on('click', (e, d) => {
            e.stopPropagation()
            setSelected(d)
            const nbrs = new Set()
            links.forEach((l) => {
              const s = typeof l.source === 'object' ? l.source.id : l.source
              const t = typeof l.target === 'object' ? l.target.id : l.target
              if (s === d.id) nbrs.add(t)
              if (t === d.id) nbrs.add(s)
            })
            nodeG.select('circle')
              .attr('fill', (n) => n.id === d.id ? COLORS.selected : nbrs.has(n.id) ? COLORS.hub : COLORS.default)
              .attr('r', (n) => n.id === d.id ? NODE_RADIUS + 3 : NODE_RADIUS)
          })

        svg.on('click', () => {
          setSelected(null)
          nodeG.select('circle')
            .attr('fill', (n) => (degree[n.id] || 0) > 3 ? COLORS.hub : COLORS.default)
            .attr('r', NODE_RADIUS)
        })

        nodeG.append('circle')
          .attr('r', NODE_RADIUS)
          .attr('fill', (d) => (degree[d.id] || 0) > 3 ? COLORS.hub : COLORS.default)
          .attr('stroke', '#111827')
          .attr('stroke-width', 1.5)

        nodeG.append('text')
          .attr('dy', -NODE_RADIUS - 3)
          .attr('text-anchor', 'middle')
          .attr('font-size', '9px')
          .attr('fill', '#9ca3af')
          .attr('pointer-events', 'none')
          .text((d) => {
            const lbl = d.concept || d.label || d.id || ''
            return lbl.length > 18 ? lbl.slice(0, 16) + '..' : lbl
          })

        sim.on('tick', () => {
          link
            .attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y)
            .attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y)
          nodeG.attr('transform', (d) => `translate(${d.x},${d.y})`)
        })
      } catch (err) {
        if (!cancelled) {
          setError(err.message)
          setLoading(false)
        }
      }
    }

    build()
    return () => {
      cancelled = true
      simulationRef.current?.stop()
    }
  }, [])

  return (
    <div className="relative flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-dark-border shrink-0">
        <div className="flex items-center gap-2">
          <GitBranch size={16} className="text-lattice-400" />
          <span className="text-sm font-medium text-dark-text">Concept Graph</span>
          {!loading && (
            <span className="text-[10px] text-dark-subtle ml-1">
              {nodeCount} nodes · {edgeCount} edges
            </span>
          )}
        </div>
        <button
          onClick={resetZoom}
          className="p-1.5 rounded text-dark-subtle hover:text-dark-text hover:bg-dark-card transition-colors"
          title="Reset zoom"
        >
          <RotateCcw size={13} />
        </button>
      </div>

      {/* Canvas */}
      <div className="relative flex-1 overflow-hidden bg-dark-bg">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-dark-subtle">
              <Loader size={16} className="animate-spin text-lattice-400" />
              Loading graph...
            </div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
        {!loading && nodeCount === 0 && !error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
            <GitBranch size={40} className="text-dark-muted opacity-20" />
            <p className="text-sm text-dark-subtle">No concept graph yet.</p>
            <p className="text-xs text-dark-muted">Upload files and compile wiki pages to populate it.</p>
          </div>
        )}
        <svg ref={svgRef} className="w-full h-full" />
        {!loading && nodeCount > 0 && <Legend />}
      </div>

      {/* Selected panel */}
      {selected && (
        <div className="absolute top-14 right-3 w-52 bg-dark-surface border border-lattice-700/40 rounded-lg p-3 shadow-xl z-10">
          <p className="text-xs font-semibold text-lattice-300 mb-1">{selected.concept || selected.label || selected.id}</p>
          {selected.folder && <p className="text-[10px] text-dark-subtle">Folder: {selected.folder}</p>}
          {selected.connections != null && <p className="text-[10px] text-dark-subtle">Connections: {selected.connections}</p>}
        </div>
      )}
    </div>
  )
}
