import { useEffect, useState } from 'react';
import { useVisualizeStore } from '../../store/visualizeStore';
import HierarchyDiagram from './HierarchyDiagram';
import StateMachineDiagram from './StateMachineDiagram';
import ToolCatalog from './ToolCatalog';
import ConversationReview from './ConversationReview';
import { adminApi } from '../../services/adminApi';
import '../../styles/visualize.css';

export default function VisualizePage() {
  const loadAgents = useVisualizeStore((state) => state.loadAgents);
  const isLoading = useVisualizeStore((state) => state.isLoading);
  const error = useVisualizeStore((state) => state.error);
  const activeView = useVisualizeStore((state) => state.activeView);
  const setActiveView = useVisualizeStore((state) => state.setActiveView);
  const [reloadState, setReloadState] = useState('idle');

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  if (isLoading) {
    return (
      <div className="visualize-page">
        <div className="loading">Loading agent data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="visualize-page">
        <div className="error-state">
          <h2>Error loading data</h2>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={loadAgents}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  const reloadConfigs = async () => {
    setReloadState('loading');
    try {
      await adminApi.reloadConfig();
      await loadAgents();
      setReloadState('done');
    } catch (err) {
      console.error(err);
      setReloadState('error');
    }
  };

  return (
    <div className="visualize-page">
      <div className="visualize-header">
        <h2>Agent Visualization</h2>
        <p className="visualize-description">
          Explore the agent architecture, state machines, and tools
        </p>
        <div className="visualize-actions">
          <button className="btn btn-primary" onClick={reloadConfigs}>
            Reload Config
          </button>
          {reloadState === 'loading' && <span>Reloading...</span>}
          {reloadState === 'done' && <span>Reloaded</span>}
          {reloadState === 'error' && <span>Reload failed</span>}
        </div>
      </div>

      <div className="visualize-tabs">
        <button
          className={`visualize-tab ${activeView === 'hierarchy' ? 'active' : ''}`}
          onClick={() => setActiveView('hierarchy')}
        >
          Agent Hierarchy
        </button>
        <button
          className={`visualize-tab ${activeView === 'flows' ? 'active' : ''}`}
          onClick={() => setActiveView('flows')}
        >
          State Machines
        </button>
        <button
          className={`visualize-tab ${activeView === 'tools' ? 'active' : ''}`}
          onClick={() => setActiveView('tools')}
        >
          Tool Catalog
        </button>
        <button
          className={`visualize-tab ${activeView === 'conversations' ? 'active' : ''}`}
          onClick={() => setActiveView('conversations')}
        >
          Conversations
        </button>
      </div>

      <div className="visualize-content">
        {activeView === 'hierarchy' && <HierarchyDiagram />}
        {activeView === 'flows' && <StateMachineDiagram />}
        {activeView === 'tools' && <ToolCatalog />}
        {activeView === 'conversations' && <ConversationReview />}
      </div>
    </div>
  );
}
