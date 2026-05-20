import { useState, useRef, useEffect } from "react"
import { useDispatch } from "react-redux"
import { addMessage, setConversationId, fetchConversations } from "../redux/convoSlice"
import { apiFetch } from "../utils/apiClient"

export function useChat(jwt, activeConversationId, messages) {
  const dispatch = useDispatch()
  const [isLoading, setIsLoading] = useState(false)
  const [streamingResponse, setStreamingResponse] = useState("")
  const [promptsRemaining, setPromptsRemaining] = useState(null)
  const [maxPrompts, setMaxPrompts] = useState(10)
  
  const abortControllerRef = useRef(null)

  useEffect(() => {
    if (!jwt) return
    const controller = new AbortController()

    const fetchLimit = async () => {
      try {
        const response = await apiFetch('/api/user/prompt-limit', { signal: controller.signal })
        if (response.ok) {
          const data = await response.json()
          setPromptsRemaining(data.promptsRemaining)
          setMaxPrompts(data.maxPrompts)
        }
      } catch (error) {
        if (error.name !== "AbortError") console.error("Prompt limit error:", error)
      }
    };

    fetchLimit()
    
    return () => controller.abort()
  }, [jwt])

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, []);

  const submitChat = async (input, files, callbacks) => {
    if (promptsRemaining !== null && promptsRemaining <= 0) {
      dispatch(addMessage({ type: "bot", content: "Daily prompt limit reached." }));
      return;
    }

    setIsLoading(true);
    dispatch(addMessage({ type: "user", content: input }));
    callbacks.onClearInput(); 
    setStreamingResponse("");

    try {
      if (abortControllerRef.current) abortControllerRef.current.abort();
      abortControllerRef.current = new AbortController();
      const signal = abortControllerRef.current.signal;

      let targetConversationId = activeConversationId;

      //upload and poll
      if (files.length > 0) {
        const uploadFormData = new FormData();
        files.forEach((file) => uploadFormData.append("file", file));
        uploadFormData.append("prompt", input); 
        uploadFormData.append("conversationId", targetConversationId || "null");

        const uploadRes = await apiFetch(`/api/documents/upload`, {
          method: "POST",
          body: uploadFormData,
          signal
        });
        
        if (!uploadRes.ok) throw new Error("File upload failed");
        targetConversationId = (await uploadRes.json()).conversationId;

        let isReady = false;
        while (!isReady) {
          await new Promise(r => setTimeout(r, 2000))
          if(signal.aborted) return
          
          const statusRes = await apiFetch(`/api/documents/status?conversationId=${targetConversationId}`, { signal })
          if(statusRes.ok) {
            const statusData = await statusRes.json();
            if (statusData.failed > 0) throw new Error("Backend failed to process document.");
            if (statusData.ready) isReady = true;
          }
        }
      }

      // chat & Stream
      const chatFormData = new FormData()
      chatFormData.append("prompt", input)
      chatFormData.append("conversationId", targetConversationId || "null")
      chatFormData.append("history", JSON.stringify(messages.slice(-10)))

      const chatRes = await apiFetch(`/api/prompt/text-file`, { method: "POST", body: chatFormData, signal })
      if (!chatRes.ok) throw new Error("Chat request failed")

      const reader = chatRes.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      let finalBotText = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const data = JSON.parse(line)
            switch (data.type) {
              case 'rag_chunk':
              case 'fallback_chunk':
                setStreamingResponse(prev => prev + data.content)
                finalBotText += data.content
                break
              case 'fallback_start':
                setStreamingResponse(data.content)
                finalBotText = data.content
                break
              case "metadata":
                if (!activeConversationId) {
                  dispatch(setConversationId(data.conversationId))
                  dispatch(fetchConversations(jwt))
                }
                if (data.promptsRemaining !== undefined) setPromptsRemaining(data.promptsRemaining)
                break
              case "error":
                finalBotText += `\n\nError: ${data.content}`;
                break
            }
          } catch (e) {
            console.error("Parse error:", e);
          }
        }
      }

      if (finalBotText.trim()) dispatch(addMessage({ type: "bot", content: finalBotText }))
      setStreamingResponse("")

    } catch (error) {
      if(error.name === 'AbortError') return
      
      if (error.message === "AUTH_FAILED") {
        callbacks.onAuthFailure()
        return
      }
      callbacks.onRestoreInput(input, files)
      dispatch(addMessage({ type: "bot", content: `Error: ${error.message}` }))
      setStreamingResponse("")
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }

  return { submitChat, isLoading, streamingResponse, promptsRemaining, maxPrompts }
}