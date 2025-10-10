'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  BarChart2,
  CheckCircle2,
  Hourglass,
  RefreshCw,
  Send,
  ThumbsUp,
  Users,
} from 'lucide-react';

import AuthLayout from '@/components/layout/AuthLayout';
import apiClient from '@/lib/api';

interface QuizStatus {
  total_sessions: number;
  completed_sessions: number;
  active_session_id: string | null;
  last_score: number | null;
  last_completed_at: string | null;
  average_score: number | null;
  question_bank_size: number;
  default_batch_sizes: number[];
}

interface QuizSessionQuestion {
  id: number;
  question: string;
  options: string[];
  category?: string;
  your_answer?: string | null;
  partner_answer?: string | null;
  is_match?: boolean;
}

interface QuizSessionProgress {
  your_answers: number;
  partner_answers: number;
  total_questions: number;
  awaiting_partner_for: number[];
}

interface QuizCompatibilitySummary {
  matches: number;
  total: number;
  score: number;
  completed_at?: string;
}

interface QuizSession {
  id: string;
  status: 'in_progress' | 'completed';
  created_at?: string;
  question_count: number;
  questions: QuizSessionQuestion[];
  progress: QuizSessionProgress;
  compatibility?: QuizCompatibilitySummary | null;
  partner?: {
    _id: string;
    name?: string;
    email?: string;
  } | null;
  created?: boolean;
  completed?: boolean;
}

interface QuestionBankResponse {
  questions: QuizSessionQuestion[];
  total_questions: number;
  default_batch_sizes: number[];
}

const FALLBACK_BATCH_SIZES = [10, 15, 20];

