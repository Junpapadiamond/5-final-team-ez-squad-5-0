'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import AuthLayout from '@/components/layout/AuthLayout';
import { useAuthStore } from '@/lib/auth';
import apiClient from '@/lib/api';
import {
  Sparkles,
  RefreshCcw,
  MessageCircle,
  Calendar,
  ClipboardList,
  Bot,
  Gauge,
  AlertCircle,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface StyleProfile {
  style_summary?: string;
  emoji_frequency?: Array<{ emoji: string; count: number }>;
  top_words?: Array<{ word: string; count: number }>;
  signature_examples?: string[];
  message_count?: number;
  updated_at?: string;
  cached?: boolean;
}

interface SuggestionCard {
  id: string;
  type: string;
  title: string;
  summary: string;
  confidence?: number;
  generated_at?: string;
  payload?: Record<string, unknown>;
}

interface AgentAnalysisMetrics {
  length: {
    characters: number;
    words: number;
  };
  emoji_count: number;
  punctuation: Record<string, number>;
  sentiment: string;
  sentiment_probability_positive: number;
  keywords: string[];
}

interface AgentAnalysisResult {
  analysis: AgentAnalysisMetrics;
  strengths: string[];
  tips: string[];
  style_profile?: Record<string, unknown>;
  llm_feedback?: string | null;
  generated_at?: string;
}

const iconForType: Record<string, JSX.Element> = {
  message_draft: <MessageCircle className="w-5 h-5 text-pink-600" />,
  daily_question: <ClipboardList className="w-5 h-5 text-blue-600" />,
  calendar: <Calendar className="w-5 h-5 text-purple-600" />,
};

export default function AgentPage() {
  const { user } = useAuthStore();
  const [styleProfile, setStyleProfile] = useState<StyleProfile | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestionCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [sampleMessage, setSampleMessage] = useState('');
  const [analysis, setAnalysis] = useState<AgentAnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState('');
  const [analyzing, setAnalyzing] = useState(false);

  const loadData = async (force = false) => {
    setRefreshing(true);
    setError('');
    try {
      const [profile, suggestionList] = await Promise.all([
        apiClient.getStyleProfile(force),
        apiClient.getAgentSuggestions(),
      ]);
      setStyleProfile(profile);
      setSuggestions(suggestionList);
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || 'Failed to load agent data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };
  const handleAnalyze = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAnalysisError('');
    const trimmed = sampleMessage.trim();
    if (!trimmed) {
      setAnalysisError('Enter a message to analyze.');
      return;
    }

    setAnalyzing(true);
    try {
      const result = await apiClient.analyzeAgentMessage(trimmed);
      setAnalysis(result);
    } catch (err: any) {
      setAnalysis(null);
      setAnalysisError(err.response?.data?.message || err.message || 'Failed to analyze message');
    } finally {
      setAnalyzing(false);
    }
  };

  const sentimentBadge = useMemo(() => {
    if (!analysis) {
      return null;
    }
    const sentiment = analysis.analysis?.sentiment ?? '';
    const classes: Record<string, string> = {
      positive: 'bg-emerald-100 text-emerald-700',
      negative: 'bg-red-100 text-red-700',
      neutral: 'bg-slate-100 text-slate-600',
    };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${classes[sentiment] || 'bg-slate-100 text-slate-600'}`}>
        {sentiment || 'unknown'}
      </span>
    );
  }, [analysis]);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const renderStyleProfile = () => {
    if (!styleProfile) {
      return (
        <div className="bg-white border rounded-lg p-6 shadow-sm">
          <p className="text-sm text-gray-500">No style information available yet.</p>
        </div>
      );
    }

    return (
      <div className="bg-white border rounded-lg p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Your Conversation Style</h2>
            <p className="text-sm text-gray-500">
              {styleProfile.updated_at
                ? `Updated ${formatDistanceToNow(new Date(styleProfile.updated_at), { addSuffix: true })}`
                : 'Fresh snapshot'}
            </p>
          </div>
          <span className="inline-flex items-center px-3 py-1 text-xs font-medium rounded-full bg-pink-100 text-pink-700">
            {styleProfile.cached ? 'cached' : 'refreshed'}
          </span>
        </div>

        {styleProfile.style_summary && (
          <p className="text-gray-700">{styleProfile.style_summary}</p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {styleProfile.emoji_frequency && styleProfile.emoji_frequency.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Favorite emojis</h3>
              <div className="flex flex-wrap gap-2">
                {styleProfile.emoji_frequency.map(({ emoji, count }) => (
                  <span
                    key={emoji}
                    className="inline-flex items-center px-2 py-1 text-sm bg-gray-100 rounded-full"
                  >
                    <span className="mr-1 text-lg">{emoji}</span>
                    <span className="text-xs text-gray-600">×{count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {styleProfile.top_words && styleProfile.top_words.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Signature words</h3>
              <div className="flex flex-wrap gap-2">
                {styleProfile.top_words.slice(0, 6).map(({ word, count }) => (
                  <span
                    key={word}
                    className="inline-flex items-center px-2 py-1 text-sm bg-blue-50 text-blue-700 rounded-full"
                  >
                    {word} <span className="ml-1 text-xs text-blue-500">×{count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {styleProfile.signature_examples && styleProfile.signature_examples.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Sample phrases</h3>
            <div className="space-y-2">
              {styleProfile.signature_examples.map((example, index) => (
                <blockquote
                  key={`${example}-${index}`}
                  className="border-l-4 border-pink-200 pl-3 text-sm text-gray-700 italic"
                >
                  “{example}”
                </blockquote>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderSuggestions = () => {
    if (suggestions.length === 0) {
      return (
        <div className="bg-white border rounded-lg p-6 shadow-sm text-center">
          <Sparkles className="w-8 h-8 text-pink-500 mx-auto mb-3" />
          <p className="text-sm text-gray-600">No new suggestions yet. Check back soon!</p>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {suggestions.map((suggestion) => (
          <div key={suggestion.id} className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {iconForType[suggestion.type] ?? <Sparkles className="w-5 h-5 text-gray-500" />}
                <h3 className="text-base font-semibold text-gray-900">{suggestion.title}</h3>
              </div>
              {typeof suggestion.confidence === 'number' && (
                <span className="text-xs text-gray-500">{Math.round(suggestion.confidence * 100)}% match</span>
              )}
            </div>
            <p className="text-sm text-gray-700">{suggestion.summary}</p>
            {suggestion.payload && suggestion.payload.secondary_text && (
              <p className="text-xs text-gray-500">
                {(suggestion.payload.secondary_text as string).length > 160
                  ? `${(suggestion.payload.secondary_text as string).slice(0, 160)}…`
                  : (suggestion.payload.secondary_text as string)}
              </p>
            )}
            {suggestion.generated_at && (
              <p className="text-xs text-gray-400">
                Generated{' '}
                {formatDistanceToNow(new Date(suggestion.generated_at), {
                  addSuffix: true,
                })}
              </p>
            )}
          </div>
        ))}
      </div>
    );
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
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Agent Suggestions</h1>
            <p className="mt-2 text-sm text-gray-600">
              Let the Together Agent help you stay connected{user?.name ? `, ${user.name}` : ''}.
            </p>
          </div>
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCcw className="w-4 h-4 mr-2" />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md">{error}</div>
        )}

        {renderStyleProfile()}
        {renderSuggestions()}

        <div className="bg-white border rounded-lg p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Tone Analyzer</h2>
              <p className="text-sm text-gray-600">
                Compare Together Agent heuristics with OpenAI-powered tone feedback in real time.
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-600">
                Logic
              </span>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-600">
                OpenAI
              </span>
            </div>
          </div>

          <form onSubmit={handleAnalyze} className="space-y-3">
            <label htmlFor="agent-sample" className="block text-sm font-medium text-gray-700">
              Paste a message you&apos;re about to send
            </label>
            <textarea
              id="agent-sample"
              value={sampleMessage}
              onChange={(event) => setSampleMessage(event.target.value)}
              rows={4}
              placeholder="Hey love, I appreciate you taking care of dinner tonight..."
              className="block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-pink-500 focus:outline-none focus:ring-pink-500"
            />
            {analysisError && (
              <div className="inline-flex items-center text-sm text-red-600">
                <AlertCircle className="w-4 h-4 mr-1" /> {analysisError}
              </div>
            )}
            <div className="flex items-center justify-end space-x-3">
              {analysis?.generated_at && (
                <span className="text-xs text-gray-400">
                  Last analyzed{' '}
                  {formatDistanceToNow(new Date(analysis.generated_at), {
                    addSuffix: true,
                  })}
                </span>
              )}
              <button
                type="submit"
                disabled={analyzing}
                className="inline-flex items-center px-4 py-2 rounded-md border border-transparent text-sm font-medium text-white bg-pink-600 hover:bg-pink-700 disabled:opacity-50"
              >
                <Bot className="w-4 h-4 mr-2" />
                {analyzing ? 'Analyzing...' : 'Analyze Tone'}
              </button>
            </div>
          </form>

          {analysis && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="border border-gray-100 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <Gauge className="w-4 h-4 text-blue-600" />
                    <h3 className="text-sm font-semibold text-gray-800">Together Agent Logic</h3>
                  </div>
                  {sentimentBadge}
                </div>
                <ul className="text-xs text-gray-600 space-y-1">
                  <li>
                    <span className="font-medium text-gray-700">Words:</span>{' '}
                    {analysis.analysis?.length?.words ?? 0}
                  </li>
                  <li>
                    <span className="font-medium text-gray-700">Characters:</span>{' '}
                    {analysis.analysis?.length?.characters ?? 0}
                  </li>
                  <li>
                    <span className="font-medium text-gray-700">Emoji count:</span>{' '}
                    {analysis.analysis?.emoji_count ?? 0}
                  </li>
                  <li>
                    <span className="font-medium text-gray-700">Positive tone likelihood:</span>{' '}
                    {Math.round((analysis.analysis?.sentiment_probability_positive ?? 0) * 100)}%
                  </li>
                  {analysis.analysis?.keywords?.length ? (
                    <li>
                      <span className="font-medium text-gray-700">Keywords:</span>{' '}
                      {analysis.analysis.keywords.join(', ')}
                    </li>
                  ) : null}
                </ul>
              </div>

              <div className="border border-gray-100 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-2">Coaching Tips</h3>
                <ul className="space-y-2 text-sm text-gray-700">
                  {analysis.tips?.map((tip, index) => (
                    <li key={`${tip}-${index}`} className="pl-3 border-l-2 border-pink-200">
                      {tip}
                    </li>
                  ))}
                </ul>
                {analysis.strengths?.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs uppercase tracking-wide text-gray-500 mb-1">Strengths</h4>
                    <ul className="space-y-1 text-xs text-emerald-700">
                      {analysis.strengths.map((strength, index) => (
                        <li key={`${strength}-${index}`}>• {strength}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="border border-indigo-100 rounded-lg p-4 bg-indigo-50/40">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-indigo-600" />
                    <h3 className="text-sm font-semibold text-indigo-700">OpenAI Tone Feedback</h3>
                  </div>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide bg-indigo-100 text-indigo-700">
                    OpenAI
                  </span>
                </div>
                <p className="text-sm text-indigo-900 leading-relaxed">
                  {analysis.llm_feedback
                    ? analysis.llm_feedback
                    : 'OpenAI feedback unavailable. Check your API key in the backend if you expect AI guidance here.'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
