import Home from '../components/Home'
import HowItWorks from '../components/HowItWorks'
import {Button} from '../components/ui/button'
import Footer from '../components/Footer'

function LandingPg() {
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
            <Button className='relative bg-[#1C221C] text-[#13E3FF] my-3'>Try RAG --&gt;</Button>
        </section>
        <Footer />
    </div>
  )
}

export default LandingPg