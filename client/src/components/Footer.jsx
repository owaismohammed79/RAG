import { conf } from "../config/conf";
import { useNavigate, NavLink } from "react-router-dom";

function Footer() {
  const emailAddress = conf.emailAddress;
  const mailtoLink = `mailto:${emailAddress}`;
  const navigate = useNavigate();

  const handleScroll = (id) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <footer className='bg-[#1C221C] mt-0.5 text-white flex flex-col items-center justify-center py-4'>
        <div className='flex gap-4'>
            <NavLink  className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors'>Home</NavLink>
            <NavLink  className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors' onClick={()=>handleScroll("how-it-works")}>How it works</NavLink>
            <NavLink  className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors' onClick={() => window.location.href = mailtoLink}>Contact Us</NavLink>
            <NavLink to="/signup" className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors'>Sign up</NavLink>
            <NavLink to="/login" className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors'>Log In</NavLink>
            <NavLink to="/privacy-policy" className='text-[#13E3FF] hover:text-[#0FC9E8] transition-colors'>Privacy Policy</NavLink>
        </div>
        <p className='text-sm mt-4'>© 2024 RAG. All Rights Reserved</p>
    </footer>
  )
}

export default Footer