import { useState, useEffect, useMemo } from 'react';
import { getTopology } from '../api';

/**
 * Color scale: green → yellow → red based on combined_priority_score (0-100).
 */
function scoreToColor(score) {
  const t = Math.min(score / 60, 1); // normalize: 60+ is "max danger"
  const r = Math.round(255 * Math.min(1, t * 2));
  const g = Math.round(255 * Math.min(1, (1 - t) * 2));
  return `rgb(${r}, ${g}, 40)`;
}

/** Node shape by asset type */
const TYPE_SHAPES = {
  substation: '■',
  transformer: '▲',
  feeder: '●',
};

const NODE_RADIUS = { substation: 18, transformer: 14, feeder: 10 };

export default function GridMap({ onSelectAsset, selectedAssetId }) {
  const [topology, setTopology] = useState(null);
  const [error, setError] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);

  useEffect(() => {
    getTopology()
      .then(setTopology)
      .catch((e) => setError(e.message));
  }, []);

  // Project lat/lon to SVG coordinates
  const { nodes, edges, bounds } = useMemo(() => {
    if (!topology) return { nodes: [], edges: [], bounds: null };

    const lats = topology.nodes.map((n) => n.lat);
    const lons = topology.nodes.map((n) => n.lon);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);

    const pad = 60;
    const width = 700;
    const height = 500;

    const projectedNodes = topology.nodes.map((n) => ({
      ...n,
      x: pad + ((n.lon - minLon) / (maxLon - minLon || 1)) * (width - 2 * pad),
      y: pad + ((maxLat - n.lat) / (maxLat - minLat || 1)) * (height - 2 * pad),
    }));

    const nodeMap = Object.fromEntries(projectedNodes.map((n) => [n.id, n]));
    const projectedEdges = topology.edges
      .map((e) => ({
        ...e,
        x1: nodeMap[e.from]?.x,
        y1: nodeMap[e.from]?.y,
        x2: nodeMap[e.to]?.x,
        y2: nodeMap[e.to]?.y,
      }))
      .filter((e) => e.x1 != null && e.x2 != null);

    return {
      nodes: projectedNodes,
      edges: projectedEdges,
      bounds: { width, height },
    };
  }, [topology]);

  if (error) {
    return <div className="panel error">Error loading grid: {error}</div>;
  }
  if (!topology) {
    return <div className="panel loading">Loading grid topology...</div>;
  }

  return (
    <div className="panel grid-map-panel">
      <h2>Grid Topology</h2>
      <div className="grid-legend">
        <span>
          <span className="legend-dot" style={{ background: 'rgb(0, 255, 40)' }} />
          Low Risk
        </span>
        <span>
          <span className="legend-dot" style={{ background: 'rgb(255, 255, 40)' }} />
          Medium
        </span>
        <span>
          <span className="legend-dot" style={{ background: 'rgb(255, 0, 40)' }} />
          High Risk
        </span>
        <span style={{ marginLeft: 16, fontSize: '0.8em', opacity: 0.7 }}>
          ■ Substation &nbsp; ▲ Transformer &nbsp; ● Feeder
        </span>
      </div>
      <svg
        viewBox={`0 0 ${bounds.width} ${bounds.height}`}
        className="grid-svg"
        width="100%"
      >
        {/* Edges */}
        {edges.map((e, i) => (
          <line
            key={i}
            x1={e.x1}
            y1={e.y1}
            x2={e.x2}
            y2={e.y2}
            stroke={e.type === 'tie' ? '#666' : '#888'}
            strokeWidth={e.type === 'tie' ? 1 : 1.5}
            strokeDasharray={e.type === 'tie' ? '4 4' : 'none'}
            opacity={0.5}
          />
        ))}

        {/* Nodes */}
        {nodes.map((n) => {
          const r = NODE_RADIUS[n.type] || 10;
          const color = scoreToColor(n.combined_priority_score || 0);
          const isSelected = n.id === selectedAssetId;
          const isHovered = n.id === hoveredNode;

          return (
            <g
              key={n.id}
              transform={`translate(${n.x}, ${n.y})`}
              onClick={() => onSelectAsset?.(n.id)}
              onMouseEnter={() => setHoveredNode(n.id)}
              onMouseLeave={() => setHoveredNode(null)}
              style={{ cursor: 'pointer' }}
            >
              {/* Selection ring */}
              {isSelected && (
                <circle r={r + 6} fill="none" stroke="#00bfff" strokeWidth={3} />
              )}

              {/* Node circle */}
              <circle
                r={r}
                fill={color}
                stroke={isHovered ? '#fff' : '#333'}
                strokeWidth={isHovered ? 2.5 : 1.5}
              />

              {/* Type icon */}
              <text
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={r * 0.8}
                fill="#fff"
                fontWeight="bold"
                pointerEvents="none"
              >
                {TYPE_SHAPES[n.type] || '?'}
              </text>

              {/* Label */}
              <text
                y={r + 14}
                textAnchor="middle"
                fontSize="10"
                fill="#ccc"
                pointerEvents="none"
              >
                {n.id}
              </text>

              {/* Tooltip on hover */}
              {isHovered && (
                <g>
                  <rect
                    x={-70}
                    y={-r - 50}
                    width={140}
                    height={38}
                    rx={4}
                    fill="rgba(0,0,0,0.85)"
                  />
                  <text
                    x={0}
                    y={-r - 36}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#fff"
                  >
                    {n.name}
                  </text>
                  <text
                    x={0}
                    y={-r - 22}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#ffa"
                  >
                    Score: {(n.combined_priority_score || 0).toFixed(1)} |
                    Customers: {(n.customers_served || 0).toLocaleString()}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
