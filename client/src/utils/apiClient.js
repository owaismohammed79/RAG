import authService from '../appwrite(service)/auth';
import { conf } from '../config/conf';

export const apiFetch = async (endpoint, options = {}) => {
  let token;
  
  try {
    const session = await authService.getJWT()
    token = session.jwt
  } catch (error) {
    console.error("Appwrite session is completely dead:", error)
    throw new Error("AUTH_FAILED")
  }

  const headers = {...options.headers, 'Authorization': `Bearer ${token}`}
  const response = await fetch(`${conf.BackendURL}${endpoint}`, {...options,headers})

  if(response.status === 401) {
    console.error("Backend rejected the token")
    throw new Error("AUTH_FAILED")
  }

  return response;
}