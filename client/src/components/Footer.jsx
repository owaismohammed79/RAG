import { NavLink, useLocation, useNavigate } from "react-router-dom";

function Footer() {
  const location = useLocation();
  const navigate = useNavigate();

  const handleScroll = (id) => {
    if (location.pathname !== '/') {
      navigate('/');
      setTimeout(() => {
        const element = document.getElementById(id);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);
    } else {
      const element = document.getElementById(id);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <footer className='bg-[#1C221C] mt-0.5 text-white flex flex-col items-center justify-center py-4'>
        <div className='flex gap-x-6 gap-y-3 flex-wrap justify-center px-4'>
            <NavLink to="/" className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors'>Home</NavLink>
            <a href="/#how-it-works" className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors cursor-pointer' onClick={(e) => { e.preventDefault(); handleScroll("how-it-works"); }}>How it works</a>
            <a href="https://github.com/owaismohammed79/RAG" target="_blank" rel="noopener noreferrer" className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors'>GitHub</a>
            <NavLink to="/privacy-policy" className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors'>Privacy Policy</NavLink>
        </div>
        <p className='text-sm mt-4'>© 2025 RAG. All Rights Reserved</p>
    </footer>
  )
}

export default Footer