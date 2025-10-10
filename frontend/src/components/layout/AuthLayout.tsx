'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import Navbar from './Navbar';

interface AuthLayoutProps {
  children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  const router = useRouter();
  const { user, token, setUser, setToken } = useAuthStore();

  useEffect(() => {
    const checkAuth = () => {
      // Check for stored auth data on mount
      const storedUser = localStorage.getItem('user');
      const storedToken = localStorage.getItem('token');

      console.log('AuthLayout: Checking stored auth data:', {
        hasStoredUser: !!storedUser,
        hasStoredToken: !!storedToken,
        currentUser: !!user,
        currentToken: !!token
      });

      if (storedUser && storedToken && storedUser !== 'undefined' && storedToken !== 'undefined') {
        try {
          const parsedUser = JSON.parse(storedUser);
          // Only set if different from current state to prevent loops
          if (!user || !token || JSON.stringify(user) !== storedUser || token !== storedToken) {
            console.log('AuthLayout: Setting user and token from localStorage');
            setUser(parsedUser);
            setToken(storedToken);
          }
        } catch (error) {
          console.error('Error parsing stored user data:', error);
          // Clear invalid data
          localStorage.removeItem('user');
          localStorage.removeItem('token');
          router.push('/login');
        }
      } else if (!user || !token) {
        // Only redirect if we're not already on login page to prevent loops
        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
          console.log('AuthLayout: No auth data found, redirecting to login');
          router.push('/login');
        }
      }
    };

    // Check immediately
    checkAuth();

    // Also listen for storage events to sync across tabs
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'token' || e.key === 'user') {
        console.log('AuthLayout: Storage changed for', e.key);
        checkAuth();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []); // Empty dependency array - only run on mount

  if (!user || !token) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-pink-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}