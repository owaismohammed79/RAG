export const conf = {
    appwriteProjectId : String(import.meta.env.VITE_APPWRITE_PROJECT_ID),
    appwriteUrl: String(import.meta.env.VITE_APPWRITE_ENDPOINT),
    appwriteDatabaseId : String(import.meta.env.VITE_APPWRITE_DATABASE_ID),
    appwriteCollectionId: String(import.meta.env.VITE_APPWRITE_COLLECTION_ID),
    googleoAuthClientId: String(import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID),
    emailAddress: String(import.meta.env.VITE_EMAIL_ADDRESS),
    BaseUrl: String(import.meta.env.BASE_URL)
}