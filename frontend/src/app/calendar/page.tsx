'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import AuthLayout from '@/components/layout/AuthLayout';
import apiClient from '@/lib/api';
import { Calendar, Plus, ChevronLeft, ChevronRight, Clock, User, X } from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isSameDay, parseISO } from 'date-fns';

interface EventForm {
  title: string;
  date: string;
  time: string;
  description?: string;
}

interface CalendarEvent {
  _id: string;
  title: string;
  date: string;
  time: string;
  description?: string;
  creator_id: string;
  creator_name: string;
}

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [showEventForm, setShowEventForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<EventForm>();

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const monthDays = eachDayOfInterval({ start: monthStart, end: monthEnd });

  // Pad the calendar with previous/next month days
  const firstDayOfWeek = monthStart.getDay();
  const lastDayOfWeek = monthEnd.getDay();
  const prevMonthDays = Array.from({ length: firstDayOfWeek }, (_, i) => {
    const date = new Date(monthStart);
    date.setDate(date.getDate() - (firstDayOfWeek - i));
    return date;
  });
  const nextMonthDays = Array.from({ length: 6 - lastDayOfWeek }, (_, i) => {
    const date = new Date(monthEnd);
    date.setDate(date.getDate() + (i + 1));
    return date;
  });
  const calendarDays = [...prevMonthDays, ...monthDays, ...nextMonthDays];

  useEffect(() => {
    fetchEvents();
  }, [currentDate]);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth() + 1;
      const eventsData = await apiClient.getEvents(year, month);
      setEvents(eventsData);
    } catch (err: any) {
      setError('Failed to load events');
    } finally {
      setLoading(false);
    }
  };

  const onEventSubmit = async (data: EventForm) => {
    setSaving(true);
    setError('');

    try {
      await apiClient.createEvent(data.title, data.date, data.time, data.description);
      reset();
      setShowEventForm(false);
      setSelectedDate(null);
      await fetchEvents();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to create event');
    } finally {
      setSaving(false);
    }
  };

  const navigateMonth = (direction: 'prev' | 'next') => {
    const newDate = new Date(currentDate);
    newDate.setMonth(newDate.getMonth() + (direction === 'next' ? 1 : -1));
    setCurrentDate(newDate);
  };

  const handleDayClick = (day: Date) => {
    if (isSameMonth(day, currentDate)) {
      setSelectedDate(day);
      setValue('date', format(day, 'yyyy-MM-dd'));
      setShowEventForm(true);
    }
  };

  const getEventsForDay = (day: Date) => {
    return events.filter(event => {
      const eventDate = parseISO(event.date);
      return isSameDay(eventDate, day);
    });
  };

  const getDayClasses = (day: Date) => {
    const baseClasses = 'min-h-[80px] p-2 border border-gray-200 cursor-pointer hover:bg-gray-50';
    const classes = [baseClasses];

    if (!isSameMonth(day, currentDate)) {
      classes.push('text-gray-400 bg-gray-50');
    }

    if (isSameDay(day, new Date())) {
      classes.push('bg-pink-50 text-pink-600 font-semibold');
    }

    if (selectedDate && isSameDay(day, selectedDate)) {
      classes.push('ring-2 ring-pink-500');
    }

    return classes.join(' ');
  };

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Calendar</h1>
            <p className="mt-2 text-sm text-gray-600">
              Shared calendar for you and your partner.
            </p>
          </div>
          <button
            onClick={() => setShowEventForm(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-pink-600 hover:bg-pink-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Event
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md">
            {error}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          {/* Calendar Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <button
              onClick={() => navigateMonth('prev')}
              className="p-2 hover:bg-gray-100 rounded-md"
            >
              <ChevronLeft className="w-5 h-5 text-gray-600" />
            </button>
            <h2 className="text-lg font-semibold text-gray-900">
              {format(currentDate, 'MMMM yyyy')}
            </h2>
            <button
              onClick={() => navigateMonth('next')}
              className="p-2 hover:bg-gray-100 rounded-md"
            >
              <ChevronRight className="w-5 h-5 text-gray-600" />
            </button>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-0">
            {/* Day Headers */}
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
              <div key={day} className="bg-gray-50 p-3 text-center text-sm font-medium text-gray-700">
                {day}
              </div>
            ))}

            {/* Calendar Days */}
            {calendarDays.map((day, index) => (
              <div
                key={index}
                className={getDayClasses(day)}
                onClick={() => handleDayClick(day)}
              >
                <div className="text-sm font-medium mb-1">
                  {format(day, 'd')}
                </div>
                <div className="space-y-1">
                  {getEventsForDay(day).slice(0, 2).map(event => (
                    <div
                      key={event._id}
                      className="text-xs bg-pink-100 text-pink-800 px-2 py-1 rounded truncate"
                      title={`${event.title} - ${event.time} (by ${event.creator_name})`}
                    >
                      {event.time} {event.title}
                    </div>
                  ))}
                  {getEventsForDay(day).length > 2 && (
                    <div className="text-xs text-gray-500 px-2">
                      +{getEventsForDay(day).length - 2} more
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Event Form Modal */}
        {showEventForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">Create New Event</h3>
                <button
                  onClick={() => {
                    setShowEventForm(false);
                    setSelectedDate(null);
                    reset();
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSubmit(onEventSubmit)} className="space-y-4">
                <div>
                  <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                    Event Title
                  </label>
                  <input
                    id="title"
                    type="text"
                    {...register('title', {
                      required: 'Event title is required',
                      maxLength: {
                        value: 100,
                        message: 'Title must be less than 100 characters',
                      },
                    })}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-pink-500 focus:border-pink-500"
                    placeholder="Enter event title"
                  />
                  {errors.title && (
                    <p className="mt-1 text-sm text-red-600">{errors.title.message}</p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="date" className="block text-sm font-medium text-gray-700">
                      Date
                    </label>
                    <input
                      id="date"
                      type="date"
                      {...register('date', {
                        required: 'Date is required',
                      })}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-pink-500 focus:border-pink-500"
                    />
                    {errors.date && (
                      <p className="mt-1 text-sm text-red-600">{errors.date.message}</p>
                    )}
                  </div>

                  <div>
                    <label htmlFor="time" className="block text-sm font-medium text-gray-700">
                      Time
                    </label>
                    <input
                      id="time"
                      type="time"
                      {...register('time', {
                        required: 'Time is required',
                      })}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-pink-500 focus:border-pink-500"
                    />
                    {errors.time && (
                      <p className="mt-1 text-sm text-red-600">{errors.time.message}</p>
                    )}
                  </div>
                </div>

                <div>
                  <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                    Description (Optional)
                  </label>
                  <textarea
                    id="description"
                    rows={3}
                    {...register('description')}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-pink-500 focus:border-pink-500"
                    placeholder="Enter event description"
                  />
                </div>

                <div className="flex justify-end space-x-2 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowEventForm(false);
                      setSelectedDate(null);
                      reset();
                    }}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-pink-600 hover:bg-pink-700 disabled:opacity-50"
                  >
                    {saving ? 'Creating...' : 'Create Event'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Events List for Selected Day */}
        {selectedDate && !showEventForm && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Events for {format(selectedDate, 'MMMM dd, yyyy')}
            </h3>
            {getEventsForDay(selectedDate).length === 0 ? (
              <p className="text-gray-500">No events scheduled for this day.</p>
            ) : (
              <div className="space-y-3">
                {getEventsForDay(selectedDate).map(event => (
                  <div key={event._id} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <Clock className="w-5 h-5 text-gray-400 mt-0.5" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-gray-900">{event.title}</h4>
                        <span className="text-sm text-gray-500">{event.time}</span>
                      </div>
                      {event.description && (
                        <p className="text-sm text-gray-600 mt-1">{event.description}</p>
                      )}
                      <div className="flex items-center mt-2 text-xs text-gray-500">
                        <User className="w-3 h-3 mr-1" />
                        Created by {event.creator_name}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </AuthLayout>
  );
}