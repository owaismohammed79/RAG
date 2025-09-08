import { conf } from "../config/conf";
import { NavLink, useLocation, useNavigate } from "react-router-dom";

function Footer() {
  const emailAddress = conf.emailAddress;
  const mailtoLink = `mailto:${emailAddress}`;
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
            <a href={mailtoLink} className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors'>Contact Us</a>
            <NavLink to="/privacy-policy" className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors'>Privacy Policy</NavLink>
        </div>
        <p className='text-sm mt-4'>© 2025 RAG. All Rights Reserved</p>
    </footer>
  )
}

export default Footer