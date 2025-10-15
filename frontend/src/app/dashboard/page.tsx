'use client';

import { useEffect, useMemo, useState } from 'react';
import AuthLayout from '@/components/layout/AuthLayout';
import { useAuthStore } from '@/lib/auth';
import apiClient, { AgentActivityEvent, AgentQueueAction } from '@/lib/api';
import { Calendar, MessageCircle, Users, HelpCircle, Heart, Activity, Bot, PlayCircle, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { motion } from 'framer-motion';
import { staggerContainer, staggerItem, pulse } from '@/lib/animations';

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

interface MessagePreview {
  _id: string;
  content: string;
  timestamp: string;
}

type PartnerStatusSummary = {
  partner?: {
    name?: string | null;
    [key: string]: unknown;
  } | null;
  [key: string]: unknown;
};

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [dailyQuestion, setDailyQuestion] = useState<DailyQuestion | null>(null);
  const [quizStatus, setQuizStatus] = useState<QuizStatus | null>(null);
  const [recentMessages, setRecentMessages] = useState<MessagePreview[]>([]);
  const [partnerStatus, setPartnerStatus] = useState<PartnerStatusSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [agentEvents, setAgentEvents] = useState<AgentActivityEvent[]>([]);
  const [agentPendingActions, setAgentPendingActions] = useState<AgentQueueAction[]>([]);
  const [agentRecentActions, setAgentRecentActions] = useState<AgentQueueAction[]>([]);
  const [agentStreamError, setAgentStreamError] = useState('');
  const [agentLastUpdate, setAgentLastUpdate] = useState<string | null>(null);

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
          const messageEntries = (Array.isArray(messages.value) ? messages.value : []) as Array<Record<string, unknown>>;
          const previews: MessagePreview[] = messageEntries.slice(0, 3).map((entry, index) => {
            const idValue = typeof entry['_id'] === 'string' ? (entry['_id'] as string) : `msg-${index}`;
            const contentValue = typeof entry['content'] === 'string' ? (entry['content'] as string) : '';
            const timestampValue =
              typeof entry['timestamp'] === 'string' ? (entry['timestamp'] as string) : new Date().toISOString();

            return {
              _id: idValue,
              content: contentValue,
              timestamp: timestampValue,
            };
          });
          setRecentMessages(previews);
          console.log('Dashboard: Messages loaded successfully');
        } else {
          console.log('Messages failed:', messages.reason?.response?.status, messages.reason?.message);
        }

        if (partner.status === 'fulfilled') {
          const partnerData = (partner.value ?? null) as PartnerStatusSummary | null;
          setPartnerStatus(partnerData);
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

  const pendingEventCount = useMemo(
    () => agentEvents.filter((event) => !event.processed).length,
    [agentEvents]
  );

  const executedCount = useMemo(
    () => agentRecentActions.filter((action) => action.status === 'executed').length,
    [agentRecentActions]
  );

  const acknowledgedCount = useMemo(
    () => agentRecentActions.filter((action) => action.status === 'acknowledged').length,
    [agentRecentActions]
  );

  const latestEvent = agentEvents.length > 0 ? agentEvents[0] : null;
  const pipelineStages = [
    {
      key: 'capture',
      title: 'Capture',
      description: 'Events waiting for review',
      count: pendingEventCount,
      total: agentEvents.length,
      icon: <Activity className="w-5 h-5 text-pink-600" />,
    },
    {
      key: 'plan',
      title: 'Plan',
      description: 'Automation plans pending',
      count: agentPendingActions.length,
      total: agentPendingActions.length,
      icon: <Bot className="w-5 h-5 text-purple-600" />,
    },
    {
      key: 'execute',
      title: 'Execute',
      description: 'Actions executed recently',
      count: executedCount,
      total: agentRecentActions.length,
      icon: <PlayCircle className="w-5 h-5 text-blue-600" />,
    },
    {
      key: 'feedback',
      title: 'Feedback',
      description: 'Actions acknowledged',
      count: acknowledgedCount,
      total: agentRecentActions.length,
      icon: <CheckCircle2 className="w-5 h-5 text-green-600" />,
    },
  ];

  useEffect(() => {
    if (!user || !user._id) {
      return;
    }

    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const fetchTelemetry = async () => {
      try {
        const [activityResult, queueResult] = await Promise.allSettled([
          apiClient.getAgentActivity({ limit: 15, includeProcessed: true }),
          apiClient.getAgentQueue(10, true),
        ]);

        if (!cancelled) {
          let telemetryError = '';

          if (activityResult.status === 'fulfilled') {
            setAgentEvents(activityResult.value.events || []);
            setAgentLastUpdate(new Date().toISOString());
          } else {
            telemetryError =
              activityResult.reason?.response?.data?.message ||
              activityResult.reason?.message ||
              'Failed to load agent activity';
          }

          if (queueResult.status === 'fulfilled') {
            setAgentPendingActions(queueResult.value.pending || []);
            setAgentRecentActions(queueResult.value.recent || []);
          } else if (!telemetryError) {
            telemetryError =
              queueResult.reason?.response?.data?.message ||
              queueResult.reason?.message ||
              'Failed to load agent queue';
          }

          setAgentStreamError(telemetryError);
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Agent telemetry unavailable';
          setAgentStreamError(message);
        }
      }
    };

    fetchTelemetry();
    intervalId = setInterval(fetchTelemetry, 10000);

    return () => {
      cancelled = true;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?._id]);

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
        {/* Welcome Section with fade-in animation */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="bg-gradient-to-r from-pink-500 to-purple-600 rounded-lg p-6 text-white"
        >
          <h1 className="text-2xl font-bold">
            {getGreeting()}, {user?.name}!
          </h1>
          <p className="mt-2 opacity-90">
            {partnerStatus?.partner
              ? `Connected with ${partnerStatus.partner.name}`
              : 'Ready to connect with your partner?'}
          </p>
        </motion.div>

        {/* Quick Stats with stagger animation */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          <motion.div
            variants={staggerItem}
            whileHover={{ y: -4, boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)' }}
            className="bg-white rounded-lg p-6 shadow-sm border cursor-pointer transition-shadow"
          >
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
          </motion.div>

          <motion.div
            variants={staggerItem}
            whileHover={{ y: -4, boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)' }}
            className="bg-white rounded-lg p-6 shadow-sm border cursor-pointer transition-shadow"
          >
            <div className="flex items-center">
              <div className="bg-blue-100 p-3 rounded-full">
                <MessageCircle className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Messages</p>
                <p className="text-2xl font-bold text-gray-900">{recentMessages.length}</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            variants={staggerItem}
            whileHover={{ y: -4, boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)' }}
            className="bg-white rounded-lg p-6 shadow-sm border cursor-pointer transition-shadow"
          >
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
          </motion.div>
        </motion.div>

        {/* Agent Operations Monitor */}
        <div className="bg-white rounded-lg p-6 shadow-sm border">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Agent Operations Monitor</h2>
              <p className="text-sm text-gray-500">
                Live view of how the Together Agent is processing your relationship signals.
              </p>
            </div>
            <div className="text-sm text-right">
              <div className="font-medium text-gray-700 flex items-center justify-end space-x-2">
                <span>Status:</span>
                {/* Animated pulse indicator */}
                <motion.div
                  variants={pulse}
                  initial="initial"
                  animate={!agentStreamError ? "animate" : "initial"}
                  className="w-2 h-2 bg-green-500 rounded-full"
                />
                <span className={agentStreamError ? 'text-red-600' : 'text-green-600'}>
                  {agentStreamError ? 'Degraded' : 'Online'}
                </span>
              </div>
              {agentLastUpdate && (
                <div className="text-gray-500 text-xs">
                  Updated {formatDistanceToNow(new Date(agentLastUpdate), { addSuffix: true })}
                </div>
              )}
            </div>
          </div>

          {agentStreamError ? (
            <div className="mt-4 p-4 border border-red-200 bg-red-50 text-red-600 rounded-md text-sm">
              {agentStreamError}
            </div>
          ) : (
            <div className="mt-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {pipelineStages.map((stage) => (
                  <div
                    key={stage.key}
                    className="border rounded-lg p-4 bg-white shadow-sm flex items-start space-x-3"
                  >
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-full ${
                        stage.count > 0 ? 'bg-pink-50' : 'bg-gray-100'
                      }`}
                    >
                      {stage.icon}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-gray-800">{stage.title}</h3>
                        <span
                          className={`text-xs font-medium ${
                            stage.count > 0 ? 'text-pink-600' : 'text-gray-400'
                          }`}
                        >
                          {stage.count}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{stage.description}</p>
                      {stage.total > 0 && (
                        <div className="mt-2 h-1.5 w-full rounded-full bg-gray-100">
                          <div
                            className="h-1.5 rounded-full bg-pink-500 transition-all duration-500"
                            style={{
                              width: `${Math.min(100, (stage.count / Math.max(stage.total, 1)) * 100)}%`,
                            }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-gray-800 mb-3">Latest Agent Events</h3>
                  {agentEvents.length === 0 ? (
                    <p className="text-sm text-gray-500">No agent events captured yet.</p>
                  ) : (
                    <ul className="space-y-3">
                      {agentEvents.slice(0, 6).map((event) => (
                        <li key={event._id} className="border rounded-md p-3 bg-gray-50">
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-medium text-gray-800 capitalize">
                              {event.event_type.replace(/_/g, ' ')}
                            </span>
                            <span className="text-xs text-gray-500">
                              {formatDistanceToNow(new Date(event.occurred_at), { addSuffix: true })}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Source: {event.source}
                            {event.processed ? ' · processed' : ' · pending'}
                          </p>
                          {event.payload && Object.keys(event.payload).length > 0 && (
                            <p className="text-xs text-gray-600 mt-1 truncate">
                              {event.payload.preview || event.payload.question || event.payload.title || JSON.stringify(event.payload)}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-800 mb-3">Automation Queue</h3>
                  {agentPendingActions.length === 0 && agentRecentActions.length === 0 ? (
                    <p className="text-sm text-gray-500">No automation steps queued right now.</p>
                  ) : (
                    <ul className="space-y-3">
                      {agentPendingActions.slice(0, 3).map((action) => (
                        <li key={action._id} className="border rounded-md p-3 bg-white shadow-sm">
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-medium text-gray-800">
                              {action.title || action.summary || 'Pending action'}
                            </span>
                            <div className="flex items-center space-x-2">
                              {action.llm_metadata?.model && (
                                <span className="text-[11px] font-semibold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full">
                                  {action.llm_metadata.model}
                                </span>
                              )}
                              <span className="text-xs text-orange-600">pending</span>
                            </div>
                          </div>
                          {action.created_at && (
                            <p className="text-xs text-gray-500 mt-1">
                              queued {formatDistanceToNow(new Date(action.created_at), { addSuffix: true })}
                            </p>
                          )}
                        </li>
                      ))}
                      {agentRecentActions
                        .filter((action) => action.status !== 'pending')
                        .slice(0, 3)
                        .map((action) => (
                          <li key={action._id} className="border rounded-md p-3 bg-gray-50">
                            <div className="flex items-center justify-between text-sm">
                              <span className="font-medium text-gray-800">
                                {action.title || action.summary || 'Completed action'}
                              </span>
                              <div className="flex items-center space-x-2">
                                {action.llm_metadata?.model && (
                                  <span className="text-[11px] font-semibold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full">
                                    {action.llm_metadata.model}
                                  </span>
                                )}
                                <span className="text-xs text-green-600">{action.status}</span>
                              </div>
                            </div>
                            {action.updated_at && (
                              <p className="text-xs text-gray-500 mt-1">
                                updated {formatDistanceToNow(new Date(action.updated_at), { addSuffix: true })}
                              </p>
                            )}
                          </li>
                        ))}
                    </ul>
                  )}
                </div>
              </div>

              {latestEvent && (
                <div className="border border-dashed border-pink-200 rounded-lg p-4 bg-pink-50 text-sm text-pink-700">
                  <span className="font-semibold">Latest trigger:</span> {latestEvent.event_type.replace(/_/g, ' ')} ·{' '}
                  {formatDistanceToNow(new Date(latestEvent.occurred_at), { addSuffix: true })}
                </div>
              )}
            </div>
          )}
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
