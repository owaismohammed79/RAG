import Logo from "./Logo"
import { NavLink } from "react-router-dom"
import { conf } from "../config/conf";

/*bg-[#1C221C]*/
function Navbar() {
  const emailAddress = conf.emailAddress;
  const mailtoLink = `mailto:${emailAddress}`;

    const handleScroll = (id) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <nav className="w-11/12 h-16 py-2 flex justify-between px-2 fixed top-2 z-20 bg-white/30 backdrop-blur-3xl backdrop-brightness-50 rounded-full">
        <Logo />
        <div className="flex justify-around items-center gap-1">
            <NavLink to="/" className="text-white text-lg font-semibold px-2">Home</NavLink>
            <NavLink to="#how-it-works" className="text-white text-lg font-semibold px-2" onClick={()=>handleScroll("how-it-works")}>How it works</NavLink>
            <NavLink to="#contact" className="text-white text-lg font-semibold px-2" onClick={() => window.location.href = mailtoLink}>Contact Us</NavLink>
            <NavLink to="/signup" className="text-white text-lg font-semibold px-2">Sign up</NavLink>
            <NavLink to="/login" className="text-white text-lg font-semibold px-2">Log In</NavLink>
        </div>
    </nav>
  )
}

export default Navbar