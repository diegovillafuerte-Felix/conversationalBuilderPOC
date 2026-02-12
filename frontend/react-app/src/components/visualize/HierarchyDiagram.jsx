import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';

import AgentNode from './nodes/AgentNode';
import { useVisualizeStore } from '../../store/visualizeStore';

const nodeTypes = {
  agentNode: AgentNode,
};

const NODE_WIDTH = 180;
const NODE_HEIGHT = 80;

function getLayoutedElements(nodes, edges) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 100 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

export default function HierarchyDiagram() {
  const agents = useVisualizeStore((state) => state.agents);
  const getHierarchyGraph = useVisualizeStore((state) => state.getHierarchyGraph);
  const detailPanel = useVisualizeStore((state) => state.detailPanel);
  const hideDetailPanel = useVisualizeStore((state) => state.hideDetailPanel);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (agents.length > 0) {
      const { nodes: graphNodes, edges: graphEdges } = getHierarchyGraph();
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        graphNodes,
        graphEdges
      );
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    }
  }, [agents, getHierarchyGraph, setNodes, setEdges]);

  const selectedAgent = detailPanel?.type === 'agent' ? detailPanel.data : null;

  return (
    <div className="hierarchy-container">
      <div className={`diagram-wrapper ${selectedAgent ? 'with-panel' : ''}`}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#e5e7eb" gap={16} />
          <Controls showInteractive={false} />
          <MiniMap
            nodeColor={(node) => (node.data.isActive ? '#3b82f6' : '#9ca3af')}
            maskColor="rgba(0, 0, 0, 0.1)"
          />
        </ReactFlow>
      </div>

      {selectedAgent && (
        <div className="detail-panel">
          <div className="detail-panel-header">
            <h3>{selectedAgent.name}</h3>
            <button className="close-btn" onClick={hideDetailPanel}>
              &times;
            </button>
          </div>

          <div className="detail-panel-content">
            <div className="detail-section">
              <h4>Description</h4>
              <p className="detail-description">
                {selectedAgent.description || 'No description'}
              </p>
            </div>

            <div className="detail-section">
              <h4>Model Config</h4>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Model</span>
                  <span className="detail-value">
                    {selectedAgent.model_config?.model || 'default'}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Temperature</span>
                  <span className="detail-value">
                    {selectedAgent.model_config?.temperature ?? 0.7}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Max Tokens</span>
                  <span className="detail-value">
                    {selectedAgent.model_config?.maxTokens || 1000}
                  </span>
                </div>
              </div>
            </div>

            <div className="detail-section">
              <h4>Navigation</h4>
              <div className="detail-badges">
                {selectedAgent.navigation?.canGoUp && (
                  <span className="detail-badge">Can Go Up</span>
                )}
                {selectedAgent.navigation?.canGoHome && (
                  <span className="detail-badge">Can Go Home</span>
                )}
                {selectedAgent.navigation?.canEscalate && (
                  <span className="detail-badge">Can Escalate</span>
                )}
              </div>
            </div>

            {selectedAgent.tools && selectedAgent.tools.length > 0 && (
              <div className="detail-section">
                <h4>Tools ({selectedAgent.tools.length})</h4>
                <div className="detail-list">
                  {selectedAgent.tools.map((tool) => (
                    <div key={tool.name} className="detail-list-item">
                      <span className="tool-name">{tool.name}</span>
                      {tool.side_effects && tool.side_effects !== 'none' && (
                        <span className={`tool-badge ${tool.side_effects}`}>
                          {tool.side_effects}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedAgent.subflows && selectedAgent.subflows.length > 0 && (
              <div className="detail-section">
                <h4>Subflows ({selectedAgent.subflows.length})</h4>
                <div className="detail-list">
                  {selectedAgent.subflows.map((subflow) => (
                    <div key={subflow.id} className="detail-list-item">
                      <span className="subflow-name">{subflow.name || subflow.id}</span>
                      <span className="subflow-states">
                        {subflow.states?.length || 0} states
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
