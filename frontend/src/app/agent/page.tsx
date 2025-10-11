'use client';

import { useEffect, useState } from 'react';
import AuthLayout from '@/components/layout/AuthLayout';
import { useAuthStore } from '@/lib/auth';
import apiClient from '@/lib/api';
import { Sparkles, RefreshCcw, MessageCircle, Calendar, ClipboardList } from 'lucide-react';
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
      </div>
    </AuthLayout>
  );
}
