'use client';

import { useState, useEffect } from 'react';
import AuthLayout from '@/components/layout/AuthLayout';
import apiClient from '@/lib/api';
import { HelpCircle, CheckCircle2, Send } from 'lucide-react';

interface QuizQuestion {
  id: number;
  question: string;
  type: string;
  options?: string[];
}

interface QuizStatus {
  has_taken_quiz: boolean;
  quiz_count: number;
  latest_quiz_date: string | null;
  available_questions: number;
}

export default function QuizPage() {
  const [quizStatus, setQuizStatus] = useState<QuizStatus | null>(null);
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [answers, setAnswers] = useState<{ [key: number]: string }>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadQuizData();
  }, []);

  const loadQuizData = async () => {
    setLoading(true);
    setError('');
    try {
      const [statusData, questionsData] = await Promise.all([
        apiClient.getQuizStatus(),
        apiClient.getQuizQuestions(),
      ]);

      setQuizStatus(statusData);
      setQuestions(questionsData.questions || []);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load quiz data');
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (questionId: number, answer: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: answer }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');

    try {
      // Format answers for API
      const formattedAnswers = questions.map(q => ({
        question_id: q.id,
        answer: answers[q.id] || '',
      }));

      const result = await apiClient.submitQuiz(formattedAnswers);
      setResults(result);
      setShowResults(true);
      await loadQuizData(); // Refresh status
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to submit quiz');
    } finally {
      setSubmitting(false);
    }
  };

  const startNewQuiz = () => {
    setAnswers({});
    setShowResults(false);
    setResults(null);
    setError('');
  };

  const allQuestionsAnswered = questions.length > 0 &&
    questions.every(q => answers[q.id] && answers[q.id].trim() !== '');

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
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Compatibility Quiz</h1>
          <p className="mt-2 text-sm text-gray-600">
            Answer questions about your partner to see how well you know them.
          </p>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md">
            {error}
          </div>
        )}

        {/* Quiz Stats */}
        {quizStatus && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="grid grid-cols-2 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-gray-900">{quizStatus.quiz_count}</div>
                <p className="text-sm text-gray-600">Quizzes Taken</p>
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">{quizStatus.available_questions}</div>
                <p className="text-sm text-gray-600">Total Questions</p>
              </div>
            </div>
            {quizStatus.latest_quiz_date && (
              <div className="mt-4 text-center text-sm text-gray-500">
                Last taken: {new Date(quizStatus.latest_quiz_date).toLocaleDateString()}
              </div>
            )}
          </div>
        )}

        {showResults ? (
          /* Show Results */
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="text-center mb-6">
              <CheckCircle2 className="w-12 h-12 text-green-600 mx-auto mb-4" />
              <h2 className="text-xl font-bold text-gray-900">Quiz Submitted!</h2>
              <p className="text-gray-600">
                Your answers have been recorded successfully.
              </p>
            </div>

            <div className="text-center">
              <button
                onClick={startNewQuiz}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-pink-600 hover:bg-pink-700"
              >
                <HelpCircle className="w-4 h-4 mr-2" />
                Take Quiz Again
              </button>
            </div>
          </div>
        ) : (
          /* Show Quiz Questions */
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="space-y-6">
              {questions.map((question, index) => (
                <div key={question.id} className="border-b border-gray-200 pb-6 last:border-b-0">
                  <label className="block mb-3">
                    <span className="text-sm font-medium text-gray-700">
                      {index + 1}. {question.question}
                    </span>
                  </label>

                  {question.type === 'multiple_choice' && question.options ? (
                    <div className="space-y-2">
                      {question.options.map((option, optIndex) => (
                        <label key={optIndex} className="flex items-center cursor-pointer">
                          <input
                            type="radio"
                            name={`question-${question.id}`}
                            value={option}
                            checked={answers[question.id] === option}
                            onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                            className="h-4 w-4 text-pink-600 border-gray-300 focus:ring-pink-500"
                          />
                          <span className="ml-3 text-gray-700">{option}</span>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <input
                      type="text"
                      value={answers[question.id] || ''}
                      onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-pink-500 focus:border-pink-500 text-gray-900"
                      placeholder="Your answer..."
                    />
                  )}
                </div>
              ))}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={handleSubmit}
                disabled={!allQuestionsAnswered || submitting}
                className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-pink-600 hover:bg-pink-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4 mr-2" />
                {submitting ? 'Submitting...' : 'Submit Quiz'}
              </button>
            </div>
          </div>
        )}
      </div>
    </AuthLayout>
  );
}
