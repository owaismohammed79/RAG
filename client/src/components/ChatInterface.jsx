import { useState, useContext, useEffect, useRef } from 'react'
import {useSelector} from 'react-redux'
import { Menu, Mic, Send, Upload, BookOpen, Database, Bot, MenuIcon, AlertCircle } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { UserDataContext } from '../Context/UserDataContextProvider'
import { useNavigate } from 'react-router-dom'
import { Alert, AlertDescription } from "@/components/ui/alert"
import {conf} from "../config/conf"
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { dracula } from 'react-syntax-highlighter/dist/esm/styles/prism';


export default function ChatInterface() {
  const [isListening, setIsListening] = useState(false);
  const {userData, setUserData} = useContext(UserDataContext)
  const navigate = useNavigate()
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [files, setFiles] = useState([]);
  const fileInputRef = useRef(null);
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);
  const micRef = useRef(null);
  const [recognition, setRecognition] = useState(null);
  const [transcriptFeedback, setTranscriptFeedback] = useState('');
  const [browserSupport, setBrowserSupport] = useState({ supported: true, message: '' });
  // const token = useSelector(state => state.userData.authToken)
  
  useEffect(() => {
    if (userData !== null) return;
    const storedUserDataString = localStorage.getItem('userData');
    if (storedUserDataString === null) {
      console.log("No user data found in localStorage. Redirecting to /login.");
      navigate('/login');
      return;
    }
    try {
      const parsedData = JSON.parse(storedUserDataString);
      if (parsedData !== null && parsedData !== undefined) {
        setUserData(parsedData);
      } else {
        console.warn("localStorage 'userData' contained string 'null' or 'undefined'. Clearing invalid data.");
        localStorage.removeItem('userData');
        navigate('/login');
      }
    } catch (error) {
      console.error("Error parsing user data from localStorage:", error);
      localStorage.removeItem('userData');
      console.log("Invalid user data cleared from localStorage. Redirecting to /login.");
      navigate('/login');
    }
  }, [userData, setUserData, navigate]);

  useEffect(() => {
    if (isListening) {
      micRef.current.classList.add('animate-pulse');
      micRef.current.classList.add('text-red-500');
    } else {
      micRef.current.classList.remove('animate-pulse');
      micRef.current.classList.remove('text-red-500');
    }
  }, [isListening]); 

  useEffect(() => {
    const checkBrowserSupport = async () => {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      
      if (!SpeechRecognition) {
        setBrowserSupport({
          supported: false,
          message: "Speech recognition is not supported in this browser. Please try Chrome or Edge."
        });
        return;
      }
      
      try {
        const permissionResult = await navigator.mediaDevices.getUserMedia({ audio: true });
        permissionResult.getTracks().forEach(track => track.stop());

        // Initialize speech recognition
        const recognitionInstance = new SpeechRecognition();
        recognitionInstance.continuous = true;
        recognitionInstance.interimResults = true;
        
        recognitionInstance.onresult = (event) => {
          const transcript = Array.from(event.results)
            .map(result => result[0])
            .map(result => result.transcript)
            .join('');
          
          setInput(transcript);
          setTranscriptFeedback(transcript);
        };

        recognitionInstance.onstart = () => {
          setIsListening(true);
          console.log('Speech recognition started');
        };

        recognitionInstance.onend = () => {
          setIsListening(false);
          console.log('Speech recognition ended');
        };

        setRecognition(recognitionInstance);
        setBrowserSupport({ supported: true, message: '' });

      } catch (err) {
        console.error('Permission error:', err);
        setBrowserSupport({
          supported: false,
          message: "Microphone access was denied. Please enable microphone permissions and refresh the page."
        });
      }
    };

    checkBrowserSupport();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages])

  const handleMicClick = async () => {
    if (!browserSupport.supported) {
      return;
    }

    if (!recognition) {
      console.error('Speech recognition not available');
      return;
    }

    try {
      if (isListening) {
        recognition.stop();
        console.log('Stopping speech recognition');
      } else {
        // Request microphone permission again before starting
        await navigator.mediaDevices.getUserMedia({ audio: true });
        recognition.start();
        console.log('Starting speech recognition');
      }
    } catch (err) {
      console.error('Error accessing microphone:', err);
      setBrowserSupport({
        supported: false,
        message: "Microphone access was denied. Please enable microphone permissions and try again."
      });
    }
  };

  const handleFileChange = (event) => {
    const files = event.target.files;
    const maxSizeInBytes = 10 * 1024 * 1024;

    if (files) {
      for (let file of files) {
        if (file.type !== 'application/pdf' || file.size > maxSizeInBytes) { 
          alert('Please select only PDF files under 10MB.');
          return;
        }
      }
    }
    if (files.length > 5) {
      alert('Please select a maximum of 5 files.');
      return;
    }
    setFiles(Array.from(files));
  };

  const handleClick = () => {
    fileInputRef.current.click();
  };

  const handleSubmit = async(e) => {
    e.preventDefault();
    if (input.trim() === '') return;
    setIsLoading(true);
    setMessages(prevMessages => [...prevMessages, { type: 'user', content: input }]);
    const formData = new FormData();
    files.forEach(file => formData.append('file', file));
    formData.append('prompt', input);
    setInput('');
    try {
      //{conf.BaseUrl}
      const res = await fetch('http://localhost:5000/api/prompt/text-file', {   
        method: "POST",
        body: formData,
        // headers: {
        //   'Content-Type': 'application/json',
        //   'Authorization': `${token}`
        // }
      });
      const data = await res.json();
      setMessages(prevMessages => [...prevMessages, { type: 'model', content: data.answer }]);
    } catch(error) {
      console.log('Error fetching response:', error);
      setMessages(prevMessages => [...prevMessages, { type: 'model', content: 'Sorry, I encountered an error. Please try again.' }]);
    }
    setIsLoading(false);
  };

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };


  const sidebarItems = [
    { icon: BookOpen, label: 'Documents' },
    { icon: Database, label: 'Storage' },
    { icon: Bot, label: 'Assistant' },
    { icon: Menu, label: 'Menu' }
  ]

  const Sidebar = ({className}) => (
    <div className={`flex flex-col gap-4 p-4 ${className}`}>
      {sidebarItems.map((item, index) => (
        <Button
          key={index}
          variant="ghost"
          size="icon"
          className="w-12 h-12 rounded-lg hover:bg-cyan-500/20"
        >
          <item.icon className="w-6 h-6 text-cyan-400" />
        </Button>
      ))}
    </div>
  )

  return (
    <div className="flex min-h-screen bg-[#0a1a1f] text-white">
      <div className="hidden md:block border-r border-cyan-950">
        <Sidebar />
      </div>

      {/* Mobile Hamburger Menu */}
      <div className="md:hidden z-20">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="m-2">
              <MenuIcon className="w-6 h-6 text-cyan-400" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-[240px] bg-[#0a1a1f] border-cyan-950">
            <Sidebar className="flex-row"/>
          </SheetContent>
        </Sheet>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col absolute inset-0">
        {browserSupport.message && (
          <Alert variant="destructive" className="m-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {browserSupport.message}
            </AlertDescription>
          </Alert>
        )}
        <main className="flex-1 p-4 scrollbar scrollbar-thumb-sky-700 scrollbar-track-sky-300 overflow-y-scroll">
          <div className="max-w-2xl mx-auto">
            {messages.map((message, index) => (
              <div key={index} className={`mb-4 ${message.type === 'user' ? 'text-right' : 'text-left'}`}>
                <div className={`inline-block p-4 rounded-lg ${message.type === 'user' ? 'bg-cyan-600' : 'bg-gray-700'}`}>
                  <p className="text-white whitespace-pre-line">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]} //This is necessary for tables, task lists, strikethrough and code
                    components={{
                      //inline here refers to the text is already covered with a border 
                      //This is a JavaScript object property where the key is code. This tells ReactMarkdown: When you encounter a code element (from Markdown parsing), use this function to render it.
                      code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || ''); //regex trying to match the language of the text
                        return !inline && match ? (
                          <SyntaxHighlighter //If it is not inline and you've got the language then highlight it
                            style={dracula} 
                            language={match[1]} //this is unusual i.e the language that matches is match[1]
                            PreTag="div" //This tag when converted to plain HTML, CSS, JS is wrapped using the pre tag but if we want to add styles to it then we can change it to a div
                            {...props}
                          >
                            {String(children).replace(/\n$/, '') /*This is to remove the next line characters which are pretty
                            common in markdowns which have code in them as trailing characters*/}
                          </SyntaxHighlighter>
                        ) : ( //If the code is inline or the language was not found then simply give it like a border and render it
                          <code className={className} {...props}>
                            {children}
                          </code>
                        );
                      },
                    }}>
                      {message.content}
                    </ReactMarkdown>
                  </p>
                </div>
                <p className="mt-1 text-sm text-gray-400">{message.type === 'user' ? 'You' : 'RAG Bot'}</p>
              </div>
            ))}
            {isLoading && (
              <div className="text-center">
                <p className="text-cyan-400">RAG Bot is thinking...</p>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </main>

        <div className="p-4">
          <form onSubmit={handleSubmit} className="flex items-center gap-2 bg-black/30 rounded-full p-2 max-w-[900px] mx-auto">
          {/*So basically forms me agar buttons he to unko type="button" explicitly dena padega warna by default saare submit
          type ke rahenge joki kya karega ki submit wale button pe click karne par dusre saare buttons bhi click hojaenge */}
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={handleMicClick} 
              className={`rounded-full transition-colors duration-200 ${
                isListening ? 'text-red-500 animate-pulse' : 'text-cyan-400'
              } ${!browserSupport.supported ? 'opacity-50 cursor-not-allowed' : ''}`}
              disabled={!browserSupport.supported}
              title={browserSupport.supported ? 'Click to start/stop voice input' : browserSupport.message}
              type="button"
            >
              <Mic className="w-6 h-6" ref={micRef}/>
            </Button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Or Talk With RAG"
              className="flex-1 bg-transparent border-none focus:outline-none text-gray-300"
            />
            {isListening && browserSupport.supported && (
              <div className="absolute bottom-16 left-0 right-0 text-center text-sm">
                <span className="text-cyan-400">
                  {transcriptFeedback || 'Listening...'}
                </span>
              </div>
            )}
            <Button variant="ghost" size="icon" type="button" className="text-cyan-400 rounded-full" title="Only PDF files allowed" onClick={handleClick}>
              <Upload className="w-6 h-6" />
              <input
                type="file"
                ref={fileInputRef}
                multiple
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
            </Button>
            {files.length > 0 && (
              <ul>
                {`${files.length} files uploaded`}
              </ul>
            )}
            <Button type="submit" variant="ghost" size="icon" className="text-cyan-400 rounded-full" disabled={isLoading}>
                <Send className="w-6 h-6" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}

