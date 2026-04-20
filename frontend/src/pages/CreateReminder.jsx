import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api/axios';
import { toast } from 'react-hot-toast';
import {
  Bell,
  Phone,
  Calendar,
  Clock,
  Mic,
  Upload,
  ArrowLeft,
  Loader,
  Save,
  Type,
  Repeat,
  RefreshCw
} from 'lucide-react';
import { motion } from 'framer-motion';
import AudioRecorder from '../components/AudioRecorder';
import AudioUploader from '../components/AudioUploader';

const RECURRENCE_OPTIONS = [
  { value: 'none',     label: 'Does not repeat' },
  { value: 'daily',    label: 'Daily' },
  { value: 'weekly',   label: 'Weekly' },
  { value: 'monthly',  label: 'Monthly' },
  { value: 'weekdays', label: 'Weekdays (Mon – Fri)' },
];

const CreateReminder = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;

  const [formData, setFormData] = useState({
    title: '',
    phone_number: '',
    scheduled_date: '',
    scheduled_time: ''
  });
  const [audioFile, setAudioFile] = useState(null);
  const [audioSource, setAudioSource] = useState('record');
  const [recurrence, setRecurrence] = useState('none');
  const [recurrenceEndDate, setRecurrenceEndDate] = useState('');
  const [retryEnabled, setRetryEnabled] = useState(false);
  const [retryCount, setRetryCount] = useState(1);
  const [retryGapMinutes, setRetryGapMinutes] = useState(10);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loading, setLoading] = useState(isEdit);
  const [existingAudioUrl, setExistingAudioUrl] = useState(null);

  useEffect(() => {
    if (isEdit) {
      const fetchReminder = async () => {
        try {
          const response = await api.get(`/reminders/${id}`);
          const r = response.data;
          const dt = new Date(r.scheduled_time + 'Z');
          setFormData({
            title: r.title,
            phone_number: r.phone_number,
            scheduled_date: dt.toLocaleDateString('en-CA'),
            scheduled_time: dt.toTimeString().slice(0, 5)
          });
          setExistingAudioUrl(`/audio/${r.audio_filename}`);
          setRecurrence(r.recurrence || 'none');
          if (r.retry_count > 0) {
            setRetryEnabled(true);
            setRetryCount(r.retry_count);
            setRetryGapMinutes(r.retry_gap_minutes);
          }
          if (r.recurrence_end_date) {
            const endDt = new Date(r.recurrence_end_date + 'Z');
            setRecurrenceEndDate(endDt.toLocaleDateString('en-CA'));
          }
        } catch (error) {
          toast.error('Could not load reminder details');
          navigate('/dashboard');
        } finally {
          setLoading(false);
        }
      };
      fetchReminder();
    }
  }, [id, isEdit, navigate]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    if (!formData.title.trim()) {
      toast.error('Please enter a title for the reminder.');
      setIsSubmitting(false);
      return;
    }

    if (!/^\+91\d{10}$/.test(formData.phone_number)) {
      toast.error('Please enter a valid Indian mobile number in E.164 format, e.g. +919876543210.');
      setIsSubmitting(false);
      return;
    }

    if (!formData.scheduled_date || !formData.scheduled_time) {
      toast.error('Please select a valid date and time.');
      setIsSubmitting(false);
      return;
    }

    const scheduledDateTimeValue = new Date(`${formData.scheduled_date}T${formData.scheduled_time}:00`);
    if (Number.isNaN(scheduledDateTimeValue.getTime()) || scheduledDateTimeValue.getTime() <= Date.now()) {
      toast.error('Please choose a future date and time for the reminder.');
      setIsSubmitting(false);
      return;
    }

    if (!audioFile && !isEdit) {
      toast.error('Please record or upload a voice message.');
      setIsSubmitting(false);
      return;
    }

    const data = new FormData();
    data.append('title', formData.title);
    data.append('phone_number', formData.phone_number);
    const localDt = new Date(`${formData.scheduled_date}T${formData.scheduled_time}:00`);
    data.append('scheduled_time', localDt.toISOString());
    if (audioFile) {
      data.append('audio_file', audioFile);
    }
    if (recurrence !== 'none') {
      data.append('recurrence', recurrence);
      if (recurrenceEndDate) {
        // Use end-of-day UTC so the last occurrence on that date fires
        const endDt = new Date(`${recurrenceEndDate}T23:59:59`);
        data.append('recurrence_end_date', endDt.toISOString());
      }
    } else {
      // Explicitly clear recurrence when editing a previously recurring reminder
      data.append('recurrence', '');
    }
    data.append('retry_count', retryEnabled ? String(retryCount) : '0');
    data.append('retry_gap_minutes', String(retryGapMinutes));

    try {
      if (isEdit) {
        await api.put(`/reminders/${id}`, data);
        toast.success('Reminder updated successfully');
      } else {
        await api.post('/reminders', data);
        toast.success('Reminder created! We will call you at the scheduled time.');
      }
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || error.message || 'Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader className="w-12 h-12 text-primary-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-6 group"
      >
        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
        Back to Dashboard
      </button>

      <div className="flex items-center gap-3 mb-8">
        <div className="bg-primary-600/20 p-3 rounded-2xl">
          <Bell className="w-8 h-8 text-primary-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white">
            {isEdit ? 'Edit Reminder' : 'Create New Reminder'}
          </h1>
          <p className="text-slate-400">Schedule your personalized voice call</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Basic Info Section */}
        <section className="glass-card p-6 rounded-2xl space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Type className="w-4 h-4 text-primary-400" />
                Reminder Title
              </label>
              <input
                name="title"
                required
                className="glass-input w-full"
                placeholder="e.g., Morning Wake-up Call"
                value={formData.title}
                onChange={handleChange}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Phone className="w-4 h-4 text-emerald-400" />
                Phone Number
              </label>
              <input
                name="phone_number"
                required
                className="glass-input w-full"
                placeholder="+919876543210"
                value={formData.phone_number}
                onChange={handleChange}
              />
              <p className="text-xs text-slate-500">Enter your phone number in E.164 format, e.g. +919876543210.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-primary-400" />
                Date
              </label>
              <input
                name="scheduled_date"
                type="date"
                required
                min={new Date().toISOString().split('T')[0]}
                className="glass-input w-full"
                value={formData.scheduled_date}
                onChange={handleChange}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Clock className="w-4 h-4 text-primary-400" />
                Time
              </label>
              <input
                name="scheduled_time"
                type="time"
                required
                className="glass-input w-full"
                value={formData.scheduled_time}
                onChange={handleChange}
              />
            </div>
          </div>
        </section>

        {/* Recurrence Section */}
        <section className="glass-card p-6 rounded-2xl space-y-4">
          <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <Repeat className="w-4 h-4 text-primary-400" />
            Recurrence
          </h2>
          <select
            value={recurrence}
            onChange={(e) => {
              setRecurrence(e.target.value);
              if (e.target.value === 'none') setRecurrenceEndDate('');
            }}
            className="glass-input w-full"
          >
            {RECURRENCE_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          {recurrence !== 'none' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-2"
            >
              <label className="text-xs font-medium text-slate-400 flex items-center gap-2">
                <Calendar className="w-3.5 h-3.5" />
                End date <span className="text-slate-600">(optional — leave blank to repeat forever)</span>
              </label>
              <input
                type="date"
                min={formData.scheduled_date || new Date().toISOString().split('T')[0]}
                value={recurrenceEndDate}
                onChange={(e) => setRecurrenceEndDate(e.target.value)}
                className="glass-input w-full"
              />
            </motion.div>
          )}
        </section>

        {/* Retry Section */}
        <section className="glass-card p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-primary-400" />
              Auto-Retry on Failure
            </h2>
            <button
              type="button"
              onClick={() => setRetryEnabled(v => !v)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                retryEnabled ? 'bg-primary-600' : 'bg-white/10'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                  retryEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {retryEnabled && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-4"
            >
              <p className="text-xs text-slate-500">
                If the call is not answered, we'll retry automatically at the gap you choose.
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-slate-400">How many retries?</label>
                  <div className="flex gap-2">
                    {[1, 2].map(n => (
                      <button
                        key={n}
                        type="button"
                        onClick={() => setRetryCount(n)}
                        className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${
                          retryCount === n
                            ? 'bg-primary-600 border-primary-500 text-white'
                            : 'bg-white/5 border-white/10 text-slate-400 hover:text-white'
                        }`}
                      >
                        {n} {n === 1 ? '(2 calls)' : '(3 calls)'}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-slate-400">Gap between retries</label>
                  <div className="flex flex-wrap gap-2">
                    {[5, 10, 15, 30].map(m => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setRetryGapMinutes(m)}
                        className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                          retryGapMinutes === m
                            ? 'bg-primary-600 border-primary-500 text-white'
                            : 'bg-white/5 border-white/10 text-slate-400 hover:text-white'
                        }`}
                      >
                        {m} min
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </section>

        {/* Audio Content Section */}
        <section className="glass-card p-6 rounded-2xl">
          <div className="flex p-1 bg-white/5 rounded-xl mb-6 max-w-xs">
            <button
              type="button"
              onClick={() => setAudioSource('record')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                audioSource === 'record' ? 'bg-primary-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Mic className="w-4 h-4" />
              Record
            </button>
            <button
              type="button"
              onClick={() => setAudioSource('upload')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                audioSource === 'upload' ? 'bg-primary-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Upload className="w-4 h-4" />
              Upload
            </button>
          </div>

          {audioSource === 'record' ? (
            <AudioRecorder
              onRecordingComplete={setAudioFile}
              initialAudioUrl={existingAudioUrl}
            />
          ) : (
            <AudioUploader
              onFileSelect={setAudioFile}
              initialFileName={isEdit && !audioFile ? "Existing recording preserved" : null}
            />
          )}

          {isEdit && !audioFile && (
            <p className="text-xs text-slate-500 mt-4 italic">
              * Leave the audio section as is to keep the existing voice message.
            </p>
          )}
        </section>

        <div className="flex gap-4 pt-4">
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex-grow btn-primary py-4 flex items-center justify-center gap-3 text-lg"
          >
            {isSubmitting ? (
              <Loader className="w-6 h-6 animate-spin" />
            ) : (
              <>
                <Save className="w-6 h-6" />
                {isEdit ? 'Update Reminder' : 'Set Reminder'}
              </>
            )}
          </button>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="btn-secondary px-8"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateReminder;
