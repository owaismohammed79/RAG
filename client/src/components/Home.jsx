import React from 'react'
import Navbar from './Navbar'
import { Typewriter } from 'react-simple-typewriter'
import { useNavigate } from 'react-router-dom'

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="bg-[#1C221C] text-white overflow-hidden flex justify-center">
      <Navbar />
      <main className="relative mt-10 sm:mt-4 px-4 py-16 md:py-24">
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'radial-gradient(circle at center, rgba(19, 227, 255, 0.15) 0%, rgba(28, 34, 28, 0.95) 70%, #1C221C 100%)'
          }}
        />
        <section className='relative z-10 flex flex-col gap-16 items-center max-w-5xl mx-auto'>
          <div className='text-center'>
            <h2 className='text-4xl md:text-5xl text-[#13E3FF] font-bold mb-2'>Meet RAG</h2>
            <p className='text-lg text-gray-300'>(Rapid Answer Generator)</p>
          </div>
          
          <div className='flex flex-col items-center gap-8'>
            <div className='font-bold text-4xl md:text-5xl text-center'>
              <span>Upload Your Documents, Ask Anything,</span>
              <br />
              <span className="text-[#13E3FF]">
                <Typewriter
                  words={[" Get Instant Insights.", " Get Instant Answers.", " Get Instant Value."]}
                  loop={true}
                  cursor
                  cursorStyle='|'
                  typeSpeed={70}
                  deleteSpeed={50}
                  delaySpeed={1000}
                />
              </span>
            </div>
            <p className='max-w-2xl text-center text-lg leading-relaxed text-gray-300'>
              RAG turns your PDFs into a personal knowledge base. Just upload, ask, and receive precise answers 
              tailored to your content. From research to decision-making, RAG empowers you to 
              extract maximum value from your documents.
            </p>
            
            <button className='group bg-[#13E3FF] text-black rounded-xl font-bold py-3 px-6 text-xl flex items-center transition-all hover:bg-[#0FC9E8] hover:shadow-lg hover:shadow-[#13E3FF]/20' onClick={() => navigate('/signup')}>
              <span>Start Now</span>
              <img 
                src="/collection-arrow-doodles.svg" 
                alt="arrow logo" 
                className='ml-2 pt-1 w-8 h-8 transition-transform group-hover:translate-x-1'
              />
            </button>
          </div>
        </section>
      </main>
    </div>
  )
}