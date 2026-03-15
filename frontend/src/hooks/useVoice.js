import { useState, useRef, useCallback, useEffect } from "react"

const SpeechRecognition =
  typeof window !== "undefined"
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null

export function useVoice({ onResult } = {}) {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState("")
  const [interimTranscript, setInterimTranscript] = useState("")
  const recognitionRef = useRef(null)
  const isSupported = !!SpeechRecognition

  useEffect(() => {
    if (!SpeechRecognition) return

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = "en-US"

    recognition.onresult = (e) => {
      let interim = ""
      let final = ""
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript
        if (e.results[i].isFinal) {
          final += t
        } else {
          interim += t
        }
      }
      setInterimTranscript(interim)
      if (final) {
        setTranscript(final)
        setInterimTranscript("")
        onResult?.(final)
      }
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognition.onerror = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition

    return () => {
      recognition.abort()
    }
  }, [onResult])

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return
    setTranscript("")
    setInterimTranscript("")
    try {
      recognitionRef.current.start()
      setIsListening(true)
    } catch {
      // already started
    }
  }, [])

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop()
    setIsListening(false)
  }, [])

  return {
    isListening,
    transcript,
    interimTranscript,
    startListening,
    stopListening,
    isSupported,
  }
}
