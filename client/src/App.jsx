import LandingPg from "./pages/LandingPg"
import Signup from "./components/Signup"
import { BrowserRouter, Routes, Route } from "react-router-dom"
import ChatInterface from "./components/ChatInterface"
import PrivacyPolicy from "./components/PrivacyPolicy"
import AuthCallback from "./components/AuthCallback"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPg />} />
        <Route path="/login" element={<Signup variable={"Log in"}/>} />
        <Route path="/signup" element={<Signup variable={"Sign up"}/>} />
        <Route path="/auth-callback" element={<AuthCallback />} />
        <Route path="/chat" element={<ChatInterface />} />
        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
