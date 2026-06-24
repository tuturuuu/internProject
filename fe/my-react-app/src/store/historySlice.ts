import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";

type HistoryState = {
  visited: string[];
};

const initialState: HistoryState = {
  visited: [],
};

const historySlice = createSlice({
  name: "history",
  initialState,
  reducers: {
    addVisited(state, action: PayloadAction<string>) {
      if (!state.visited.includes(action.payload)) {
        state.visited.push(action.payload);
      }
    },
    removeVisited(state, action: PayloadAction<string>) {
      state.visited = state.visited.filter((id) => id !== action.payload);
    },
    toggleVisited(state, action: PayloadAction<string>) {
      if (state.visited.includes(action.payload)) {
        state.visited = state.visited.filter((id) => id !== action.payload);
      } else {
        state.visited.push(action.payload);
      }
    },
    clearHistory(state) {
      state.visited = [];
    },
    setVisited(state, action: PayloadAction<string[]>) {
      state.visited = action.payload;
    },
  },
});

export const { addVisited, removeVisited, toggleVisited, clearHistory, setVisited } = historySlice.actions;
export default historySlice.reducer;
