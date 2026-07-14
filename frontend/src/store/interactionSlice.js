import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  hcp_name: '',
  interaction_date: '',
  sentiment: '',
  products_discussed: '',
  materials_shared: '',
  notes: '',
  follow_up_date: '',
  follow_up_action: '',
  compliance_flag: '',
};

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    setFields(state, action) {
      Object.assign(state, action.payload);
    },
    resetForm(state) {
      Object.assign(state, initialState);
    },
  },
});

export const { setFields, resetForm } = interactionSlice.actions;
export default interactionSlice.reducer;
