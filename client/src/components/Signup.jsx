import {Button} from '../components/ui/button'
import Logo from './Logo'
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {useForm} from 'react-hook-form'
import { useNavigate, Link } from 'react-router-dom'
import authService from '../appwrite(service)/auth.js'
import { useState, useEffect } from 'react'
import {Label} from '../components/ui/label'
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from 'lucide-react'
import { useSelector, useDispatch } from 'react-redux'
import { login as reduxLogin, logout as reduxLogout } from '../redux/authSlice'

function Signup({variable}) {
  const [showPassword, setShowPassword] = useState(false);
  const {register,handleSubmit,formState: { errors }} = useForm()
  const navigate = useNavigate()
  const { userData } = useSelector(state => state.auth)
  const dispatch = useDispatch()
  const [formError, setFormError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (userData) {
      navigate('/chat')
    }
  }, [])

  const handleAuth = async (data) => {
    setFormError(null);
    setIsLoading(true);
    try {
      if (variable === "Sign up") {
        await authService.createAccount({ email: data.email, password: data.password });
      }
        await authService.login({ email: data.email, password: data.password });
      
      const currentUser = await authService.getCurrentUser();
      if (currentUser) {
        const jwt = await authService.getJWT()
        dispatch(reduxLogin({ userData: currentUser, jwt: jwt.jwt }))
        localStorage.setItem('userData', JSON.stringify(currentUser))
        navigate('/chat')
      } else {
        setFormError("Authentication successful, but failed to retrieve user data. Please try logging in again.");
      }
    } catch (error) {
      console.error("Authentication error:", error);
      setFormError(error.message || "An unexpected error occurred during authentication.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async() => {
    setFormError(null);
    setIsLoading(true);
    try {
      authService.logout();
      dispatch(reduxLogout());
      localStorage.clear();
      await authService.googleLogin()
    } catch (error) {
      console.error(error)
    }
  }

  return (
    <div className='w-full h-[100dvh] flex flex-col justify-center items-center px-2 py-4 bg-[#1C221C] text-white relative'>
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(circle at center, rgba(19, 227, 255, 0.15) 0%, rgba(28, 34, 28, 0.95) 70%, #1C221C 100%)'
        }}
      />
      <div className='flex flex-col justify-between items-center gap-2 w-full z-10'>
        <div>
          <Logo className={`w-40`} textSize={`4xl`}/>
          <p className='py-1'>(Rapid Answer Generator)</p>
        </div>
        <h1 className='text-3xl sm:text-4xl py-1 font-bold text-center'>Be More Productive</h1>
        <Card className='bg-[#0A363CB2] border-[#104f59] px-4 sm:px-6 py-2 relative group hover:bg-[#0A363CB2]/100 transition-colors overflow-hidden w-full max-w-md sm:w-3/4 md:w-1/2 lg:w-1/3'>  
          <CardContent className='flex flex-col justify-between items-center gap-2 px-2 sm:px-6 py-2'>
            <div className='text-sm text-gray-300 flex flex-col w-full items-center justify-center my-1'>
              <span className='text-white font-bold text-2xl'>{variable}</span>
              <div>
                {variable === "Sign up" ? (
                  <p>Already have an account?&nbsp;
                    <Link to="/login" className='underline'>Log In?</Link>
                  </p>) : 
                  (<p>Don't have an account?&nbsp;
                    <Link to="/signup" className='underline'>Sign up?</Link>
                  </p>)}
              </div>
            </div>
            {formError && (
              <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <Button className="w-full bg-white text-black hover:bg-white/80 border-hidden" onClick={handleGoogleLogin} disabled={isLoading}>
              <div className='flex justify-center items-center gap-3'>
                <img src='/Google_Icon.svg' alt='Google' className='w-7 h-7 mt-0.5'/>
                <span className='text-[16px]'>Continue with Google</span>
              </div>
            </Button>
            <span className='text-white'>OR</span>
            <form onSubmit={handleSubmit(handleAuth)} className='flex flex-col justify-between items-center gap-3 w-full text-white'>
              <Label className="place-self-start" htmlFor="email">Email</Label>
              <Input type='email' id="email" placeholder='yourname@gmail.com' className='w-full text-white focus-visible:ring-0 focus:bg-transparent' {...register("email", {
                  required: true,
                  validate: {
                    matchPatern: (value) => /^\w+([.-]?\w+)*@\w+([.-]?\w+)*(\.\w{2,3})+$/.test(value) || "Email address must be a valid address"
                  }
                })} />
              {errors.email && <span className='text-red-500'>Email is required</span>}
              <Label className="place-self-start" htmlFor="userpassword">Password</Label>
              <div className='flex w-full border border-slate-100 rounded-lg'>
                <Input id="userpassword" placeholder={variable === "Sign up" ? 'Create a new password' : 'Enter your password'} className='w-full text-white border-none focus-visible:ring-0' type={showPassword ? "text" : "password"}
                {...register("password", {
                  required: true,
                  validate: {
                    matchPattern: (value) => /^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,}$/.test(value) ||
                    "Password should be at least 8 characters long with lower, upperCase alphabets and number"
                  }
                })} disabled={isLoading}/>
                <Button onClick={() => setShowPassword(showPassword => !showPassword) } className="bg-transparent hover:bg-transparent">{showPassword ? <img src='/eye-open.svg' alt="Eye open icon" /> : <img src="/eye-closed.svg" alt="Eye closed icon"/>}</Button>
              </div>
              {errors.password && <span className='text-red-500'>{errors.password.message}</span>}
              <Button className='bg-[#13E3FF] w-full text-black hover:bg-[#13E3FF]/70' type="submit" disabled={isLoading}>
                {isLoading ? "Processing..." : variable}
              </Button>
            </form>
            <div className='text-white text-center text-xs'>By continuing, you agree to RAG&apos;s Consumer Terms and Usage Policy, and acknowledge their Privacy Policy</div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default Signup