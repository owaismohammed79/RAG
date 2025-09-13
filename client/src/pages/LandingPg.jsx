import Home from '../components/Home'
import HowItWorks from '../components/HowItWorks'
import {Button} from '../components/ui/button'
import Footer from '../components/Footer'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { conf } from '../config/conf'

function LandingPg() {
  const navigate = useNavigate()

  useEffect(() => {
    const pingBackend = async () => {
      try {
        await fetch(`${conf.BackendURL}/api/ping`);
        console.log("Backend pinged successfully.");
      } catch (error) {
        console.error("Failed to ping backend:", error);
      }
    };
    pingBackend();
  }, []);

  return (
    <div>
        <Home />
        <HowItWorks />
        <section className='relative bg-[#1C221C] text-white overflow-hidden flex flex-col justify-center items-center py-4'>
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'radial-gradient(circle at center, rgba(19, 227, 255, 0.15) 0%, rgba(28, 34, 28, 0.95) 70%, #1C221C 100%)'
            }}
          />
          <h1 className='relative text-3xl font-bold w-1/2 text-center'>Get instant, accurate answers from your PDFs with RAG. Simplify your search today!</h1>
            <Button className='relative bg-[#1C221C] text-[#13E3FF] my-3' onClick={() => navigate('/signup')}>Try RAG --&gt;</Button>
        </section>
        <Footer />
    </div>
  )
}

export default LandingPg