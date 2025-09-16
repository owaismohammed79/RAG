import { Client, Account, ID, OAuthProvider, Databases, Permission, Role, Query } from "appwrite";
import { conf } from "../config/conf.js";

export class AuthService{
    client = new Client();
    account;
    databases;

    constructor(){
    this.client
        .setEndpoint(conf.appwriteUrl)
        .setProject(conf.appwriteProjectId);
    this.account = new Account(this.client);
    this.databases = new Databases(this.client);
    }

    async googleLogin(){
        try {
            await this.account.createOAuth2Session(OAuthProvider.Google, `${conf.BaseUrl}/chat`, `${conf.BaseUrl}/login`);
            const user = await this.getCurrentUser();
            if (!user) {
                throw new Error('Failed to register Google user in Appwrite Auth');
            }
            return user;
        } catch (error) {
            console.log("Appwrite error in Google login:", error);
            throw error;
        }
    }

    async getJWT() {
        try {
            const jwt = await this.account.createJWT();
            return jwt;
        } catch (error) {
            console.log(`Appwrite error in getting JWT: ${error}`);
            throw error;
        }
    }

    async getCurrentUser() {
        try {
            const user = await this.account.get();            
            try {
                await this.databases.getDocument(
                    conf.appwriteDatabaseId,
                    conf.appwriteUsersCollectionId,
                    user.$id //making this transaction idempotent
                );
                // If getDocument succeeds, the user document already exists
            } catch (error) {
                if (error.code === 404) { 
                    await this.databases.createDocument(
                        conf.appwriteDatabaseId,
                        conf.appwriteUsersCollectionId,
                        user.$id,
                        {
                            userId: user.$id,
                            email: user.email,
                            status: user.emailVerification,
                            joined: new Date().toISOString()
                        },
                        [
                            Permission.read(Role.user(user.$id)),
                            Permission.update(Role.user(user.$id)),
                            Permission.delete(Role.user(user.$id))
                        ]
                    );
                } else {
                    console.error("Error checking/creating user document:", error);
                    throw error;
                }
            }
            return user;
        } catch (error) {
            console.error("Appwrite error in getting user:", error);
            return null;
        }
    }

    async createAccount({email, password}){
        try {
            const userAccount = await this.account.create(ID.unique(),email, password);
            if(userAccount){
                return this.login({email, password});
            }else {
                return  userAccount;
            }
        } catch (error) {
            console.log(`Appwrite Error in account creation: ${error}`)
            throw error;
        }
    }

    async login({email, password}){
        try {
            const session = await this.account.createEmailPasswordSession(email, password);
            return {session};
        } catch (error) {
            console.log(`Appwrite Error in login: ${error}`)
            throw error;
        }
    }

    async logout(){
        try {
            await this.account.deleteSession('current');
        } catch (error) {
            console.log("Appwrite error:: Logout", error)
            throw error;
        }
    }
}

const authService = new AuthService();

export default authService;