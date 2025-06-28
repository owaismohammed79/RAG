import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

const initialState = {
    status: 'idle',
    conversations: [
        {
            title: "User's query related to chat GPT?",
            messages: [
                {
                    sender: "username",
                    msg: "What is chat GPT?"
                },
                {
                    sender: "bot",
                    msg: "yada yada"
                }
            ]
        },{}
    ], //The issue here is how would I identify individual chats otherwise I might have to search the whole array of array of objects and then have to go through that array of messages for the particular conversation, help me out
    error: null
} 

const fetchConvoByUserId = createAsyncThunk(
    "conversation/fetchConvoByUserId", async(userId, {rejectWithValue}) => {
        try {
            await fetch(`https://baigan.com/${userId}`).then((response) => {
                return response.data
            })
        } catch (error) {
            console.log(`Error in loading conversations: ${error}`)
            return rejectWithValue(error.message || error.response.data) //This is used to send this thunk to the rejected action, so there are 3 states for this thunk, pending, fulfilled, rejected. This is usefull if you want to show the complete error details in the UI using the state's error, like if you simply throw the error, then the state has the whole error object, but in the rejectWithValue you can send only the required details from the error object
        }
})

const convoSlice = createSlice({
    name: "conversation",
    initialState,
    reducers: {
        loadConvo: (state, action) => {

        }
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchConvoByUserId.pending, (state) => {
                state.status = 'loading'
            }) 
            .addCase(fetchConvoByUserId.fulfilled, (state, action) => {
                state.status = 'succeeded'
                state.conversations = action.payload
            })
            .addCase(fetchConvoByUserId.rejected, (state, action) => {
                state.status = 'failed';
                state.error = action.payload
            })
    }
})
 
export const {loadConvo} = convoSlice.actions //Object destructuring of the actions object and take out only loadConvo
export default convoSlice.reducer;//This is for the store to say that this slice reducer can edit slice states in you
