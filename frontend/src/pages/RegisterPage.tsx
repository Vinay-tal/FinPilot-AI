import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Sparkles, User as UserIcon, Lock, Mail } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import { Button } from '@/components/common/Button'

const registerSchema = z.object({
  full_name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

type RegisterFormData = z.infer<typeof registerSchema>

export const RegisterPage: React.FC = () => {
  const { register: registerAuth } = useAuth()
  const { error: toastError, success: toastSuccess } = useToast()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (data: RegisterFormData) => {
    setLoading(true)
    try {
      await registerAuth(data.email, data.password, data.full_name)
      toastSuccess('Account created successfully! Welcome to FinPilot AI.')
      navigate('/dashboard')
    } catch (err: any) {
      toastError(err.message || 'Registration failed. Email may already be in use.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-navy-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-96 bg-teal-500/10 blur-[120px] pointer-events-none rounded-full" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-teal-500 to-teal-300 shadow-lg shadow-teal-500/20 mb-4">
          <Sparkles className="w-6 h-6 text-navy-950 stroke-[2.2]" />
        </div>
        <h2 className="text-3xl font-extrabold tracking-tight text-white">Create an Account</h2>
        <p className="mt-2 text-sm text-slate-400">Start managing your personal finances with AI-driven insights</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10 px-4 sm:px-0">
        <div className="bg-navy-900 border border-navy-800 py-8 px-6 shadow-2xl rounded-2xl sm:px-10 space-y-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  {...register('full_name')}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-navy-850 border border-navy-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all"
                  placeholder="Rahul Sharma"
                />
              </div>
              {errors.full_name && (
                <p className="text-[11px] text-rose-400 mt-1">{errors.full_name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="email"
                  {...register('email')}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-navy-850 border border-navy-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all"
                  placeholder="name@example.com"
                />
              </div>
              {errors.email && (
                <p className="text-[11px] text-rose-400 mt-1">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="password"
                  {...register('password')}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-navy-850 border border-navy-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all"
                  placeholder="Minimum 8 characters"
                />
              </div>
              {errors.password && (
                <p className="text-[11px] text-rose-400 mt-1">{errors.password.message}</p>
              )}
            </div>

            <Button
              type="submit"
              variant="primary"
              isLoading={loading}
              className="w-full py-2.5 mt-2"
            >
              Register & Continue
            </Button>
          </form>

          <div className="text-center text-xs text-slate-400 pt-2 border-t border-navy-800">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-teal-400 hover:text-teal-300 transition-colors">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