export default function QuizPage() {
  const [quizStatus, setQuizStatus] = useState<QuizStatus | null>(null);
  const [questionBank, setQuestionBank] = useState<QuizSessionQuestion[]>([]);
  const [batchSizes, setBatchSizes] = useState<number[]>(FALLBACK_BATCH_SIZES);
  const [session, setSession] = useState<QuizSession | null>(null);

  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [answering, setAnswering] = useState(false);

  const [error, setError] = useState('');
  const [selectedCount, setSelectedCount] = useState<number>(FALLBACK_BATCH_SIZES[0]);
  const [customCount, setCustomCount] = useState('');
  const [selectedAnswer, setSelectedAnswer] = useState('');

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (session?.status === 'in_progress') {
      const awaiting = session.progress?.awaiting_partner_for?.length ?? 0;
      if (awaiting > 0) {
        const poller = setInterval(() => {
          refreshSession(session.id);
        }, 5000);
        return () => clearInterval(poller);
      }
    }
  }, [session?.id, session?.status, session?.progress?.awaiting_partner_for?.length]);

  useEffect(() => {
    setSelectedAnswer('');
  }, [session?.id, session?.progress?.your_answers]);

  const loadInitialData = async () => {
    setLoading(true);
    setError('');

    try {
      const [statusData, questionData, activeData] = await Promise.all([
        apiClient.getQuizStatus(),
        apiClient.getQuizQuestionBank(),
        apiClient.getActiveQuizSession(),
      ]);

      if (statusData) {
        setQuizStatus(statusData);
        if (statusData.default_batch_sizes?.length) {
          setBatchSizes(statusData.default_batch_sizes);
          setSelectedCount(statusData.default_batch_sizes[0]);
        }
      }

      if (questionData) {
        setQuestionBank(questionData.questions || []);
        if (!statusData?.default_batch_sizes?.length && questionData.default_batch_sizes?.length) {
          setBatchSizes(questionData.default_batch_sizes);
          setSelectedCount(questionData.default_batch_sizes[0]);
        }
      }

      if (activeData?.session) {
        setSession(activeData.session);
      } else {
        setSession(null);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || 'Failed to load quiz data');
    } finally {
      setLoading(false);
    }
  };

  const refreshStatus = useCallback(async () => {
    try {
      const status = await apiClient.getQuizStatus();
      if (status) {
        setQuizStatus(status);
      }
    } catch (err) {
      console.error('Failed to refresh quiz status', err);
    }
  }, []);

  const refreshSession = useCallback(
    async (sessionId?: string) => {
      const targetId = sessionId || session?.id;
      if (!targetId) return;

      try {
        const response = await apiClient.getQuizSession(targetId);
        if (response?.session) {
          setSession(response.session);
        }
      } catch (err) {
        console.error('Failed to refresh session', err);
      }
    },
    [session?.id]
  );

  const handleStartSession = async () => {
    let desiredCount = selectedCount;

    if (customCount) {
      const parsed = parseInt(customCount, 10);
      if (Number.isNaN(parsed) || parsed < 1) {
        setError('Please enter a valid number of questions (at least 1).');
        return;
      }
      desiredCount = parsed;
    }

    setStarting(true);
    setError('');

    try {
      const response = await apiClient.startQuizSession(desiredCount);
      if (response) {
        const { created, ...sessionData } = response;
        setSession(sessionData as QuizSession);
        setSelectedAnswer('');
        setCustomCount('');
        await refreshStatus();
      }
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || 'Failed to start session');
    } finally {
      setStarting(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!session || !currentQuestion || !selectedAnswer) return;

    setAnswering(true);
    setError('');

    try {
      const response = await apiClient.submitQuizAnswer(session.id, currentQuestion.id, selectedAnswer);
      if (response?.session) {
        setSession(response.session);
      }
      setSelectedAnswer('');
      await refreshStatus();
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || 'Failed to submit answer');
    } finally {
      setAnswering(false);
    }
  };

  const handleRefreshClick = async () => {
    await refreshSession();
    await refreshStatus();
  };

  const handleStartAnother = async () => {
    setSession(null);
    await refreshStatus();
  };

  const currentQuestion = useMemo(() => {
    if (!session || session.status !== 'in_progress') return null;
    return session.questions.find((q) => !q.your_answer);
  }, [session]);

  const awaitingPartner = session?.progress?.awaiting_partner_for ?? [];
  const isWaitingForPartner =
    session?.status === 'in_progress' &&
    awaitingPartner.length > 0 &&
    session.progress.your_answers === session.progress.total_questions;

  const compatibility = session?.compatibility;

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
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Compatibility Sessions</h1>
            <p className="mt-2 text-sm text-gray-600">
              Answer quick-fire questions with your partner and discover how your preferences align in real time.
            </p>
          </div>
          <button
            onClick={handleRefreshClick}
            className="inline-flex items-center px-3 py-2 text-sm font-medium rounded-md text-blue-600 hover:text-blue-800"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md">{error}</div>
        )}

        {quizStatus && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm text-gray-500">Sessions completed</h3>
                  <p className="mt-1 text-2xl font-semibold text-gray-900">
                    {quizStatus.completed_sessions}
                  </p>
                </div>
                <CheckCircle2 className="w-8 h-8 text-green-500" />
              </div>
              {quizStatus.last_completed_at && (
                <p className="mt-3 text-xs text-gray-500">
                  Last finished {formatDistanceToNow(new Date(quizStatus.last_completed_at), { addSuffix: true })}
                </p>
              )}
            </div>

            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm text-gray-500">Average compatibility</h3>
                  <p className="mt-1 text-2xl font-semibold text-gray-900">
                    {quizStatus.average_score !== null ? `${quizStatus.average_score}%` : '—'}
                  </p>
                </div>
                <BarChart2 className="w-8 h-8 text-pink-500" />
              </div>
              <p className="mt-3 text-xs text-gray-500">
                Question pool: {quizStatus.question_bank_size} prompts
              </p>
            </div>
          </div>
        )}

        {session ? (
          <div className="space-y-6">
            <div className="bg-white border rounded-lg shadow-sm">
              <div className="border-b border-gray-200 px-4 py-3 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Active session</h2>
                  <p className="text-sm text-gray-600">
                    {session.partner?.name ? `Partner: ${session.partner.name}` : 'Waiting for partner details'}
                  </p>
                </div>
                <div className="text-sm text-gray-500">
                  {session.progress.your_answers}/{session.progress.total_questions} answered
                </div>
              </div>

              <div className="p-4 space-y-4">
                {session.status === 'completed' && compatibility ? (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-green-700">Compatibility score</h3>
                        <p className="text-2xl font-bold text-green-800 mt-2">{compatibility.score}%</p>
                        <p className="text-sm text-green-700 mt-1">
                          {compatibility.matches} of {compatibility.total} answers matched
                        </p>
                      </div>
                      <ThumbsUp className="w-10 h-10 text-green-500" />
                    </div>
                    <div className="mt-4 flex items-center justify-between">
                      <button
                        onClick={handleStartAnother}
                        className="inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-pink-600 rounded-md hover:bg-pink-700"
                      >
                        Start another session
                      </button>
                      {compatibility.completed_at && (
                        <p className="text-xs text-green-700">
                          Completed {formatDistanceToNow(new Date(compatibility.completed_at), { addSuffix: true })}
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <>
                    {currentQuestion ? (
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                          Next question
                        </h3>
                        <p className="mt-3 text-lg text-gray-900">{currentQuestion.question}</p>
                        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {currentQuestion.options.map((option) => (
                            <button
                              key={option}
                              type="button"
                              onClick={() => setSelectedAnswer(option)}
                              className={`px-4 py-2 border rounded-md text-sm font-medium transition ${
                                selectedAnswer === option
                                  ? 'bg-pink-600 text-white border-pink-600'
                                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'
                              }`}
                            >
                              {option}
                            </button>
                          ))}
                        </div>
                        <div className="mt-4 flex justify-end">
                          <button
                            onClick={handleSubmitAnswer}
                            disabled={!selectedAnswer || answering}
                            className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-pink-600 rounded-md hover:bg-pink-700 disabled:opacity-50"
                          >
                            <Send className="w-4 h-4 mr-2" />
                            {answering ? 'Submitting...' : 'Lock in answer'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
                        <div className="flex items-center">
                          <Hourglass className="w-6 h-6 text-blue-600 mr-3" />
                          <div>
                            <h3 className="text-sm font-semibold text-blue-700">Waiting for your partner</h3>
                            <p className="text-sm text-blue-600">
                              {awaitingPartner.length} {awaitingPartner.length === 1 ? 'question is' : 'questions are'} awaiting their answer.
                            </p>
                          </div>
                        </div>
                        <Users className="w-6 h-6 text-blue-600" />
                      </div>
                    )}
                  </>
                )}

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">Session timeline</h3>
                  <div className="space-y-2">
                    {session.questions.map((question, index) => {
                      const isAnswered = Boolean(question.your_answer);
                      const partnerAnswered = Boolean(question.partner_answer);
                      const statusColor = question.is_match
                        ? 'text-green-600 bg-green-50 border-green-200'
                        : partnerAnswered && !question.is_match
                          ? 'text-yellow-700 bg-yellow-50 border-yellow-200'
                          : 'text-gray-700 bg-white border-gray-200';

                      return (
                        <div
                          key={question.id}
                          className={`border rounded-md px-3 py-2 text-sm ${statusColor}`}
                        >
                          <div className="flex justify-between">
                            <span className="font-medium">
                              {index + 1}. {question.question}
                            </span>
                            {question.is_match && <CheckCircle2 className="w-5 h-5 text-green-500" />}
                          </div>
                          <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                            <p>
                              <span className="font-semibold">You:</span>{' '}
                              {isAnswered ? question.your_answer : 'Not answered yet'}
                            </p>
                            <p>
                              <span className="font-semibold">Partner:</span>{' '}
                              {partnerAnswered ? question.partner_answer : 'Waiting...'}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white border rounded-lg shadow-sm p-6 space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Start a new session</h2>
              <p className="mt-1 text-sm text-gray-600">
                Pick how many prompts you want to answer together. You can always come back for another round.
              </p>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">Quick-select</label>
              <div className="mt-2 flex flex-wrap gap-2">
                {batchSizes.map((size) => (
                  <button
                    key={size}
                    type="button"
                    onClick={() => {
                      setSelectedCount(size);
                      setCustomCount('');
                    }}
                    className={`px-3 py-2 rounded-md border text-sm font-medium ${
                      selectedCount === size && !customCount
                        ? 'bg-pink-600 text-white border-pink-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'
                    }`}
                  >
                    {size} questions
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="customCount" className="text-sm font-medium text-gray-700">
                Custom count
              </label>
              <div className="mt-1 flex">
                <input
                  id="customCount"
                  type="number"
                  min={1}
                  placeholder="Choose your own"
                  value={customCount}
                  onChange={(e) => setCustomCount(e.target.value)}
                  className="w-40 px-3 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-pink-500 focus:border-pink-500 text-gray-900 bg-white"
                />
                <button
                  type="button"
                  onClick={() => {
                    setSelectedCount(selectedCount);
                    setCustomCount('');
                  }}
                  className="px-3 py-2 border border-gray-300 rounded-r-md text-sm text-gray-600 hover:bg-gray-50"
                >
                  Clear
                </button>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Question pool currently includes {questionBank.length} curated prompts.
              </p>
            </div>

            <button
              onClick={handleStartSession}
              disabled={starting}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-pink-600 hover:bg-pink-700 disabled:opacity-50"
            >
              <Users className="w-4 h-4 mr-2" />
              {starting ? 'Creating session...' : 'Start compatibility session'}
            </button>
          </div>
        )}
      </div>
    </AuthLayout>
  );
}
