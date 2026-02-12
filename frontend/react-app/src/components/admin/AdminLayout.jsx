import VisualizePage from '../visualize/VisualizePage';

export default function AdminLayout() {
  return (
    <div className="admin-container">
      <div className="sidebar">
        <div className="sidebar-header">
          <h1>Felix Admin</h1>
        </div>
        <div className="sidebar-section-info">
          <p>Explore agent hierarchy, state machines, and tools in an interactive visualization.</p>
        </div>
      </div>
      <main className="main-content">
        <VisualizePage />
      </main>
    </div>
  );
}
