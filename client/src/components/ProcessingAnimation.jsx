import React from 'react';

const ProcessingAnimation = () => {
  const messages = [
    "Analyzing documents...",
    "Extracting key information...",
    "Synthesizing insights...",
    "Formulating response...",
    "Consulting knowledge base...",
    "Generating answer..."
  ];

  const [currentMessageIndex, setCurrentMessageIndex] = React.useState(0);

  React.useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMessageIndex((prevIndex) => (prevIndex + 1) % messages.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [messages.length]);

  return (
    <div className="text-center text-cyan-400 flex items-center justify-center space-x-2">
      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
      <span className="ml-2">{messages[currentMessageIndex]}</span>
    </div>
  );
};

export default ProcessingAnimation;