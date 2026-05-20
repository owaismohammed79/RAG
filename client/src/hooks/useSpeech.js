import { useState, useEffect, useRef } from "react"

export function useSpeech(onResult) {
  const [isListening, setIsListening] = useState(false)
  const [browserSupport, setBrowserSupport] = useState({ supported: true, message: "" })
  const recognitionRef = useRef(null)

  useEffect(() => {
    const SpeechRecognition = globalThis.SpeechRecognition || globalThis.webkitSpeechRecognition
    if(!SpeechRecognition) {
      setBrowserSupport({ supported: false, message: "Speech recognition not supported in this browser." })
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((r) => r[0])
        .map((r) => r.transcript)
        .join("");
      onResult(transcript)
    }
    
    recognition.onstart = () => setIsListening(true)
    recognition.onend = () => setIsListening(false)
    
    recognitionRef.current = recognition

    return () => {
      if(recognitionRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [onResult])

  const handleMicClick = () => {
    if(!browserSupport.supported || !recognitionRef.current) return
    isListening ? recognitionRef.current.stop() : recognitionRef.current.start()
  }

  return { isListening, browserSupport, handleMicClick }
}