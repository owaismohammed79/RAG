import { useState } from "react";
import Logo from "./Logo";
import { NavLink } from "react-router-dom";
import { conf } from "../config/conf";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Menu } from "lucide-react";

function Navbar() {
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const emailAddress = conf.emailAddress;
  const mailtoLink = `mailto:${emailAddress}`;

  const handleScroll = (id) => {
    setIsSheetOpen(false); //Close sheet on link click
    setTimeout(() => {
      const element = document.getElementById(id);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }, 100);
  };

  const navLinks = (
    <>
      <NavLink to="/" onClick={() => setIsSheetOpen(false)} className="text-white text-lg font-semibold px-2 py-2 md:py-0">Home</NavLink>
      <NavLink to="/#how-it-works" className="text-white text-lg font-semibold px-2 py-2 md:py-0" onClick={() => handleScroll("how-it-works")}>How it works</NavLink>
      <a href={mailtoLink} onClick={() => setIsSheetOpen(false)} className="text-white text-lg font-semibold px-2 py-2 md:py-0">Contact Us</a>
      <NavLink to="/signup" onClick={() => setIsSheetOpen(false)} className="text-white text-lg font-semibold px-2 py-2 md:py-0">Sign up</NavLink>
      <NavLink to="/login" onClick={() => setIsSheetOpen(false)} className="text-white text-lg font-semibold px-2 py-2 md:py-0">Log In</NavLink>
    </>
  );

  return (
    <nav className="w-11/12 h-16 py-2 flex justify-between items-center px-4 fixed top-2 z-20 bg-white/30 backdrop-blur-3xl backdrop-brightness-50 rounded-full">
      <Logo />
      {/* Desktop Navigation */}
      <div className="hidden md:flex justify-around items-center gap-1">
        {navLinks}
      </div>
      {/* Mobile Navigation */}
      <div className="md:hidden">
        <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon">
              <Menu className="h-6 w-6 text-white" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="bg-[#0a1a1f] border-l-cyan-950 text-white w-[250px] sm:w-[300px] p-6">
            <div className="flex flex-col items-start gap-6 pt-10">
              {navLinks}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </nav>
  );
}

export default Navbar;