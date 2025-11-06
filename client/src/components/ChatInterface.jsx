import { useState, useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  Mic,
  Send,
  Upload,
  MenuIcon,
  AlertCircle,
  X,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
  SheetClose,
} from "@/components/ui/sheet";
import { useNavigate } from "react-router-dom";
import { Alert, AlertDescription } from "@/components/ui/alert";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { dracula } from "react-syntax-highlighter/dist/esm/styles/prism";
import authService from "../appwrite(service)/auth";
import {
  addMessage,
  setConversationId,
  fetchConversations,
} from "../redux/convoSlice";
import { login as reduxLogin, logout as reduxLogout } from "../redux/authSlice";
import ConversationHistory from "./ConversationHistory";
import ProcessingAnimation from "./ProcessingAnimation";
import { conf } from "../config/conf";

const SidebarContent = ({ jwt }) => <ConversationHistory jwt={jwt} />;

export default function ChatInterface() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const { userData, jwt } = useSelector((state) => state.auth);
  const { activeConversationId, messages } = useSelector(
    (state) => state.conversation
  );
  const [input, setInput] = useState("");
  const [streamingResponse, setStreamingResponse] = useState("");
  const [files, setFiles] = useState([]);
  const fileInputRef = useRef(null);
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);

  const [isListening, setIsListening] = useState(false);
  const micRef = useRef(null);
  const [recognition, setRecognition] = useState(null);
  const [browserSupport, setBrowserSupport] = useState({
    supported: true,
    message: "",
  });
  const [promptsRemaining, setPromptsRemaining] = useState(null);
  const [maxPrompts, setMaxPrompts] = useState(10);
  const isSendDisabled =
    isLoading || (promptsRemaining !== null && promptsRemaining <= 0);

  useEffect(() => {
    const fetchPromptLimit = async () => {
      if (!jwt) return;
      try {
        const response = await fetch(
          `${conf.BackendURL}/api/user/prompt-limit`,
          {
            headers: { Authorization: `Bearer ${jwt}` },
          }
        );
        if (response.ok) {
          const data = await response.json();
          setPromptsRemaining(data.promptsRemaining);
          setMaxPrompts(data.maxPrompts);
        } else {
          console.error("Failed to fetch prompt limit:", await response.json());
        }
      } catch (error) {
        console.error("Error fetching prompt limit:", error);
      }
    };
    fetchPromptLimit();
  }, [jwt]);

  useEffect(() => {
    const checkUserAndJWT = async () => {
      if (userData && jwt) {
        return;
      }

      try {
        const currentUser = await authService.getCurrentUser();
        if (currentUser) {
          const token = await authService.getJWT();
          dispatch(reduxLogin({ userData: currentUser, jwt: token.jwt }));
          localStorage.setItem("userData", JSON.stringify(currentUser));
        } else {
          console.log("No active Appwrite session");
          dispatch(reduxLogout());
          localStorage.clear();
          navigate("/login");
        }
      } catch (error) {
        console.error("Authentication check failed:", error);
        dispatch(reduxLogout());
        localStorage.removeItem("userData");
        navigate("/login");
      }
    };
    checkUserAndJWT();
  }, [dispatch, navigate, userData, jwt]);

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setBrowserSupport({
        supported: false,
        message: "Speech recognition not supported in this browser.",
      });
      return;
    }
    const recognitionInstance = new SpeechRecognition();
    recognitionInstance.continuous = true;
    recognitionInstance.interimResults = true;
    recognitionInstance.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((r) => r[0])
        .map((r) => r.transcript)
        .join("");
      setInput(transcript);
    };
    recognitionInstance.onstart = () => setIsListening(true);
    recognitionInstance.onend = () => setIsListening(false);
    setRecognition(recognitionInstance);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingResponse]);

  //refetch conversations when a new one is created
  useEffect(() => {
    if (jwt && activeConversationId) {
      dispatch(fetchConversations(jwt));
    }
  }, [activeConversationId, dispatch, jwt]);

  const handleMicClick = () => {
    if (!browserSupport.supported || !recognition) return;
    isListening ? recognition.stop() : recognition.start();
  };

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files);
    if (
      selectedFiles.some(
        (file) => file.type !== "application/pdf" || file.size > 5 * 1024 * 1024
      )
    ) {
      alert("Please select only PDF files under 5 MB.");
      return;
    }
    if (selectedFiles.length > 2) {
      alert("Please select a maximum of 2 files.");
      return;
    }
    setFiles(selectedFiles);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (input.trim() === "" || !jwt) return;
    if (promptsRemaining !== null && promptsRemaining <= 0) {
      dispatch(
        addMessage({
          type: "bot",
          content: `You have reached your daily prompt limit of ${maxPrompts}. Please try again tomorrow.`,
        })
      );
      return;
    }

    setIsLoading(true);
    const userMessage = { type: "user", content: input };
    dispatch(addMessage(userMessage));

    const formData = new FormData();
    files.forEach((file) => formData.append("file", file));
    formData.append("prompt", input);
    formData.append("conversationId", activeConversationId || "null");

    //sliding window of last 5 pairs (10 messages)
    const history = messages.slice(-10);
    formData.append("history", JSON.stringify(history));

    setInput("");
    setFiles([]); //clear files after submission
    setStreamingResponse("");

    try {
      const res = await fetch(`${conf.BackendURL}/api/prompt/text-file`, {
        method: "POST",
        body: formData,
        headers: { Authorization: `Bearer ${jwt}` },
      });

      if (!res.ok) {
        const data = await res.json();
        if (res.status === 429) {
          dispatch(addMessage({ type: "bot", content: data.error }));
          setPromptsRemaining(0);
        } else {
          throw new Error(data.error || "API request failed");
        }
        setIsLoading(false);
        return;
      }

      // Streaming logic
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalBotText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (line.trim() === "") continue;

          try {
            const data = JSON.parse(line);

            // This handles the different JSON events
            switch (data.type) {
              case "rag_chunk":
                setStreamingResponse((prev) => prev + data.content);
                finalBotText += data.content;
                break;

              case "fallback_start":
                setStreamingResponse("");
                finalBotText = "";
                break;

              case "fallback_chunk":
                setStreamingResponse((prev) => prev + data.content);
                finalBotText += data.content;
                break;

              case "metadata":
                if (!activeConversationId) {
                  dispatch(setConversationId(data.conversationId));
                  dispatch(fetchConversations(jwt));
                }
                setPromptsRemaining(data.promptsRemaining);
                break;

              case "error":
                finalBotText += `\n\nSorry, an error occurred: ${data.content}`;
                break;
            }
          } catch (error) {
            console.error("Failed to parse JSON line:", line, error);
          }
        }
      }

      // Streaming is done, add the complete message to Redux
      if (finalBotText.trim()) {
        dispatch(addMessage({ type: "bot", content: finalBotText }));
      }
      setStreamingResponse("");
    } catch (error) {
      console.error("Error fetching streaming response:", error);
      dispatch(
        addMessage({
          type: "bot",
          content: `Sorry, an error occurred: ${error.message}`,
        })
      );
      setStreamingResponse("");
    }
    setIsLoading(false);
  };

  const handleLogout = async () => {
    try {
      await authService.logout();
      dispatch(reduxLogout());
      localStorage.removeItem("userData");
      navigate("/login");
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return (
    <div className="flex h-[100dvh] bg-[#0a1a1f] text-white">
      <div className="hidden md:flex md:flex-shrink-0">
        <div className="flex flex-col w-64 border-r border-cyan-950">
          <SidebarContent jwt={jwt} />
        </div>
      </div>

      <div className="flex flex-col flex-1 w-full">
        <header className="flex items-center justify-between p-2 border-b border-cyan-950 md:hidden">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon">
                <MenuIcon className="w-6 h-6 text-cyan-400" />
              </Button>
            </SheetTrigger>
            <SheetContent
              side="left"
              className="w-64 bg-[#0a1a1f] border-cyan-950 p-0"
            >
              <div className="flex justify-end p-2">
                <SheetClose asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-cyan-400 hover:bg-gray-700"
                  >
                    <X className="w-5 h-5" />
                  </Button>
                </SheetClose>
              </div>
              <SidebarContent jwt={jwt} />
            </SheetContent>
          </Sheet>
          <h1 className="text-lg font-semibold">RAG</h1>
          <Button
            onClick={handleLogout}
            variant="ghost"
            size="sm"
            className="text-cyan-400 hover:text-cyan-300"
          >
            <LogOut className="w-5 h-5" />
          </Button>
        </header>

        {browserSupport.message && !browserSupport.supported && (
          <Alert variant="destructive" className="m-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{browserSupport.message}</AlertDescription>
          </Alert>
        )}

        {/* <main className="flex-1 p-4 overflow-y-auto pb-24 md:pb-4">
          <div className="max-w-3xl mx-auto">
            {messages.map((message, index) => (
              <div key={index} className={`mb-4 flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`p-4 rounded-lg max-w-lg ${message.type === 'user' ? 'bg-cyan-600' : 'bg-gray-700'}`}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline && match ? (
                          <SyntaxHighlighter style={dracula} language={match[1]} PreTag="div" {...props}>
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code className="bg-gray-800 rounded px-1" {...props}>{children}</code>
                        );
                      },
                    }}>
                    {message.content}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
            {isLoading && <ProcessingAnimation />}
            <div ref={chatEndRef} />
          </div>
        </main> */}

        <main className="flex-1 p-4 overflow-y-auto pb-24 md:pb-4">
          <div className="max-w-3xl mx-auto">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`mb-4 flex ${
                  message.type === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`p-4 rounded-lg max-w-lg ${
                    message.type === "user" ? "bg-cyan-600" : "bg-gray-700"
                  }`}
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || "");
                        return !inline && match ? (
                          <SyntaxHighlighter
                            style={dracula}
                            language={match[1]}
                            PreTag="div"
                            {...props}
                          >
                            {String(children).replace(/\n$/, "")}
                          </SyntaxHighlighter>
                        ) : (
                          <code className="bg-gray-800 rounded px-1" {...props}>
                            {children}
                          </code>
                        );
                      },
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              </div>
            ))}

            {/* It renders the live streaming text in a bot message bubble */}
            {streamingResponse && (
              <div className="mb-4 flex justify-start">
                <div className="p-4 rounded-lg max-w-lg bg-gray-700">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || "");
                        return !inline && match ? (
                          <SyntaxHighlighter
                            style={dracula}
                            language={match[1]}
                            PreTag="div"
                            {...props}
                          >
                            {String(children).replace(/\n$/, "")}
                          </SyntaxHighlighter>
                        ) : (
                          <code className="bg-gray-800 rounded px-1" {...props}>
                            {children}
                          </code>
                        );
                      },
                    }}
                  >
                    {streamingResponse}
                  </ReactMarkdown>
                </div>
              </div>
            )}
            {/* --- END OF NEW BLOCK --- */}

            {/* Updated loading indicator: only show if loading AND not yet streaming */}
            {isLoading && !streamingResponse && <ProcessingAnimation />}

            <div ref={chatEndRef} />
          </div>
        </main>

        <div className="fixed bottom-0 left-0 right-0 p-4 border-t border-cyan-950 bg-[#0a1a1f] md:relative md:pb-4">
          {promptsRemaining !== null && (
            <div className="text-center text-sm text-gray-400 mb-2">
              {promptsRemaining <= 0 ? (
                <span className="text-red-400">
                  Daily prompt limit reached.
                </span>
              ) : (
                <span>
                  {promptsRemaining} of {maxPrompts} prompts remaining today.
                </span>
              )}
            </div>
          )}
          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 bg-black/30 rounded-full p-2 max-w-[900px] mx-auto"
          >
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={handleMicClick}
              className={`rounded-full ${
                isListening ? "text-red-500 animate-pulse" : "text-cyan-400"
              }`}
              disabled={!browserSupport.supported || isSendDisabled}
            >
              <Mic className="w-6 h-6" ref={micRef} />
            </Button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Or Talk With RAG"
              className="flex-1 bg-transparent border-none focus:outline-none text-gray-300"
              disabled={isSendDisabled}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="text-cyan-400 rounded-full"
              title="Upload PDF files"
              onClick={() => fileInputRef.current.click()}
              disabled={isSendDisabled}
            >
              <Upload className="w-6 h-6" />
              <input
                type="file"
                ref={fileInputRef}
                multiple
                style={{ display: "none" }}
                onChange={handleFileChange}
                accept=".pdf"
              />
            </Button>
            {files.length > 0 && (
              <span className="text-sm text-gray-400 whitespace-nowrap px-2">
                {files.length} file{files.length > 1 ? "s" : ""}
              </span>
            )}
            <Button
              type="submit"
              variant="ghost"
              size="icon"
              className="text-cyan-400 rounded-full"
              disabled={isLoading && isSendDisabled}
            >
              <Send className="w-6 h-6" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
