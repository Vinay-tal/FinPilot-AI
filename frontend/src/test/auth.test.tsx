import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { AuthProvider } from '@/context/AuthContext'
import { ToastProvider } from '@/context/ToastContext'

describe('Authentication Pages', () => {
  it('renders LoginPage with form inputs and 1-Click Demo Login button', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <ToastProvider>
            <LoginPage />
          </ToastProvider>
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { name: /finpilot ai/i })).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/name@example.com/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/••••••••/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^sign in$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /1-click demo sign in/i })).toBeInTheDocument()
  })

  it('renders RegisterPage with full name, email, and password fields', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <ToastProvider>
            <RegisterPage />
          </ToastProvider>
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { name: /create an account/i })).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/rahul sharma/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/name@example.com/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/minimum 8 characters/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /register & continue/i })).toBeInTheDocument()
  })
})
