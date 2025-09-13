import { useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../appwrite(service)/auth';
import { UserDataContext } from '../Context/UserDataContextProvider';
import Logo from './Logo';

const AuthCallback = () => {
    const navigate = useNavigate();
    const { setUserData } = useContext(UserDataContext);

    useEffect(() => {
        navigate('/chat');
    }, [navigate]);

    return (
        <div className="w-full min-h-screen flex flex-col justify-center items-center px-2 py-4 bg-[#1C221C] text-white relative">
            <div
                className="absolute inset-0 pointer-events-none"
                style={{
                background: 'radial-gradient(circle at center, rgba(19, 227, 255, 0.15) 0%, rgba(28, 34, 28, 0.95) 70%, #1C221C 100%)'
                }}
            />
            <div className="flex flex-col items-center gap-4 z-10">
                <Logo className={`w-40`} textSize={`4xl`}/>
                <p className="text-2xl animate-pulse">Finalizing your session...</p>
            </div>
        </div>
    );
};

export default AuthCallback;