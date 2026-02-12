import { useEffect } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';

import StateNode from './nodes/StateNode';
import { useVisualizeStore } from '../../store/visualizeStore';

const nodeTypes = {
  stateNode: StateNode,
};

const NODE_WIDTH = 160;
const NODE_HEIGHT = 70;

function getLayoutedElements(nodes, edges) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 80 });

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

export default function StateMachineDiagram() {
  const agents = useVisualizeStore((state) => state.agents);
  const selectedAgent = useVisualizeStore((state) => state.selectedAgent);
  const selectedSubflow = useVisualizeStore((state) => state.selectedSubflow);
  const selectAgent = useVisualizeStore((state) => state.selectAgent);
  const selectSubflow = useVisualizeStore((state) => state.selectSubflow);
  const getSubflowGraph = useVisualizeStore((state) => state.getSubflowGraph);
  const detailPanel = useVisualizeStore((state) => state.detailPanel);
  const hideDetailPanel = useVisualizeStore((state) => state.hideDetailPanel);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Get agents with subflows
  const agentsWithSubflows = agents.filter(
    (a) => a.subflows && a.subflows.length > 0
  );

  useEffect(() => {
    if (selectedSubflow) {
      const { nodes: graphNodes, edges: graphEdges } = getSubflowGraph(selectedSubflow);
      if (graphNodes.length > 0) {
        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
          graphNodes,
          graphEdges
        );
        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
      } else {
        setNodes([]);
        setEdges([]);
      }
    } else {
      setNodes([]);
      setEdges([]);
    }
  }, [selectedSubflow, getSubflowGraph, setNodes, setEdges]);

  const selectedState = detailPanel?.type === 'state' ? detailPanel.data : null;

  return (
    <div className="state-machine-container">
      <div className="flow-selector">
        <div className="selector-group">
          <label>Agent</label>
          <select
            value={selectedAgent?.id || ''}
            onChange={(e) => {
              const agent = agents.find((a) => a.id === e.target.value);
              selectAgent(agent || null);
            }}
          >
            <option value="">Select an agent...</option>
            {agentsWithSubflows.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} ({agent.subflows?.length || 0} flows)
              </option>
            ))}
          </select>
        </div>

        <div className="selector-group">
          <label>Subflow</label>
          <select
            value={selectedSubflow?.id || ''}
            onChange={(e) => {
              const subflow = selectedAgent?.subflows?.find(
                (s) => s.id === e.target.value
              );
              selectSubflow(subflow || null);
            }}
            disabled={!selectedAgent}
          >
            <option value="">Select a subflow...</option>
            {selectedAgent?.subflows?.map((subflow) => (
              <option key={subflow.id} value={subflow.id}>
                {subflow.name || subflow.id} ({subflow.states?.length || 0} states)
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className={`diagram-wrapper ${selectedState ? 'with-panel' : ''}`}>
        {selectedSubflow ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            minZoom={0.3}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
            defaultEdgeOptions={{
              markerEnd: { type: MarkerType.ArrowClosed },
            }}
          >
            <Background color="#e5e7eb" gap={16} />
            <Controls showInteractive={false} />
          </ReactFlow>
        ) : (
          <div className="empty-diagram">
            <p>Select an agent and subflow to view the state machine</p>
          </div>
        )}
      </div>

      {selectedState && (
        <div className="detail-panel">
          <div className="detail-panel-header">
            <h3>{selectedState.name || selectedState.id}</h3>
            <button className="close-btn" onClick={hideDetailPanel}>
              &times;
            </button>
          </div>

          <div className="detail-panel-content">
            <div className="detail-section">
              <h4>State ID</h4>
              <code className="state-id-code">{selectedState.id}</code>
            </div>

            {selectedState.agent_instructions && (
              <div className="detail-section">
                <h4>Agent Instructions</h4>
                <p className="detail-description instructions">
                  {selectedState.agent_instructions}
                </p>
              </div>
            )}

            {selectedState.on_enter && (
              <div className="detail-section">
                <h4>On Enter Actions</h4>
                {selectedState.on_enter.message && (
                  <div className="on-enter-item">
                    <span className="on-enter-label">Message:</span>
                    <span className="on-enter-value">{selectedState.on_enter.message}</span>
                  </div>
                )}
                {selectedState.on_enter.callTool && (
                  <div className="on-enter-item">
                    <span className="on-enter-label">Call Tool:</span>
                    <code className="on-enter-value">
                      {selectedState.on_enter.callTool.name}
                    </code>
                  </div>
                )}
              </div>
            )}

            {selectedState.state_tools && selectedState.state_tools.length > 0 && (
              <div className="detail-section">
                <h4>State Tools ({selectedState.state_tools.length})</h4>
                <div className="detail-list">
                  {selectedState.state_tools.map((toolName) => (
                    <div key={toolName} className="detail-list-item">
                      <code>{toolName}</code>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedState.transitions && selectedState.transitions.length > 0 && (
              <div className="detail-section">
                <h4>Transitions ({selectedState.transitions.length})</h4>
                <div className="transitions-list">
                  {selectedState.transitions.map((transition, idx) => (
                    <div key={idx} className="transition-item">
                      <span className="transition-trigger">{transition.trigger}</span>
                      <span className="transition-arrow">-&gt;</span>
                      <span className="transition-target">{transition.target}</span>
                      {transition.condition && (
                        <span className="transition-condition">
                          when: {transition.condition}
                        </span>
                      )}
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
