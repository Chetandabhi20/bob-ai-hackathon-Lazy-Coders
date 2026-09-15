import { useState, useRef, useEffect } from 'react';
import { sendChat } from '../api';

/** Convert the simple markdown subset used by the backend into HTML spans. */
function renderMarkdown(text) {
  // Bold: **text**
  let html = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Italic: _text_
  html = html.replace(/_(.+?)_/g, '<em>$1</em>');
  // Bullet lines starting with "- "
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
  // Line breaks
  html = html.replace(/\n/g, '<br/>');
  return html;
}

/** Badge label for each intent type */
const INTENT_LABELS = {
  asset_health: '🔍 Asset Health',
  weather: '🌩️ Weather Risk',
  crew_plan: '🚗 Crew Plan',
  incident_brief: '📋 Incident Brief',
};

/** Suggested starter queries shown below the input */
const SUGGESTIONS = [
  'What needs attention right now?',
  'Show me the health of TX-001',
  'What is the weather risk?',
  'Show me the crew deployment plan',
  'Health of SUB-002',
  'Any storms coming?',
];

export default function ChatPanel() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        '**Grid Guardian AI** is ready.\n\nAsk me anything about the grid:\n- "What needs attention right now?"\n- "Show me the health of TX-001"\n- "What is the weather risk?"\n- "Show the crew deployment plan"',
      intent: null,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function handleSend(text) {
    const query = (text || input).trim();
    if (!query || loading) return;

    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    setInput('');
    setLoading(true);

    try {
      const result = await sendChat(query);
      const brief = result.brief || result.error || 'No response generated.';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: brief,
          intent: result.intent || null,
          meta: buildMeta(result),
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `**Error:** ${e.message}`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function buildMeta(result) {
    const parts = [];
    if (result.total_assets_assessed != null)
      parts.push(`${result.total_assets_assessed} assets assessed`);
    if (result.crew_assignments != null)
      parts.push(`${result.crew_assignments} crews deployed`);
    if (result.asset_id)
      parts.push(`Asset: ${result.asset_id}`);
    return parts.length ? parts.join(' · ') : null;
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
            {/* Intent badge (assistant messages only) */}
            {m.role === 'assistant' && m.intent && (
              <span className="intent-badge">
                {INTENT_LABELS[m.intent] || m.intent}
              </span>
            )}
            <div
              className="msg-content"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(m.content) }}
            />
            {m.meta && <div className="msg-meta">{m.meta}</div>}
          </div>
        ))}

        {loading && (
          <div className="chat-msg assistant loading-msg">
            <div className="msg-content">Analyzing grid data…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggestion chips — shown only when there is just the welcome message */}
      {messages.length === 1 && (
        <div className="chat-suggestions">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              className="suggestion-chip"
              onClick={() => handleSend(s)}
              disabled={loading}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="chat-input-row">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder='Ask: "TX-001 health", "weather risk", "crew plan"…'
          disabled={loading}
        />
        <button onClick={() => handleSend()} disabled={loading || !input.trim()}>
          {loading ? '…' : 'Send'}
        </button>
      </div>
    </div>
  );
}
