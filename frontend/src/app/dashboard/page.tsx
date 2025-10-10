'use client';

import { useEffect, useState } from 'react';
import AuthLayout from '@/components/layout/AuthLayout';
import { useAuthStore } from '@/lib/auth';
import apiClient from '@/lib/api';
import { Calendar, MessageCircle, Users, HelpCircle, Heart } from 'lucide-react';
import Link from 'next/link';

interface DailyQuestion {
  _id: string;
  question: string;
  date: string;
}

interface QuizStatus {
  overall_score: number;
  total_answered: number;
  match_percentage: number;
}

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [dailyQuestion, setDailyQuestion] = useState<DailyQuestion | null>(null);
  const [quizStatus, setQuizStatus] = useState<QuizStatus | null>(null);
  const [recentMessages, setRecentMessages] = useState<any[]>([]);
  const [partnerStatus, setPartnerStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        console.log('Dashboard: Fetching data for user:', user?._id);

        // Double-check token is available before making API calls
        const token = localStorage.getItem('token');
        if (!token || token === 'undefined') {
          console.log('Dashboard: No token available, skipping API calls');
          setLoading(false);
          return;
        }

        console.log('Dashboard: Token available, making API calls');
        const [dailyQ, quiz, messages, partner] = await Promise.allSettled([
          apiClient.getDailyQuestion(),
          apiClient.getQuizStatus(),
          apiClient.getMessages(),
          apiClient.getPartnerStatus(),
        ]);

        if (dailyQ.status === 'fulfilled') {
          setDailyQuestion(dailyQ.value);
          console.log('Dashboard: Daily question loaded successfully');
        } else {
          console.log('Daily question failed:', dailyQ.reason?.response?.status, dailyQ.reason?.message);
        }

        if (quiz.status === 'fulfilled') {
          setQuizStatus(quiz.value);
          console.log('Dashboard: Quiz status loaded successfully');
        } else {
          console.log('Quiz status failed:', quiz.reason?.response?.status, quiz.reason?.message);
        }

        if (messages.status === 'fulfilled') {
          setRecentMessages(messages.value.slice(0, 3));
          console.log('Dashboard: Messages loaded successfully');
        } else {
          console.log('Messages failed:', messages.reason?.response?.status, messages.reason?.message);
        }

        if (partner.status === 'fulfilled') {
          setPartnerStatus(partner.value);
          console.log('Dashboard: Partner status loaded successfully');
        } else {
          console.log('Partner status failed:', partner.reason?.response?.status, partner.reason?.message);
        }
      } catch (error) {
        console.error('Dashboard data fetch error:', error);
      } finally {
        setLoading(false);
      }
    };

    // Only fetch if we have a user and token
    if (user && user._id) {
      // Add a small delay to ensure token is fully synchronized
      const timeoutId = setTimeout(() => {
        fetchDashboardData();
      }, 100);

      return () => clearTimeout(timeoutId);
    } else {
      console.log('Dashboard: Waiting for user data...');
      setLoading(false);
    }
  }, [user]);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  if (loading) {
    return (
      <AuthLayout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <div className="space-y-6">
        {/* Welcome Section */}
        <div className="bg-gradient-to-r from-pink-500 to-purple-600 rounded-lg p-6 text-white">
          <h1 className="text-2xl font-bold">
            {getGreeting()}, {user?.name}!
          </h1>
          <p className="mt-2 opacity-90">
            {partnerStatus?.partner
              ? `Connected with ${partnerStatus.partner.name}`
              : 'Ready to connect with your partner?'}
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg p-6 shadow-sm border">
            <div className="flex items-center">
              <div className="bg-pink-100 p-3 rounded-full">
                <Heart className="w-6 h-6 text-pink-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Quiz Match</p>
                <p className="text-2xl font-bold text-gray-900">
                  {quizStatus?.match_percentage || 0}%
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg p-6 shadow-sm border">
            <div className="flex items-center">
              <div className="bg-blue-100 p-3 rounded-full">
                <MessageCircle className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Messages</p>
                <p className="text-2xl font-bold text-gray-900">{recentMessages.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg p-6 shadow-sm border">
            <div className="flex items-center">
              <div className="bg-green-100 p-3 rounded-full">
                <Users className="w-6 h-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Partner Status</p>
                <p className="text-2xl font-bold text-gray-900">
                  {partnerStatus?.partner ? 'Connected' : 'Pending'}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily Question */}
          <div className="bg-white rounded-lg p-6 shadow-sm border">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Today's Question</h2>
              <HelpCircle className="w-5 h-5 text-gray-400" />
            </div>
            {dailyQuestion ? (
              <div>
                <p className="text-gray-700 mb-4">{dailyQuestion.question}</p>
                <Link
                  href="/daily-questions"
                  className="inline-flex items-center text-sm text-pink-600 hover:text-pink-700"
                >
                  Answer question →
                </Link>
              </div>
            ) : (
              <p className="text-gray-500">No question available today</p>
            )}
          </div>

          {/* Recent Messages */}
          <div className="bg-white rounded-lg p-6 shadow-sm border">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Recent Messages</h2>
              <MessageCircle className="w-5 h-5 text-gray-400" />
            </div>
            {recentMessages.length > 0 ? (
              <div className="space-y-3">
                {recentMessages.map((message, index) => (
                  <div key={index} className="text-sm">
                    <p className="text-gray-700 truncate">{message.content}</p>
                    <p className="text-gray-400 text-xs mt-1">
                      {new Date(message.timestamp).toLocaleDateString()}
                    </p>
                  </div>
                ))}
                <Link
                  href="/messages"
                  className="inline-flex items-center text-sm text-pink-600 hover:text-pink-700"
                >
                  View all messages →
                </Link>
              </div>
            ) : (
              <p className="text-gray-500">No messages yet</p>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg p-6 shadow-sm border">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Link
              href="/calendar"
              className="flex flex-col items-center p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <Calendar className="w-8 h-8 text-blue-600 mb-2" />
              <span className="text-sm font-medium text-gray-700">Calendar</span>
            </Link>

            <Link
              href="/messages"
              className="flex flex-col items-center p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <MessageCircle className="w-8 h-8 text-green-600 mb-2" />
              <span className="text-sm font-medium text-gray-700">Messages</span>
            </Link>

            <Link
              href="/quiz"
              className="flex flex-col items-center p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <HelpCircle className="w-8 h-8 text-purple-600 mb-2" />
              <span className="text-sm font-medium text-gray-700">Quiz</span>
            </Link>

            <Link
              href="/partner"
              className="flex flex-col items-center p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <Users className="w-8 h-8 text-pink-600 mb-2" />
              <span className="text-sm font-medium text-gray-700">Partner</span>
            </Link>
          </div>
        </div>
      </div>
    </AuthLayout>
  );
}