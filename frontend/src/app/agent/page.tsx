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
  key_traits?: string[];
  ai_source?: string;
}

interface SuggestionPayload {
  call_to_action?: string | null;
  suggested_message?: string | null;
  tone_hint?: string | null;
  secondary_text?: string | null;
  suggested_window?: string | null;
}

interface SuggestionCard {
  id: string;
  type: string;
  title: string;
  summary: string;
  confidence?: number | null;
  generated_at?: string;
  payload?: SuggestionPayload | null;
  ai_source?: string;
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
  emotional_drivers?: string[];
}

interface AgentAnalysisResult {
  analysis: AgentAnalysisMetrics;
  strengths: string[];
  tips: string[];
  style_profile?: Record<string, unknown>;
  llm_feedback?: string | null;
  generated_at?: string;
  ai_source?: string;
  suggested_reply?: string | null;
  warnings?: string[];
  cached?: boolean;
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
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center px-3 py-1 text-xs font-medium rounded-full bg-pink-100 text-pink-700">
              {styleProfile.cached ? 'cached' : 'refreshed'}
            </span>
            {styleProfile.ai_source && (
              <span
                className={`inline-flex items-center px-3 py-1 text-xs font-medium rounded-full ${
                  styleProfile.ai_source === 'openai'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                {styleProfile.ai_source === 'openai' ? 'LLM summary' : 'Logic summary'}
              </span>
            )}
          </div>
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
          {styleProfile.key_traits && styleProfile.key_traits.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Key Traits</h3>
              <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                {styleProfile.key_traits.map((trait: string, index: number) => (
                  <li key={`${trait}-${index}`}>{trait}</li>
                ))}
              </ul>
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
              <div className="flex items-center space-x-2">
                {typeof suggestion.confidence === 'number' && (
                  <span className="text-xs text-gray-500">{Math.round(suggestion.confidence * 100)}% match</span>
                )}
                {suggestion.ai_source && (
                  <span
                    className={`px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide ${
                      suggestion.ai_source === 'openai'
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {suggestion.ai_source === 'openai' ? 'LLM' : 'Logic'}
                  </span>
                )}
              </div>
            </div>
            <p className="text-sm text-gray-700">{suggestion.summary}</p>
            {suggestion.payload?.secondary_text && (
              <p className="text-xs text-gray-500">
                {suggestion.payload.secondary_text.length > 160
                  ? `${suggestion.payload.secondary_text.slice(0, 160)}…`
                  : suggestion.payload.secondary_text}
              </p>
            )}
            {suggestion.payload?.call_to_action && (
              <div className="border border-blue-100 rounded-md p-3 bg-blue-50/40">
                <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">
                  Next Step
                </p>
                <p className="text-sm text-blue-900">{suggestion.payload.call_to_action}</p>
              </div>
            )}
            {suggestion.payload?.suggested_message && (
              <div className="border border-pink-100 rounded-md p-3 bg-pink-50/40">
                <p className="text-xs font-semibold text-pink-700 uppercase tracking-wide mb-1">
                  Suggested message
                </p>
                <p className="text-sm text-pink-900 leading-relaxed">
                  {suggestion.payload.suggested_message}
                </p>
              </div>
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
                <div className="flex items-center justify-between text-[11px] uppercase tracking-wide mb-2">
                  <span className="font-semibold text-gray-500">Source</span>
                  <span
                    className={`px-2 py-0.5 rounded-full ${
                      analysis.ai_source === 'openai'
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {analysis.ai_source === 'openai' ? 'LLM powered' : 'Logic fallback'}
                  </span>
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
                  {analysis.analysis?.emotional_drivers && analysis.analysis.emotional_drivers.length > 0 ? (
                    <li>
                      <span className="font-medium text-gray-700">Emotional drivers:</span>{' '}
                      {analysis.analysis.emotional_drivers.join(', ')}
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

              <div className="border border-indigo-100 rounded-lg p-4 bg-indigo-50/40 space-y-3">
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
                {analysis.suggested_reply && (
                  <div className="border border-indigo-200 rounded-md p-3 bg-white/50">
                    <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide mb-1">
                      Suggested next move
                    </p>
                    <p className="text-sm text-indigo-900">{analysis.suggested_reply}</p>
                  </div>
                )}
                {analysis.warnings && analysis.warnings.length > 0 && (
                  <div className="border border-amber-200 rounded-md p-3 bg-amber-50">
                    <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">Warnings</p>
                    <ul className="space-y-1 text-sm text-amber-900 list-disc list-inside">
                      {analysis.warnings.map((warning, index) => (
                        <li key={`${warning}-${index}`}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
