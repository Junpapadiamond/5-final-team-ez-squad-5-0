'use client';

import { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import AuthLayout from '@/components/layout/AuthLayout';
import { useAuthStore } from '@/lib/auth';
import apiClient from '@/lib/api';
import { MessageCircle, Send, Clock, X, Calendar, Plus } from 'lucide-react';
import { format } from 'date-fns';

interface MessageForm {
  content: string;
}

interface ScheduleMessageForm {
  content: string;
  scheduledDate: string;
  scheduledTime: string;
}

interface Message {
  _id: string;
  sender_id: string;
  sender_name: string;
  recipient_id: string;
  recipient_name: string;
  content: string;
  timestamp: string;
  is_scheduled: boolean;
}

interface ScheduledMessage {
  _id: string;
  content: string;
  scheduled_for: string;
  sender_name: string;
  status: string;
}

export default function MessagesPage() {
  const { user } = useAuthStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [scheduledMessages, setScheduledMessages] = useState<ScheduledMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [scheduleMode, setScheduleMode] = useState<'create' | 'edit'>('create');
  const [editingMessage, setEditingMessage] = useState<ScheduledMessage | null>(null);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    register: messageRegister,
    handleSubmit: handleMessageSubmit,
    formState: { errors: messageErrors },
    reset: resetMessageForm,
  } = useForm<MessageForm>();

  const {
    register: scheduleRegister,
    handleSubmit: handleScheduleSubmit,
    formState: { errors: scheduleErrors },
    reset: resetScheduleForm,
  } = useForm<ScheduleMessageForm>();

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchData = async () => {
    try {
      const [messagesData, scheduledData] = await Promise.allSettled([
        apiClient.getMessages(),
        apiClient.getScheduledMessages(),
      ]);

      if (messagesData.status === 'fulfilled') {
        setMessages(messagesData.value);
      }

      if (scheduledData.status === 'fulfilled') {
        setScheduledMessages(scheduledData.value);
      }
    } catch (err: any) {
      setError('Failed to load messages');
    } finally {
      setLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const onMessageSubmit = async (data: MessageForm) => {
    setSending(true);
    setError('');

    try {
      await apiClient.sendMessage(data.content);
      resetMessageForm();
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const onScheduleSubmit = async (data: ScheduleMessageForm) => {
    setSending(true);
    setError('');

    try {
      const scheduleDateTime = new Date(`${data.scheduledDate}T${data.scheduledTime}`);
      if (Number.isNaN(scheduleDateTime.getTime())) {
        throw new Error('Invalid date or time');
      }

      const scheduledFor = scheduleDateTime.toISOString();

      if (scheduleMode === 'edit' && editingMessage) {
        await apiClient.updateScheduledMessage(editingMessage._id, {
          content: data.content,
          scheduled_for: scheduledFor,
        });
      } else {
        await apiClient.scheduleMessage(data.content, scheduledFor);
      }

      resetScheduleForm();
      setShowScheduleForm(false);
      setScheduleMode('create');
      setEditingMessage(null);
      await fetchData();
    } catch (err: any) {
      const message =
        err.response?.data?.message ||
        err.message ||
        'Failed to schedule message';
      setError(message);
    } finally {
      setSending(false);
    }
  };

  const handleCancelScheduled = async (messageId: string) => {
    try {
      await apiClient.cancelScheduledMessage(messageId);
      await fetchData();
    } catch (err: any) {
      const message =
        err.response?.data?.message ||
        err.message ||
        'Failed to cancel scheduled message';
      setError(message);
    }
  };

  const handleOpenScheduleForm = () => {
    setScheduleMode('create');
    setEditingMessage(null);
    resetScheduleForm();
    setShowScheduleForm(true);
  };

  const handleEditScheduled = (message: ScheduledMessage) => {
    setScheduleMode('edit');
    setEditingMessage(message);
    setShowScheduleForm(true);

    const scheduledDate = new Date(message.scheduled_for);
    const dateValue = scheduledDate.toLocaleDateString('en-CA');
    const timeValue = scheduledDate.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });

    resetScheduleForm({
      content: message.content,
      scheduledDate: dateValue,
      scheduledTime: timeValue,
    });
  };

  const handleCloseScheduleForm = () => {
    setShowScheduleForm(false);
    setScheduleMode('create');
    setEditingMessage(null);
    resetScheduleForm();
  };

  const formatMessageTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffInDays === 0) {
      return format(date, 'HH:mm');
    } else if (diffInDays === 1) {
      return `Yesterday ${format(date, 'HH:mm')}`;
    } else if (diffInDays < 7) {
      return format(date, 'EEE HH:mm');
    } else {
      return format(date, 'MMM dd, HH:mm');
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
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Messages</h1>
            <p className="mt-2 text-sm text-gray-600">
              Send instant messages or schedule them for later.
            </p>
          </div>
          <button
            onClick={() => (showScheduleForm ? handleCloseScheduleForm() : handleOpenScheduleForm())}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <Calendar className="w-4 h-4 mr-2" />
            {showScheduleForm ? (scheduleMode === 'edit' ? 'Close Editor' : 'Close Scheduler') : 'Schedule Message'}
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Messages */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center">
                  <MessageCircle className="w-5 h-5 text-pink-600 mr-2" />
                  <h2 className="text-lg font-medium text-gray-900">Conversation</h2>
                </div>
              </div>

              <div className="h-96 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    <MessageCircle className="w-12 h-12 mx-auto text-gray-300 mb-4" />
                    <p>No messages yet. Send your first message!</p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message._id}
                      className={`flex ${
                        message.sender_id === user?._id ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                          message.sender_id === user?._id
                            ? 'bg-pink-500 text-white'
                            : 'bg-gray-100 text-gray-900'
                        }`}
                      >
                        <p className="text-sm">{message.content}</p>
                        <p
                          className={`text-xs mt-1 ${
                            message.sender_id === user?._id
                              ? 'text-pink-100'
                              : 'text-gray-500'
                          }`}
                        >
                          {formatMessageTime(message.timestamp)}
                        </p>
                      </div>
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="p-4 border-t border-gray-200">
                <form onSubmit={handleMessageSubmit(onMessageSubmit)}>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      {...messageRegister('content', {
                        required: 'Message cannot be empty',
                        maxLength: {
                          value: 500,
                          message: 'Message must be less than 500 characters',
                        },
                      })}
                      placeholder="Type your message..."
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-pink-500 focus:border-pink-500 text-gray-900 bg-white"
                    />
                    <button
                      type="submit"
                      disabled={sending}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-pink-600 hover:bg-pink-700 disabled:opacity-50"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                  {messageErrors.content && (
                    <p className="mt-1 text-sm text-red-600">{messageErrors.content.message}</p>
                  )}
                </form>
              </div>
            </div>

            {/* Schedule Message Form */}
            {showScheduleForm && (
              <div className="bg-white rounded-lg shadow-sm border p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">
                    {scheduleMode === 'edit' ? 'Edit Scheduled Message' : 'Schedule Message'}
                  </h3>
                  <button
                    onClick={handleCloseScheduleForm}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <form onSubmit={handleScheduleSubmit(onScheduleSubmit)} className="space-y-4">
                  <div>
                    <label htmlFor="content" className="block text-sm font-medium text-gray-700">
                      Message
                    </label>
                    <textarea
                      id="content"
                      rows={3}
                      {...scheduleRegister('content', {
                        required: 'Message cannot be empty',
                        maxLength: {
                          value: 500,
                          message: 'Message must be less than 500 characters',
                        },
                      })}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-pink-500 focus:border-pink-500 text-gray-900 bg-white"
                      placeholder="Type your message to schedule..."
                    />
                    {scheduleErrors.content && (
                      <p className="mt-1 text-sm text-red-600">{scheduleErrors.content.message}</p>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="scheduledDate" className="block text-sm font-medium text-gray-700">
                        Date
                      </label>
                      <input
                        id="scheduledDate"
                        type="date"
                        {...scheduleRegister('scheduledDate', {
                          required: 'Date is required',
                        })}
                        min={new Date().toISOString().split('T')[0]}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-pink-500 focus:border-pink-500 text-gray-900 bg-white"
                      />
                      {scheduleErrors.scheduledDate && (
                        <p className="mt-1 text-sm text-red-600">
                          {scheduleErrors.scheduledDate.message}
                        </p>
                      )}
                    </div>

                    <div>
                      <label htmlFor="scheduledTime" className="block text-sm font-medium text-gray-700">
                        Time
                      </label>
                      <input
                        id="scheduledTime"
                        type="time"
                        {...scheduleRegister('scheduledTime', {
                          required: 'Time is required',
                        })}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-pink-500 focus:border-pink-500 text-gray-900 bg-white"
                      />
                      {scheduleErrors.scheduledTime && (
                        <p className="mt-1 text-sm text-red-600">
                          {scheduleErrors.scheduledTime.message}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex justify-end space-x-2">
                    <button
                      type="button"
                      onClick={handleCloseScheduleForm}
                      className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={sending}
                      className="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                    >
                      {sending
                        ? scheduleMode === 'edit'
                          ? 'Updating...'
                          : 'Scheduling...'
                        : scheduleMode === 'edit'
                          ? 'Update Message'
                          : 'Schedule Message'}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>

          {/* Scheduled Messages */}
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center">
                  <Clock className="w-5 h-5 text-blue-600 mr-2" />
                  <h2 className="text-lg font-medium text-gray-900">Scheduled</h2>
                </div>
              </div>

              <div className="p-4">
                {scheduledMessages.length === 0 ? (
                  <div className="text-center text-gray-500 py-4">
                    <Clock className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                    <p className="text-sm">No scheduled messages</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {scheduledMessages.map((message) => (
                      <div key={message._id} className="bg-blue-50 rounded-lg p-3 border border-blue-100">
                        <p className="text-sm text-gray-900 mb-2">{message.content}</p>
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-xs text-blue-600 font-medium">
                              {format(new Date(message.scheduled_for), 'MMM dd, HH:mm')}
                            </p>
                            <p className="text-xs text-blue-500 capitalize">{message.status}</p>
                          </div>
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => handleEditScheduled(message)}
                              className="text-xs text-blue-700 hover:text-blue-900 underline"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleCancelScheduled(message._id)}
                              className="text-xs text-red-600 hover:text-red-800 underline"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AuthLayout>
  );
}
