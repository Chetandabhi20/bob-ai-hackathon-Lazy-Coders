import { useState } from 'react';
import { sendChat } from '../api';

export default function ChatPanel() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Hello! I\'m Grid Guardian AI. Ask me about grid risks, asset health, or crew deployment. Try: "What needs attention right now?"',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setInput('');
    setLoading(true);

    try {
      const result = await sendChat(5);
      const brief = result.brief || 'No response generated.';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: brief,
          meta: {
            assets: result.total_assets_assessed,
            crews: result.crew_assignments,
          },
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${e.message}`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="panel chat-panel">
      <h2>Grid Guardian AI</h2>
      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role} ${m.error ? 'error' : ''}`}>
            <div className="msg-content">{m.content}</div>
            {m.meta && (
              <div className="msg-meta">
                {m.meta.assets} assets assessed · {m.meta.crews} crews deployed
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="chat-msg assistant loading-msg">
            <div className="msg-content">Analyzing grid data...</div>
          </div>
        )}
      </div>
      <div className="chat-input-row">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about grid risks, assets, or crew deployment..."
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading || !input.trim()}>
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
