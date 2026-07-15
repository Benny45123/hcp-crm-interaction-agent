import { useState, useRef, useEffect, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendMessage, addUserMessage, clearHistory } from '../store/chatSlice';
import { setFields } from '../store/interactionSlice';

const SUGGESTIONS = [
  { icon: '🏥', text: 'Today I met with Dr. Smith and discussed product X efficacy. The sentiment was positive.' },
  { icon: '💊', text: 'Log interaction with Dr. Johnson — discussed new oncology trial results and shared brochures.' },
  { icon: '📅', text: 'Schedule a follow-up in 2 weeks to discuss trial enrollment.' },
  { icon: '⚠️', text: 'Check this note for compliance issues before finalizing.' },
];

function fmtTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function ChatPanel() {
  const [input, setInput] = useState('');
  const chat = useSelector((s) => s.chat);
  const form = useSelector((s) => s.interaction);
  const dispatch = useDispatch();
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, []);

  useEffect(() => { scrollToBottom(); }, [chat.messages.length, chat.isTyping, scrollToBottom]);

  useEffect(() => {
    const fields = chat._updatedFields;
    if (fields && Object.keys(fields).length > 0) dispatch(setFields(fields));
  }, [chat._updatedFields, dispatch]);

  const submit = useCallback((e) => {
    e?.preventDefault?.();
    const trimmed = input.trim();
    if (!trimmed) return;
    dispatch(addUserMessage(trimmed));
    dispatch(sendMessage({ message: trimmed, currentFormState: form }));
    setInput('');
    inputRef.current?.focus?.();
  }, [input, form, dispatch]);

  const onChipSend = useCallback((text) => {
    if (chat.isTyping) return;
    dispatch(addUserMessage(text));
    dispatch(sendMessage({ message: text, currentFormState: form }));
  }, [chat.isTyping, form, dispatch]);

  const handleFileSelect = useCallback((e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    const newAttachments = (chat._pendingAttachments || []).concat(
      files.map(f => ({ name: f.name, size: f.size, type: f.type }))
    );
    dispatch({ type: 'chat/setPendingAttachments', payload: newAttachments });
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, [chat._pendingAttachments, dispatch]);

  const removeAttachment = useCallback((index) => {
    const updated = (chat._pendingAttachments || []).filter((_, i) => i !== index);
    dispatch({ type: 'chat/setPendingAttachments', payload: updated });
  }, [chat._pendingAttachments, dispatch]);

  const handleSendWithFiles = useCallback(() => {
    const trimmed = input.trim();
    const pending = chat._pendingAttachments || [];
    if (!trimmed || !pending.length) return;
    const fileNotes = pending.map(f => {
      const size = (f.size / 1024).toFixed(1) + ' KB';
      return `[📎 Shared file: ${f.name} (${size})]`;
    }).join('\n');
    const fullMsg = `${trimmed}\n\n${fileNotes}`;
    dispatch(addUserMessage(fullMsg));
    dispatch(sendMessage({ message: fullMsg, currentFormState: form }));
    setInput('');
    dispatch({ type: 'chat/setPendingAttachments', payload: [] });
  }, [input, form, chat._pendingAttachments, dispatch]);

  const isEmpty = chat.messages.length === 0;
  const hasAttachments = (chat._pendingAttachments || []).length > 0;

  return (
    <div className="chat-panel">
      <div className="chat-panel-header">
        <h2>
          <span className="ai-avatar-icon">
            <span className="ai-avatar-grid" />
            <span className="ai-avatar-glow" />
          </span>
          <span className="ai-label-group">
            <span className="ai-label-main">AI Assistant</span>
            <span className="ai-label-sub">Powered by Groq</span>
          </span>
          <span className="status-indicator">
            <span className="status-dot-pulse" />
          </span>
        </h2>
        <div className="header-actions">
          <button className="attach-btn" onClick={() => fileInputRef.current?.click()}>
            <span className="btn-icon">📎</span>
            <span className="btn-label">Attach</span>
          </button>
          <button className="clear-btn" onClick={() => {
            dispatch(clearHistory());
            dispatch({ type: 'chat/setPendingAttachments', payload: [] });
          }}>
            <span className="btn-icon">🗑</span> Clear
          </button>
        </div>
        <input ref={fileInputRef} type="file" multiple className="file-input-hidden" onChange={handleFileSelect} />
      </div>

      {hasAttachments && (
        <div className="attachments-preview">
          {(chat._pendingAttachments || []).map((att, i) => (
            <div key={i} className="attachment-chip">
              <span className="attachment-icon">📄</span>
              <span className="attachment-info">
                <span className="attachment-name">{att.name}</span>
                <span className="attachment-size">{(att.size / 1024).toFixed(1)} KB</span>
              </span>
              <button className="attachment-remove" onClick={() => removeAttachment(i)}>×</button>
            </div>
          ))}
        </div>
      )}

      <div className="chat-messages scrollbar-thin" ref={scrollRef}>
        {isEmpty && (
          <div className="empty-chat">
            <div className="empty-icon-wrapper">
              <div className="empty-icon">🤖</div>
              <div className="empty-ring" />
              <div className="empty-ring-2" />
            </div>
            <h3>Your AI-Powered Assistant</h3>
            <p>Log interactions, manage attendees, attach brochures — all through natural conversation.</p>
            <div className="feature-pills">
              <span className="pill pill-purple">📋 Auto-log forms</span>
              <span className="pill pill-green">📎 Attach files</span>
              <span className="pill pill-yellow">👥 Manage participants</span>
              <span className="pill pill-blue">✅ Compliance check</span>
            </div>
            <div className="suggestion-chips">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="chip" onClick={() => onChipSend(s.text)}>
                  <span className="chip-emoji">{s.icon}</span>
                  <span>{s.text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {!isEmpty && chat.messages.map((m, i) => {
          if (m._transient) {
            return (
              <div key={'p' + i} className="typing-indicator">
                <div className="ai-mini-avatar"><span className="ai-mini-grid" /></div>
                <div className="typing-bubbles"><span /><span /><span /></div>
              </div>
            );
          }
          if (m.role === 'user') {
            return (
              <div key={'u' + i} className="msg-row msg-row-user">
                <div className="msg-bubble msg-user">
                  <div className="msg-text">{m.content}</div>
                  <div className="msg-meta">
                    <span className="msg-time">{fmtTime()}</span>
                    <span className="msg-tick">✓</span>
                  </div>
                </div>
              </div>
            );
          }
          if (m.role === 'assistant') {
            return (
              <div key={'a' + i} className="msg-row msg-row-assistant">
                <div className="ai-circle-avatar"><span className="ai-logo-icon">✨</span></div>
                <div className="msg-bubble msg-assistant">
                  <div className="msg-text">{m.content}</div>
                </div>
              </div>
            );
          }
          return null;
        })}

        {chat.isTyping && isEmpty && (
          <div className="typing-indicator">
            <div className="ai-mini-avatar"><span className="ai-mini-grid" /></div>
            <div className="typing-bubbles"><span /><span /><span /></div>
          </div>
        )}

        {chat.error && (
          <div className="error-card">
            <span className="error-icon">⚠️</span>
            {chat.error}
          </div>
        )}
      </div>

      <div className="chat-input-area">
        <div className="input-glow-bar" />
        <form className="chat-form" onSubmit={(e) => {
          e.preventDefault();
          if (hasAttachments) handleSendWithFiles();
          else submit(e);
        }}>
          <div className="input-wrapper">
            <input ref={inputRef} className="chat-input" type="text"
              placeholder="Describe your interaction…"
              value={input} onChange={(e) => setInput(e.target.value)}
              disabled={chat.isTyping} />
          </div>
          <button className="send-btn" type="submit"
            disabled={(!input.trim() && !hasAttachments) || chat.isTyping}>
            <span className="send-icon">➤</span>
          </button>
        </form>
      </div>
    </div>
  );
}
