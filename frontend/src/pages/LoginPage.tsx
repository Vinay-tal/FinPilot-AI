import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Sparkles, Shield, Lock, Mail, ArrowRight } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import { Button } from '@/components/common/Button'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

type LoginFormData = z.infer<typeof loginSchema>

export const LoginPage: React.FC = () => {
  const { login, loginAsDemo } = useAuth()
  const { error: toastError, success: toastSuccess } = useToast()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: 'demo@finpilot.in',
      password: 'Demo@FinPilot2026!',
    },
  })

  const onSubmit = async (data: LoginFormData) => {
    setLoading(true)
    try {
      await login(data.email, data.password)
      toastSuccess('Successfully signed in!')
      navigate('/dashboard')
    } catch (err: any) {
      toastError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleDemoLogin = async () => {
    setDemoLoading(true)
    try {
      await loginAsDemo()
      toastSuccess('Signed in as Rahul Sharma demo persona!')
      navigate('/dashboard')
    } catch (err: any) {
      toastError(err.message || 'Failed to authenticate demo account.')
    } finally {
      setDemoLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-navy-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Decorative gradient glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-96 bg-teal-500/10 blur-[120px] pointer-events-none rounded-full" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-teal-500 to-teal-300 shadow-lg shadow-teal-500/20 mb-4">
          <Sparkles className="w-6 h-6 text-navy-950 stroke-[2.2]" />
        </div>
        <h2 className="text-3xl font-extrabold tracking-tight text-white">FinPilot AI</h2>
        <p className="mt-2 text-sm text-slate-400">Intelligent Personal Financial Advisor for Indian Users</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10 px-4 sm:px-0">
        <div className="bg-navy-900 border border-navy-800 py-8 px-6 shadow-2xl rounded-2xl sm:px-10 space-y-6">
          {/* 1-Click Evaluation Banner */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-teal-950/80 to-navy-850 border border-teal-800/60 text-left space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-teal-300 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-teal-400" />
                Academic Evaluator Quick-Start
              </span>
              <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Skip registration and instantly test with <strong>Rahul Sharma's</strong> seeded 12-month Bengaluru financial dataset.
            </p>
            <Button
              type="button"
              onClick={handleDemoLogin}
              isLoading={demoLoading}
              className="w-full text-xs py-2 bg-teal-500 hover:bg-teal-400 text-navy-950 font-bold shadow-md shadow-teal-950"
            >
              1-Click Demo Sign In (Rahul Sharma)
            </Button>
          </div>

          <div className="relative flex items-center justify-center">
            <div className="border-t border-navy-800 w-full" />
            <span className="bg-navy-900 px-3 text-[11px] uppercase tracking-wider text-slate-500 font-semibold absolute">
              Or sign in manually
            </span>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
                  placeholder="••••••••"
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
              Sign In
            </Button>
          </form>

          <div className="text-center text-xs text-slate-400 pt-2 border-t border-navy-800">
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold text-teal-400 hover:text-teal-300 transition-colors">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
