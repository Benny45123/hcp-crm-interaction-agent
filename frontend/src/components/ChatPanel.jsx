import { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendMessage, setTyping, clearHistory } from '../store/chatSlice';
import { setFields } from '../store/interactionSlice';

export default function ChatPanel() {
  const [input, setInput] = useState('');
  const chat = useSelector((s) => s.chat);
  const form = useSelector((s) => s.interaction);
  const dispatch = useDispatch();
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chat.messages, chat.isTyping]);

  // When a new turn completes, propagate updated_fields to form slice
  useEffect(() => {
    if (chat._updatedFields && Object.keys(chat._updatedFields).length > 0) {
      dispatch(setFields(chat._updatedFields));
    }
  }, [chat._updatedFields, dispatch]);

  const submit = (e) => {
    e.preventDefault();
    if (!input.trim() || chat.isTyping) return;
    dispatch(sendMessage({ message: input.trim(), currentFormState: form }));
    setInput('');
  };

  return (
    <div className="chat-panel">
      <div className="chat-panel-header">
        <h2>
          <span className="status-dot" />
          AI Assistant
        </h2>
        <button
          onClick={() => dispatch(clearHistory())}
          style={{
            background: 'transparent',
            border: '1px solid #e2e8f0',
            borderRadius: 8,
            padding: '5px 12px',
            fontSize: 12,
            cursor: 'pointer',
            fontFamily: 'Inter, sans-serif',
          }}
        >
          Clear chat
        </button>
      </div>

      <div className="chat-messages scrollbar-thin" ref={scrollRef}>
        {chat.messages.length === 0 && (
          <div className="msg-system" style={{ marginTop: 40, textAlign: 'center' }}>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 6 }}>
              Hi! I&apos;m your HCP interaction assistant.
            </p>
            <p style={{ fontSize: 13, color: '#94a3b8' }}>
              Tell me about your visit and I&apos;ll log everything for you.
            </p>
            <div
              style={{
                marginTop: 24,
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
                alignItems: 'flex-start',
              }}
            >
              {[
                'Today I met with Dr. Smith and discussed product X efficacy. The sentiment was positive and I shared the brochures.',
                "What did we last discuss with Dr. Smith?",
                "Schedule a follow-up in 2 weeks to discuss trial results.",
                'Check this note for compliance issues.',
              ].map((s, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInput(s);
                    inputRef.current?.focus?.();
                  }}
                  style={{
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderRadius: 12,
                    padding: '8px 14px',
                    fontSize: 13,
                    fontFamily: 'Inter, sans-serif',
                    textAlign: 'left',
                    cursor: 'pointer',
                    maxWidth: '88%',
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {chat.messages.map((m, i) => (
          <div key={i} className={'msg-bubble msg-' + m.role}>
            {m.content}
          </div>
        ))}

        {chat.isTyping && (
          <div className="msg-bubble msg-assistant">
            <div className="typing-indicator">
              <span /><span /><span />
            </div>
          </div>
        )}

        {chat.error && (
          <div className="msg-system" style={{ color: '#dc2626' }}>
            Error: {chat.error}
          </div>
        )}
      </div>

      <form className="chat-input-area" onSubmit={submit}>
        <input
          ref={inputRef}
          className="chat-input"
          type="text"
          placeholder="Type here… e.g. 'Met with Dr. Smith, discussed Product X…'"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={chat.isTyping}
        />
        <button className="send-btn" type="submit" disabled={!input.trim() || chat.isTyping}>
          Send
        </button>
      </form>
    </div>
  );
}
