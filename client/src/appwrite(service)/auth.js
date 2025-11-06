import { Client, Account, ID, OAuthProvider, Databases} from "appwrite";
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
            try {
                await this.account.get();
                console.log("Another session found, logging out before login...");
                await this.account.deleteSession('current');
            } catch (error) {
                //Not throwing this error is the best way to handle this
                console.log("User is guest, proceeding to login.", error);
            }
            
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