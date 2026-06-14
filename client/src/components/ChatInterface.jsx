import { useState, useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Mic, Send, Upload, MenuIcon, AlertCircle, X, LogOut } from "lucide-react";
import { FaGithub } from "react-icons/fa";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetClose } from "@/components/ui/sheet";
import { useNavigate } from "react-router-dom";
import { Alert, AlertDescription } from "@/components/ui/alert";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { dracula } from "react-syntax-highlighter/dist/esm/styles/prism";
import authService from "../appwrite(service)/auth";
import { login as reduxLogin, logout as reduxLogout } from "../redux/authSlice";
import ConversationHistory from "./ConversationHistory";
import ProcessingAnimation from "./ProcessingAnimation";
import { useSpeech } from "../hooks/useSpeech";
import { useChat } from "../hooks/useChat";

const SidebarContent = () => <ConversationHistory />;

export default function ChatInterface() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const { userData, jwt } = useSelector((state) => state.auth);
  const { activeConversationId, messages } = useSelector((state) => state.conversation)
  const [input, setInput] = useState("");
  const [files, setFiles] = useState([]);
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  const { isListening, browserSupport, handleMicClick } = useSpeech((transcript) => setInput(transcript));
  const { submitChat, isLoading, streamingResponse, promptsRemaining, maxPrompts } = useChat(jwt, activeConversationId, messages);
  const isSendDisabled = isLoading || (promptsRemaining !== null && promptsRemaining <= 0);

  useEffect(() => {
    let isMounted = true;
    const checkUserAndJWT = async () => {
      if (userData && jwt) return;
      try {
        const currentUser = await authService.getCurrentUser();
        if (currentUser) {
          const token = await authService.getJWT();
          if (isMounted) {
            dispatch(reduxLogin({ userData: currentUser, jwt: token.jwt }));
            localStorage.setItem("userData", JSON.stringify(currentUser));
          }
        } else {
          throw new Error("No session");
        }
      } catch (error) {
        if (isMounted) handleLogout();
        console.log("Error in getting current user:", error.message)
      }
    };
    checkUserAndJWT();
    return () => { isMounted = false; };
  }, [dispatch, userData, jwt]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingResponse]);

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch(e) {
      console.log("Error in logging out:", e.message)
    }
    dispatch(reduxLogout());
    localStorage.clear();
    navigate("/login");
  };

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (selectedFiles.some(f => f.type !== "application/pdf" || f.size > 5242880)) {
      return alert("Only PDFs under 5MB allowed.");
    }
    if (selectedFiles.length > 2) return alert("Max 2 files.");
    setFiles(selectedFiles);
  };

  const onSubmit = (e) => {
    e.preventDefault();
    if(!input.trim() || !jwt) return;
    
    submitChat(input, files, {onClearInput: () => { setInput(""); setFiles([]); }, onRestoreInput: (failedInput, failedFiles) => { setInput(failedInput); setFiles(failedFiles); }, onAuthFailure: handleLogout});
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
          <div className="flex justify-center items-center justify-self-center">
            <Button
              onClick={handleLogout}
              variant="ghost"
              size="sm"
              className="text-cyan-400 hover:text-cyan-300"
            >
              <LogOut className="w-5 h-5" />
            </Button>
            <Button className="bg-transparent" variant="ghost" size="sm" asChild>
                <a href='https://github.com/owaismohammed79/RAG' target="_blank" rel="noopener noreferrer"><FaGithub className="w-5 h-5"/></a>
            </Button>
          </div>
        </header>

        {browserSupport.message && !browserSupport.supported && (
          <Alert variant="destructive" className="m-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{browserSupport.message}</AlertDescription>
          </Alert>
        )}

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
                      code({ inline, className, children, ...props }) {
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

            {streamingResponse && (
              <div className="mb-4 flex justify-start">
                <div className="p-4 rounded-lg max-w-lg bg-gray-700">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ inline, className, children, ...props }) {
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
            onSubmit={onSubmit}
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
              <Mic className="w-6 h-6" />
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
