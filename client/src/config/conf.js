export const conf = {
    supabaseUrl: String(import.meta.env.VITE_SUPABASE_URL),
    supabasePublishableKey: String(import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY),
    googleoAuthClientId: String(import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID),
    emailAddress: String(import.meta.env.VITE_EMAIL_ADDRESS),
    BackendURL: String(import.meta.env.VITE_BACKEND_URL),
    BaseUrl: String(import.meta.env.VITE_BASE_URL)
};