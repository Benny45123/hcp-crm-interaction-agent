import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ message, currentFormState }) => {
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, current_form_state: currentFormState }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${res.status}`);
      }
      const data = await res.json();
      return data;
    } catch (e) {
      throw new Error(e.message);
    }
  }
);

const initialState = {
  messages: [],
  isTyping: false,
  error: null,
  _updatedFields: {},
  _pendingAttachments: [],
  _complianceFlag: null,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    clearHistory(state) { state.messages = []; },
    addUserMessage(state, action) {
      state.messages = [...state.messages, { role: 'user', content: action.payload }];
    },
    setTyping(state, action) { state.isTyping = action.payload; },
    setPendingAttachments(state, action) { state._pendingAttachments = action.payload; },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.messages = [...state.messages, { role: 'assistant', content: '', _transient: true }];
        state.isTyping = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.isTyping = false;
        state.messages = state.messages.map((m, i) =>
          i === state.messages.length - 1 && m._transient
            ? { role: 'assistant', content: action.payload.assistant_reply }
            : m
        );
        state._updatedFields = action.payload.updated_fields || {};
        state._complianceFlag = action.payload.compliance_flag || null;
        state._pendingAttachments = [];
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isTyping = false;
        state.messages = state.messages.filter((m) => !m._transient);
        state.error = action.error?.message || 'Something went wrong';
      });
  },
});

export const { clearHistory, addUserMessage, setTyping, setPendingAttachments } = chatSlice.actions;
export default chatSlice.reducer;
