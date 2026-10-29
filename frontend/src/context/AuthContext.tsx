import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User } from '@/types'
import { loginApi, registerApi, demoLoginApi, getMeApi } from '@/api/auth'

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  isDemoMode: boolean
  login: (email: string, pass: string) => Promise<void>
  register: (email: string, pass: string, fullName: string) => Promise<void>
  loginAsDemo: () => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('finpilot_user')
    return saved ? JSON.parse(saved) : null
  })
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('finpilot_token'))
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    async function verifyUser() {
      if (token) {
        try {
          const profile = await getMeApi()
          setUser(profile)
          localStorage.setItem('finpilot_user', JSON.stringify(profile))
        } catch (err: any) {
          // If token expired or explicitly unauthorized, reset
          if (err?.statusCode === 401 || err?.status === 401) {
            localStorage.removeItem('finpilot_token')
            localStorage.removeItem('finpilot_user')
            setUser(null)
            setToken(null)
          }
        }
      }
      setIsLoading(false)
    }

    verifyUser()
  }, [token])

  const login = async (email: string, pass: string) => {
    setIsLoading(true)
    try {
      const res = await loginApi({ email, password: pass })
      localStorage.setItem('finpilot_token', res.access_token)
      localStorage.setItem('finpilot_user', JSON.stringify(res.user))
      setToken(res.access_token)
      setUser(res.user)
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (email: string, pass: string, fullName: string) => {
    setIsLoading(true)
    try {
      const res = await registerApi({ email, password: pass, full_name: fullName })
      localStorage.setItem('finpilot_token', res.access_token)
      localStorage.setItem('finpilot_user', JSON.stringify(res.user))
      setToken(res.access_token)
      setUser(res.user)
    } finally {
      setIsLoading(false)
    }
  }

  const loginAsDemo = async () => {
    setIsLoading(true)
    try {
      const res = await demoLoginApi()
      localStorage.setItem('finpilot_token', res.access_token)
      localStorage.setItem('finpilot_user', JSON.stringify(res.user))
      setToken(res.access_token)
      setUser(res.user)
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('finpilot_token')
    localStorage.removeItem('finpilot_user')
    setUser(null)
    setToken(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!token && !!user,
        isDemoMode: user?.is_demo ?? false,
        login,
        register,
        loginAsDemo,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
