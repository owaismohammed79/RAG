import { useState, useContext, useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Menu, Mic, Send, Upload, PlusCircle, MenuIcon, AlertCircle, X } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger, SheetClose } from "@/components/ui/sheet"
import { UserDataContext } from '../Context/UserDataContextProvider'
import { useNavigate } from 'react-router-dom'
import { Alert, AlertDescription } from "@/components/ui/alert"
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { dracula } from 'react-syntax-highlighter/dist/esm/styles/prism';
import authService from '../appwrite(service)/auth'
import { addMessage, setConversationId, fetchConversations } from '../redux/convoSlice'
import ConversationHistory from './ConversationHistory'
import { conf } from '../config/conf'

const SidebarContent = ({ jwt }) => <ConversationHistory jwt={jwt} />;

export default function ChatInterface() {
  const { setUserData } = useContext(UserDataContext);
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const { activeConversationId, messages } = useSelector(state => state.conversation);
  const [jwt, setJwt] = useState(null);
  const [input, setInput] = useState('');
  const [files, setFiles] = useState([]);
  const fileInputRef = useRef(null);
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);
  
  const [isListening, setIsListening] = useState(false);
  const micRef = useRef(null);
  const [recognition, setRecognition] = useState(null);
  const [browserSupport, setBrowserSupport] = useState({ supported: true, message: '' });

  useEffect(() => {
    const checkUser = async () => {
      try {
        const currentUser = await authService.getCurrentUser();
        if (currentUser) {
          setUserData(currentUser);
          const token = await authService.getJWT();
          setJwt(token.jwt);
        } else {
          const storedUserDataString = localStorage.getItem('userData');
          if (storedUserDataString) {
            const parsedData = JSON.parse(storedUserDataString);
            setUserData(parsedData);
            const token = await authService.getJWT();
            setJwt(token.jwt);
          } else {
            navigate('/login');
          }
        }
      } catch (error) {
        console.error("Authentication check failed:", error);
        localStorage.removeItem('userData');
        navigate('/login');
      }
    };
    checkUser();
  }, [navigate, setUserData]);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setBrowserSupport({ supported: false, message: "Speech recognition not supported in this browser." });
      return;
    }
    const recognitionInstance = new SpeechRecognition();
    recognitionInstance.continuous = true;
    recognitionInstance.interimResults = true;
    recognitionInstance.onresult = (event) => {
      const transcript = Array.from(event.results).map(r => r[0]).map(r => r.transcript).join('');
      setInput(transcript);
    };
    recognitionInstance.onstart = () => setIsListening(true);
    recognitionInstance.onend = () => setIsListening(false);
    setRecognition(recognitionInstance);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
    if (selectedFiles.some(file => file.type !== 'application/pdf' || file.size > 10 * 1024 * 1024)) {
      alert('Please select only PDF files under 10MB.');
      return;
    }
    if (selectedFiles.length > 5) {
      alert('Please select a maximum of 5 files.');
      return;
    }
    setFiles(selectedFiles);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (input.trim() === '' || !jwt) return;

    setIsLoading(true);
    const userMessage = { type: 'user', content: input };
    dispatch(addMessage(userMessage));

    const formData = new FormData();
    files.forEach(file => formData.append('file', file));
    formData.append('prompt', input);
    formData.append('conversationId', activeConversationId || 'null');
    
    //sliding window of last 5 pairs (10 messages)
    const history = messages.slice(-10);
    formData.append('history', JSON.stringify(history));

    setInput('');
    setFiles([]); //clear files after submission

    try {
      const res = await fetch(`${conf.BaseUrl}/api/prompt/text-file`, {
        method: "POST",
        body: formData,
        headers: { 'Authorization': `Bearer ${jwt}` }
      });
      const data = await res.json();
      if (res.ok) {
        dispatch(addMessage({ type: 'bot', content: data.answer }));
        if (!activeConversationId) {
          dispatch(setConversationId(data.conversationId));
          dispatch(fetchConversations(jwt)); 
        }
      } else {
        throw new Error(data.error || 'API request failed');
      }
    } catch (error) {
      console.error('Error fetching response:', error);
      dispatch(addMessage({ type: 'bot', content: `Sorry, an error occurred: ${error.message}` }));
    }
    setIsLoading(false);
  };

  return (
    <div className="flex h-screen bg-[#0a1a1f] text-white">
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
            <SheetContent side="left" className="w-64 bg-[#0a1a1f] border-cyan-950 p-0">
                <div className="flex justify-end p-2">
                    <SheetClose asChild>
                        <Button variant="ghost" size="icon" className="text-cyan-400 hover:bg-gray-700">
                            <X className="w-5 h-5" />
                        </Button>
                    </SheetClose>
                </div>
              <SidebarContent jwt={jwt} />
            </SheetContent>
          </Sheet>
          <h1 className="text-lg font-semibold">RAG</h1>
        </header>

        {browserSupport.message && !browserSupport.supported && (
          <Alert variant="destructive" className="m-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{browserSupport.message}</AlertDescription>
          </Alert>
        )}

        <main className="flex-1 p-4 overflow-y-auto">
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
            {isLoading && <div className="text-center text-cyan-400">RAG Bot is thinking...</div>}
            <div ref={chatEndRef} />
          </div>
        </main>

        <div className="p-4 border-t border-cyan-950">
          <form onSubmit={handleSubmit} className="flex items-center gap-2 bg-black/30 rounded-full p-2 max-w-[900px] mx-auto">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={handleMicClick}
              className={`rounded-full ${isListening ? 'text-red-500 animate-pulse' : 'text-cyan-400'}`}
              disabled={!browserSupport.supported}
            >
              <Mic className="w-6 h-6" ref={micRef} />
            </Button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Or Talk With RAG"
              className="flex-1 bg-transparent border-none focus:outline-none text-gray-300"
            />
            <Button type="button" variant="ghost" size="icon" className="text-cyan-400 rounded-full" title="Upload PDF files" onClick={() => fileInputRef.current.click()}>
              <Upload className="w-6 h-6" />
              <input type="file" ref={fileInputRef} multiple style={{ display: 'none' }} onChange={handleFileChange} accept=".pdf" />
            </Button>
            {files.length > 0 && <span className="text-sm text-gray-400">{files.length} file(s)</span>}
            <Button type="submit" variant="ghost" size="icon" className="text-cyan-400 rounded-full" disabled={isLoading}>
              <Send className="w-6 h-6" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}