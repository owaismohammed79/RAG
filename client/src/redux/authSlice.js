import { createSlice } from "@reduxjs/toolkit";

const initialState = {
    status: false,
    userData: null,
    jwt: null
}

const authSlice = createSlice({
    name: "auth",
    initialState,
    reducers: {
        login: (state, action) => {
            state.status = true;
            state.userData = action.payload.userData;
            state.jwt = action.payload.jwt;
        },
        logout: (state) => {
            state.status = false;
            state.userData = null;
            state.jwt = null;
        }
    }
})

export const {login, logout} = authSlice.actions;

export default authSlice.reducer