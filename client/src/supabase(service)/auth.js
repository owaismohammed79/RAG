import { createClient } from '@supabase/supabase-js';
import { conf } from '../config/conf';

const supabaseUrl = conf.supabaseUrl;
const supabaseKey = conf.supabasePublishableKey;

const supabase = createClient(supabaseUrl, supabaseKey);

export class AuthService {
    async createAccount({ email, password }) {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        return data;
    }

    async login({ email, password }) {
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        return data;
    }

    async googleLogin() {
        const { data, error } = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: `${window.location.origin}/chat`
            }
        });
        if (error) throw error;
        return data;
    }

    async getCurrentUser() {
        const { data: { user }, error } = await supabase.auth.getUser();
        if (error || !user) return null;
        return user;
    }

    async getSession() {
        // getSession() pulls the token created by the URL hash automatically
        const { data: { session }, error } = await supabase.auth.getSession();
        if (error) throw error;
        return session;
    }

    async logout() {
        const { error } = await supabase.auth.signOut();
        if (error) throw error;
    }
}

const authService = new AuthService();
export default authService;