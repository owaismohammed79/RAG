import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { conf } from "../config/conf";

const initialState = {
    status: 'idle',
    conversations: [],
    activeConversationId: null,
    messages: [],
    error: null
}

export const fetchConversations = createAsyncThunk(
    "conversation/fetchConversations",
    async (jwt, { rejectWithValue }) => {
        try {
            const response = await fetch(`${conf.BaseUrl}/api/conversations`, {
                headers: { 'Authorization': `Bearer ${jwt}` }
            });
            if (!response.ok) {
                throw new Error('Failed to fetch conversations');
            }
            const data = await response.json();
            return data;
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

export const fetchMessages = createAsyncThunk(
    "conversation/fetchMessages",
    async ({ conversationId, jwt }, { rejectWithValue }) => {
        try {
            const response = await fetch(`${conf.BaseUrl}/api/conversations/${conversationId}`, {
                headers: { 'Authorization': `Bearer ${jwt}` }
            });
            if (!response.ok) {
                throw new Error('Failed to fetch messages');
            }
            const data = await response.json();
            return data;
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

export const deleteConversation = createAsyncThunk(
    "conversation/deleteConversation",
    async ({ conversationId, jwt }, { rejectWithValue, dispatch }) => {
        try {
            const response = await fetch(`${conf.BaseUrl}/api/conversations/${conversationId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${jwt}` }
            });
            if (!response.ok) {
                throw new Error('Failed to delete conversation');
            }
            // After successful deletion, re-fetch conversations to update the sidebar
            dispatch(fetchConversations(jwt));
            return conversationId;
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

const convoSlice = createSlice({
    name: "conversation",
    initialState,
    reducers: {
        setActiveConversation: (state, action) => {
            state.activeConversationId = action.payload;
            state.messages = []; //Remember to clear messages when switching conversations
        },
        addMessage: (state, action) => {
            state.messages.push(action.payload);
        },
        setConversationId: (state, action) => {
            state.activeConversationId = action.payload;
        },
        startNewChat: (state) => {
            state.activeConversationId = null;
            state.messages = [];
        }
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchConversations.pending, (state) => {
                state.status = 'loading';
            })
            .addCase(fetchConversations.fulfilled, (state, action) => {
                state.status = 'succeeded';
                state.conversations = action.payload;
            })
            .addCase(fetchConversations.rejected, (state, action) => {
                state.status = 'failed';
                state.error = action.payload;
            })
            .addCase(fetchMessages.pending, (state) => {
                state.status = 'loading';
            })
            .addCase(fetchMessages.fulfilled, (state, action) => {
                state.status = 'succeeded';
                state.messages = action.payload.map(msg => ({
                    type: msg.senderType,
                    content: msg.content
                }));
            })
            .addCase(fetchMessages.rejected, (state, action) => {
                state.status = 'failed';
                state.error = action.payload;
            })
            .addCase(deleteConversation.fulfilled, (state, action) => {
                state.status = 'succeeded';
                //remove the deleted conversation from the state
                state.conversations = state.conversations.filter(
                    (convo) => convo.$id !== action.payload
                );
                //if the active conversation was deleted, clear it
                if (state.activeConversationId === action.payload) {
                    state.activeConversationId = null;
                    state.messages = [];
                }
            })
            .addCase(deleteConversation.rejected, (state, action) => {
                state.status = 'failed';
                state.error = action.payload;
            });
    }
})

export const { setActiveConversation, addMessage, setConversationId, startNewChat } = convoSlice.actions;
export default convoSlice.reducer;