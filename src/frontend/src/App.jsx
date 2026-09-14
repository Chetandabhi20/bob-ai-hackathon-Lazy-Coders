import { useState } from 'react';
import GridMap from './components/GridMap';
import AssetList from './components/AssetList';
import CrewPlan from './components/CrewPlan';
import ChatPanel from './components/ChatPanel';
import './App.css';

function App() {
  const [selectedAssetId, setSelectedAssetId] = useState(null);
  const [activeTab, setActiveTab] = useState('grid');

  return (
    <div className="app">
      <header className="app-header">
        <h1>⚡ Grid Guardian</h1>
        <span className="subtitle">
          AI-Powered Grid Risk Assessment &amp; Crew Deployment
        </span>
      </header>

      <nav className="tab-bar">
        {[
          { id: 'grid', label: 'Grid Map' },
          { id: 'assets', label: 'Risk Assets' },
          { id: 'crew', label: 'Crew Plan' },
          { id: 'chat', label: 'AI Chat' },
        ].map((tab) => (
          <button
            key={tab.id}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="main-content">
        {activeTab === 'grid' && (
          <div className="grid-layout">
            <GridMap
              onSelectAsset={setSelectedAssetId}
              selectedAssetId={selectedAssetId}
            />
            <AssetList
              selectedAssetId={selectedAssetId}
              onSelectAsset={setSelectedAssetId}
            />
          </div>
        )}
        {activeTab === 'assets' && (
          <AssetList
            selectedAssetId={selectedAssetId}
            onSelectAsset={setSelectedAssetId}
          />
        )}
        {activeTab === 'crew' && <CrewPlan />}
        {activeTab === 'chat' && <ChatPanel />}
      </main>

      <footer className="app-footer">
        Grid Guardian — IBM Bob AI Hackathon 2026 | Lazy Coders
      </footer>
    </div>
  );
}

export default App;
