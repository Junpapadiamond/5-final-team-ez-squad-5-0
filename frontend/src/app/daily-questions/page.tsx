'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import AuthLayout from '@/components/layout/AuthLayout';
import { useAuthStore } from '@/lib/auth';
import apiClient from '@/lib/api';
import { MessageCircle, Send, Calendar, Users } from 'lucide-react';
import { format } from 'date-fns';

interface AnswerForm {
  answer: string;
}

interface DailyQuestion {
  question: string;
  date: string;
  answered?: boolean;
  answer?: string | null;
}

interface DailyAnswer {
  _id: string;
  user_id: string;
  user_name?: string;
  question: string;
  answer: string;
  answered: boolean;
  answered_at?: string | null;
  question_date?: string;
}

interface DailyAnswers {
  question: DailyQuestion | null;
  your_answer: DailyAnswer | null;
  partner_answer: DailyAnswer | null;
  both_answered: boolean;
}

export default function DailyQuestionsPage() {
  const { user } = useAuthStore();
  const [currentQuestion, setCurrentQuestion] = useState<DailyQuestion | null>(null);
  const [answers, setAnswers] = useState<DailyAnswers | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<AnswerForm>({
    defaultValues: { answer: '' },
  });

  useEffect(() => {
    loadDailyQuestion();
    loadDailyAnswers();
  }, []);

  const loadDailyQuestion = async () => {
    try {
      const question = await apiClient.getDailyQuestion();
      setCurrentQuestion(question);
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError("Failed to load today's question");
      }
    }
  };

  const loadDailyAnswers = async () => {
    try {
      const answersData = await apiClient.getDailyAnswers();
      setAnswers(answersData);
    } catch (err: any) {
      console.error('Failed to load answers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (answers?.your_answer?.answered) {
      reset({ answer: answers.your_answer.answer || '' });
    } else {
      reset({ answer: '' });
    }
  }, [answers?.your_answer?.answered, answers?.your_answer?.answer, reset]);

  const onAnswerSubmit = async (data: AnswerForm) => {
    setSubmitting(true);
    setError('');
    setMessage('');

    try {
      const trimmedAnswer = data.answer.trim();
      if (!trimmedAnswer) {
        setError('Please provide an answer');
        setSubmitting(false);
        return;
      }

      const alreadyAnswered = Boolean(answers?.your_answer?.answered);

      await apiClient.answerDailyQuestion(trimmedAnswer);
      setMessage(alreadyAnswered ? 'Your answer has been updated!' : 'Your answer has been submitted!');

      await Promise.all([loadDailyAnswers(), loadDailyQuestion()]);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to submit answer');
    } finally {
      setSubmitting(false);
    }
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
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Daily Questions</h1>
          <p className="mt-2 text-sm text-gray-600">
            Answer daily questions to learn more about each other.
          </p>
        </div>

        {message && (
          <div className="p-4 bg-green-50 border border-green-200 text-green-700 rounded-md">
            {message}
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md">
            {error}
          </div>
        )}

        {/* Today's Question */}
        {currentQuestion && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center mb-4">
              <div className="bg-pink-100 p-2 rounded-full mr-3">
                <MessageCircle className="w-5 h-5 text-pink-600" />
              </div>
              <div>
                <h2 className="text-lg font-medium text-gray-900">Today's Question</h2>
                <p className="text-sm text-gray-500">
                  {format(new Date(currentQuestion.date), 'MMMM dd, yyyy')}
                </p>
              </div>
            </div>

            <div className="mb-6">
              <p className="text-lg text-gray-900 leading-relaxed">
                {currentQuestion.question}
              </p>
            </div>

            <form onSubmit={handleSubmit(onAnswerSubmit)} className="space-y-4">
              {answers?.your_answer?.answered && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800 flex items-start">
                  <div className="bg-green-100 p-1 rounded-full mr-2 mt-0.5">
                    <MessageCircle className="w-4 h-4 text-green-600" />
                  </div>
                  <div>
                    <p>You can update your answer anytime today.</p>
                    {answers.your_answer.answered_at && (
                      <p className="text-green-700 mt-1">
                        Last updated {format(new Date(answers.your_answer.answered_at), 'MMM dd, yyyy • h:mm a')}.
                      </p>
                    )}
                  </div>
                </div>
              )}

              <div>
                <label htmlFor="answer" className="block text-sm font-medium text-gray-700">
                  {answers?.your_answer?.answered ? 'Update your answer' : 'Your Answer'}
                </label>
                <textarea
                  id="answer"
                  rows={4}
                  {...register('answer', {
                    required: 'Please provide an answer',
                    maxLength: {
                      value: 500,
                      message: 'Answer must be less than 500 characters',
                    },
                  })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-pink-500 focus:border-pink-500"
                  placeholder="Share your thoughts..."
                />
                {errors.answer && (
                  <p className="mt-1 text-sm text-red-600">{errors.answer.message}</p>
                )}
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-pink-600 hover:bg-pink-700 disabled:opacity-50"
                >
                  <Send className="w-4 h-4 mr-2" />
                  {submitting
                    ? answers?.your_answer?.answered
                      ? 'Updating...'
                      : 'Submitting...'
                    : answers?.your_answer?.answered
                      ? 'Update Answer'
                      : 'Submit Answer'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Answers Display */}
        {answers && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center mb-6">
              <Users className="w-5 h-5 text-blue-600 mr-2" />
              <h2 className="text-lg font-medium text-gray-900">Your Answers</h2>
            </div>

            <div className="space-y-6">
              {/* Your Answer */}
              {answers.your_answer ? (
                <div className="bg-pink-50 rounded-lg p-4">
                  <div className="flex items-center mb-3">
                    <div className="bg-pink-100 p-2 rounded-full mr-3">
                      <div className="w-4 h-4 bg-pink-600 rounded-full"></div>
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">Your Answer</h3>
                      {answers.your_answer.answered_at && (
                        <p className="text-sm text-gray-500">
                          {format(new Date(answers.your_answer.answered_at), 'MMM dd, yyyy • h:mm a')}
                        </p>
                      )}
                    </div>
                  </div>
                  <p className="text-gray-800 leading-relaxed pl-10">
                    {answers.your_answer.answer}
                  </p>
                </div>
              ) : (
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                  <MessageCircle className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-gray-500">You haven't answered today's question yet.</p>
                </div>
              )}

              {/* Partner Answer */}
              {answers.partner_answer ? (
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-center mb-3">
                    <div className="bg-blue-100 p-2 rounded-full mr-3">
                      <div className="w-4 h-4 bg-blue-600 rounded-full"></div>
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">
                        {answers.partner_answer.user_name}'s Answer
                      </h3>
                      {answers.partner_answer.answered_at && (
                        <p className="text-sm text-gray-500">
                          {format(new Date(answers.partner_answer.answered_at), 'MMM dd, yyyy • h:mm a')}
                        </p>
                      )}
                    </div>
                  </div>
                  <p className="text-gray-800 leading-relaxed pl-10">
                    {answers.partner_answer.answer}
                  </p>
                </div>
              ) : (
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                  <Users className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-gray-500">Your partner hasn't answered today's question yet.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* No Question Available */}
        {!currentQuestion && !loading && (
          <div className="bg-white rounded-lg shadow-sm border p-6 text-center">
            <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">No Question Today</h2>
            <p className="text-gray-600">
              Check back tomorrow for a new daily question to answer with your partner!
            </p>
          </div>
        )}

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <MessageCircle className="w-5 h-5 text-blue-400" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">How it works</h3>
              <div className="mt-2 text-sm text-blue-700">
                <ul className="list-disc list-inside space-y-1">
                  <li>A new question is posted each day</li>
                  <li>Both you and your partner can answer independently</li>
                  <li>Once both have answered, you can see each other's responses</li>
                  <li>Use these questions to spark deeper conversations</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AuthLayout>
  );
}
