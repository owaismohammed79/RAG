import {configureStore} from '@reduxjs/toolkit'
import authSlice from './authSlice'
import convoSlice from './convoSlice'

const store = configureStore({
    reducer: {
        auth: authSlice,
        conversation: convoSlice
    }
})

export default store