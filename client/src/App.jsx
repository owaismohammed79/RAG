import LandingPg from "./pages/LandingPg"
import Signup from "./components/Signup"
import { BrowserRouter, Routes, Route } from "react-router-dom"
import ChatInterface from "./components/ChatInterface"


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPg />} />
        <Route path="/login" element={<Signup variable={"Log in"}/>} />
        <Route path="/signup" element={<Signup variable={"Sign up"}/>} />
        <Route path="/chat" element={<ChatInterface />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
