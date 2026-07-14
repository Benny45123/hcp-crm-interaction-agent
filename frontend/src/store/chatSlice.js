import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ message, currentFormState }, { rejectWithValue }) => {
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, current_form_state: currentFormState }),
      });
      if (!res.ok) return rejectWithValue('Request failed');
      const data = await res.json();
      return data;
    } catch (e) {
      return rejectWithValue(e.message);
    }
  }
);

const initialState = {
  messages: [],
  isTyping: false,
  error: null,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    clearHistory(state) { state.messages = []; },
    setTyping(state, action) { state.isTyping = action.payload; },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.messages = [...state.messages, { role: 'user', content: state._pending || '' }];
        state.isTyping = true;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.isTyping = false;
        const p = action.payload;
        state.messages = [...state.messages, { role: 'assistant', content: p.assistant_reply }];
        state._updatedFields = p.updated_fields || {};
        state._complianceFlag = p.compliance_flag || null;
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isTyping = false;
        state.error = action.payload || 'Something went wrong';
      });
  },
});

export const { clearHistory, setTyping } = chatSlice.actions;
export default chatSlice.reducer;
