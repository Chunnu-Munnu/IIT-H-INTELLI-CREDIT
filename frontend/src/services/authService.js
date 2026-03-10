import api from "./api"
import { useAuthStore } from "../store/authStore"

export const authService = {

  async login(email, password) {
    const res = await api.post("/auth/login", { email, password })

    const { access_token, user } = res.data

    useAuthStore.getState().setAuth(user, access_token)

    return user
  },

  async register(data) {
    const res = await api.post("/auth/register", data)
    
    const { access_token, user } = res.data
    
    if (access_token && user) {
      useAuthStore.getState().setAuth(user, access_token)
    }
    
    return user
  },

  async logout() {
    await api.post("/auth/logout")
    useAuthStore.getState().clearAuth()
  },

  async getCurrentUser() {
    const res = await api.get("/auth/me")
    return res.data
  }

}
