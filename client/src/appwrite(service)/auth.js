import { Client, Account, ID, OAuthProvider} from "appwrite";
import { conf } from "../config/conf.js";

export class AuthService{
    client = new Client();
    account;

    constructor(){
    this.client
        .setEndpoint('https://fra.cloud.appwrite.io/v1')
        .setProject(conf.appwriteProjectId);
    this.account = new Account(this.client);
    }

    async googleLogin(){
        await this.account.createOAuth2Session(OAuthProvider.Google, 'http://localhost:5173/chat', 'http://localhost:5173/fail')
    }

    async getCurrentUser() {
        try {
            const user = await this.account.getSession('current');
            return user;
        } catch (error) {
            console.log(`Appwrite error in getting user: ${error}`)
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
            await this.account.deleteSessions();
        } catch (error) {
            console.log("Appwrite error:: Logout", error)
            throw error;
        }
    }
}

const authService = new AuthService();

export default authService;