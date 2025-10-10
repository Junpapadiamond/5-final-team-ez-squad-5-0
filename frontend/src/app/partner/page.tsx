'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import AuthLayout from '@/components/layout/AuthLayout';
import apiClient from '@/lib/api';
import { Users, Mail, Check, X, Heart, Send } from 'lucide-react';

interface InviteForm {
  partnerEmail: string;
}

interface PartnerStatus {
  partner?: {
    _id: string;
    name: string;
    email: string;
  };
  pending_invitations?: Array<{
    _id: string;
    inviter_name: string;
    inviter_email: string;
    created_at: string;
  }>;
  sent_invitations?: Array<{
    _id: string;
    invitee_email: string;
    created_at: string;
  }>;
}

export default function PartnerPage() {
  const [partnerStatus, setPartnerStatus] = useState<PartnerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<InviteForm>();

  useEffect(() => {
    fetchPartnerStatus();
  }, []);

  const fetchPartnerStatus = async () => {
    try {
      const status = await apiClient.getPartnerStatus();
      setPartnerStatus(status);
    } catch (err: any) {
      setError('Failed to load partner status');
    } finally {
      setLoading(false);
    }
  };

  const onInviteSubmit = async (data: InviteForm) => {
    setLoading(true);
    setMessage('');
    setError('');

    try {
      await apiClient.invitePartner(data.partnerEmail);
      setMessage('Invitation sent successfully!');
      reset();
      await fetchPartnerStatus();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to send invitation');
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptInvitation = async (inviterId: string) => {
    setLoading(true);
    setMessage('');
    setError('');

    try {
      await apiClient.acceptPartner(inviterId);
      setMessage('Invitation accepted! You are now connected.');
      await fetchPartnerStatus();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to accept invitation');
    } finally {
      setLoading(false);
    }
  };

  const handleRejectInvitation = async (inviterId: string) => {
    setLoading(true);
    setMessage('');
    setError('');

    try {
      await apiClient.rejectPartner(inviterId);
      setMessage('Invitation rejected.');
      await fetchPartnerStatus();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to reject invitation');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !partnerStatus) {
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
      <div className="max-w-2xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Partner Connection</h1>
          <p className="mt-2 text-sm text-gray-600">
            Connect with your partner to share calendars, messages, and more.
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

        {/* Connected Partner */}
        {partnerStatus?.partner && (
          <div className="bg-white shadow-sm rounded-lg p-6 border border-green-200">
            <div className="flex items-center mb-4">
              <div className="bg-green-100 p-3 rounded-full mr-4">
                <Heart className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h2 className="text-lg font-medium text-gray-900">Connected Partner</h2>
                <p className="text-sm text-gray-500">You are successfully connected!</p>
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center">
                <Users className="w-5 h-5 text-gray-400 mr-3" />
                <div>
                  <p className="font-medium text-gray-900">{partnerStatus.partner.name}</p>
                  <p className="text-sm text-gray-500">{partnerStatus.partner.email}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Pending Invitations */}
        {partnerStatus?.pending_invitations && partnerStatus.pending_invitations.length > 0 && (
          <div className="bg-white shadow-sm rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Pending Invitations</h2>
            <div className="space-y-4">
              {partnerStatus.pending_invitations.map((invitation) => (
                <div key={invitation._id} className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{invitation.inviter_name}</p>
                      <p className="text-sm text-gray-500">{invitation.inviter_email}</p>
                      <p className="text-xs text-gray-400 mt-1">
                        Sent {new Date(invitation.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleAcceptInvitation(invitation._id)}
                        disabled={loading}
                        className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                      >
                        <Check className="w-4 h-4 mr-1" />
                        Accept
                      </button>
                      <button
                        onClick={() => handleRejectInvitation(invitation._id)}
                        disabled={loading}
                        className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
                      >
                        <X className="w-4 h-4 mr-1" />
                        Reject
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sent Invitations */}
        {partnerStatus?.sent_invitations && partnerStatus.sent_invitations.length > 0 && (
          <div className="bg-white shadow-sm rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Sent Invitations</h2>
            <div className="space-y-4">
              {partnerStatus.sent_invitations.map((invitation) => (
                <div key={invitation._id} className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center">
                    <Mail className="w-5 h-5 text-gray-400 mr-3" />
                    <div>
                      <p className="font-medium text-gray-900">{invitation.invitee_email}</p>
                      <p className="text-sm text-gray-500">
                        Sent {new Date(invitation.created_at).toLocaleDateString()}
                      </p>
                      <p className="text-xs text-yellow-600 mt-1">Waiting for response...</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Invite Partner Form */}
        {!partnerStatus?.partner && (
          <div className="bg-white shadow-sm rounded-lg p-6">
            <div className="flex items-center mb-6">
              <Send className="w-5 h-5 text-gray-400 mr-2" />
              <h2 className="text-lg font-medium text-gray-900">Invite Your Partner</h2>
            </div>

            <form onSubmit={handleSubmit(onInviteSubmit)} className="space-y-4">
              <div>
                <label htmlFor="partnerEmail" className="block text-sm font-medium text-gray-700">
                  Partner's Email Address
                </label>
                <div className="mt-1">
                  <input
                    id="partnerEmail"
                    type="email"
                    {...register('partnerEmail', {
                      required: 'Partner email is required',
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: 'Invalid email address',
                      },
                    })}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-pink-500 focus:border-pink-500"
                    placeholder="Enter your partner's email"
                  />
                  {errors.partnerEmail && (
                    <p className="mt-1 text-sm text-red-600">{errors.partnerEmail.message}</p>
                  )}
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-pink-600 hover:bg-pink-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-pink-500 disabled:opacity-50"
                >
                  <Send className="w-4 h-4 mr-2" />
                  {loading ? 'Sending...' : 'Send Invitation'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* No Partner Connected */}
        {!partnerStatus?.partner &&
          (!partnerStatus?.pending_invitations || partnerStatus.pending_invitations.length === 0) &&
          (!partnerStatus?.sent_invitations || partnerStatus.sent_invitations.length === 0) && (
            <div className="bg-gray-50 rounded-lg p-8 text-center">
              <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Partner Connected</h3>
              <p className="text-gray-600 mb-4">
                Invite your partner to start sharing calendars, messages, and taking quizzes together.
              </p>
            </div>
          )}
      </div>
    </AuthLayout>
  );
}