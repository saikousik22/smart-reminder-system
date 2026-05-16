import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
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
  RefreshCw,
  Bookmark,
  LayoutTemplate,
  X,
  MessageSquare,
  Languages,
  CheckCircle,
  BookUser,
  Users
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AudioRecorder from '../components/AudioRecorder';
import AudioUploader from '../components/AudioUploader';

const RECURRENCE_OPTIONS = [
  { value: 'none',     label: 'Does not repeat' },
  { value: 'daily',    label: 'Daily' },
  { value: 'weekly',   label: 'Weekly' },
  { value: 'monthly',  label: 'Monthly' },
  { value: 'weekdays', label: 'Weekdays (Mon – Fri)' },
];

const LANGUAGE_OPTIONS = [
  { code: 'hi',    name: 'Hindi' },
  { code: 'te',    name: 'Telugu' },
  { code: 'ta',    name: 'Tamil' },
  { code: 'kn',    name: 'Kannada' },
  { code: 'ml',    name: 'Malayalam' },
  { code: 'mr',    name: 'Marathi' },
  { code: 'bn',    name: 'Bengali' },
  { code: 'gu',    name: 'Gujarati' },
  { code: 'pa',    name: 'Punjabi' },
  { code: 'ur',    name: 'Urdu' },
  { code: 'fr',    name: 'French' },
  { code: 'es',    name: 'Spanish' },
  { code: 'de',    name: 'German' },
  { code: 'ar',    name: 'Arabic' },
  { code: 'zh-CN', name: 'Chinese (Simplified)' },
  { code: 'ja',    name: 'Japanese' },
  { code: 'ko',    name: 'Korean' },
  { code: 'pt',    name: 'Portuguese' },
  { code: 'ru',    name: 'Russian' },
  { code: 'it',    name: 'Italian' },
];

const CreateReminder = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const isEdit = !!id;

  // Group mode — pre-filled when navigating from Groups page via Link state
  const [recipientMode, setRecipientMode] = useState(
    location.state?.groupId ? 'group' : 'single'
  );
  const [groups, setGroups]               = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState(location.state?.groupId ?? null);

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

  // Fallback state
  const [fallbackType, setFallbackType]             = useState('none');
  const [fallbackEmail, setFallbackEmail]           = useState('');
  const [originalText, setOriginalText]             = useState('');
  const [preferredLanguage, setPreferredLanguage]   = useState('');
  const [fallbackText, setFallbackText]             = useState('');
  const [translating, setTranslating]               = useState(false);
  const [translationConfirmed, setTranslationConfirmed] = useState(false);

  // Template state
  const [templates, setTemplates]             = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState(null);
  const [showTemplateSave, setShowTemplateSave] = useState(false);
  const [templateName, setTemplateName]         = useState('');
  const [savingTemplate, setSavingTemplate]     = useState(false);

  // Contact picker state
  const [contacts, setContacts]           = useState([]);
  const [showContactPicker, setShowContactPicker] = useState(false);
  const [contactSearch, setContactSearch] = useState('');

  const parseUtcDate = (isoString) => {
    return new Date(/[+-]\d{2}:\d{2}$|Z$/i.test(isoString) ? isoString : `${isoString}Z`);
  };

  // Fetch templates, contacts, and groups (only on create form)
  useEffect(() => {
    if (isEdit) return;
    const controller = new AbortController();
    api.get('/templates', { signal: controller.signal }).then(r => setTemplates(r.data)).catch(() => {});
    api.get('/contacts', { signal: controller.signal }).then(r => setContacts(r.data)).catch(() => {});
    api.get('/groups', { signal: controller.signal }).then(r => setGroups(r.data)).catch(() => {});
    return () => controller.abort();
  }, [isEdit]);

  const applyTemplate = (templateId) => {
    const tpl = templates.find(t => t.id === Number(templateId));
    if (!tpl) { setSelectedTemplateId(null); return; }
    setSelectedTemplateId(tpl.id);
    setFormData(prev => ({ ...prev, title: tpl.title, phone_number: tpl.phone_number }));
    setRecurrence(tpl.recurrence || 'none');
    if (tpl.retry_count > 0) {
      setRetryEnabled(true);
      setRetryCount(tpl.retry_count);
      setRetryGapMinutes(tpl.retry_gap_minutes);
    } else {
      setRetryEnabled(false);
    }
  };

  useEffect(() => {
    if (isEdit) {
      const fetchReminder = async () => {
        try {
          const response = await api.get(`/reminders/${id}`);
          const r = response.data;
          const dt = parseUtcDate(r.scheduled_time);
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
            const endDt = parseUtcDate(r.recurrence_end_date);
            setRecurrenceEndDate(endDt.toLocaleDateString('en-CA'));
          }
          if (r.fallback_type)  setFallbackType(r.fallback_type);
          if (r.fallback_email) setFallbackEmail(r.fallback_email);
          if (r.original_text)  setOriginalText(r.original_text);
          if (r.fallback_text)  setFallbackText(r.fallback_text);
          if (r.preferred_language) {
            setPreferredLanguage(r.preferred_language);
            if (r.fallback_text) setTranslationConfirmed(true);
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

  const handleTranslate = async () => {
    if (!originalText.trim()) { toast.error('Enter a fallback message to translate.'); return; }
    if (!preferredLanguage)   { toast.error('Select a target language first.'); return; }
    setTranslating(true);
    setTranslationConfirmed(false);
    try {
      const res = await api.post('/translate', { text: originalText, target_lang: preferredLanguage });
      setFallbackText(res.data.translated_text);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Translation failed. Please try again.');
    } finally {
      setTranslating(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    if (!formData.title.trim()) {
      toast.error('Please enter a title for the reminder.');
      setIsSubmitting(false);
      return;
    }

    if (recipientMode === 'group') {
      if (!selectedGroupId) {
        toast.error('Please select a group.');
        setIsSubmitting(false);
        return;
      }
    } else {
      if (!/^\+[1-9]\d{0,14}$/.test(formData.phone_number)) {
        toast.error('Please enter a valid phone number in E.164 format, e.g. +919876543210.');
        setIsSubmitting(false);
        return;
      }
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

    if (!audioFile && !isEdit && !selectedTemplateId) {
      toast.error('Please record or upload a voice message, or choose a template.');
      setIsSubmitting(false);
      return;
    }

    if (recurrence !== 'none' && recurrenceEndDate && recurrenceEndDate < formData.scheduled_date) {
      toast.error('Recurrence end date must be on or after the scheduled date.');
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
    } else if (selectedTemplateId && !isEdit) {
      data.append('template_id', String(selectedTemplateId));
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
    if (fallbackType && fallbackType !== 'none') data.append('fallback_type', fallbackType);
    if (fallbackEmail.trim()) data.append('fallback_email', fallbackEmail.trim());
    if (originalText.trim())  data.append('original_text', originalText.trim());
    if (fallbackText.trim())  data.append('fallback_text', fallbackText.trim());
    if (preferredLanguage)    data.append('preferred_language', preferredLanguage);

    try {
      if (isEdit) {
        await api.put(`/reminders/${id}`, data);
        toast.success('Reminder updated successfully');
      } else if (recipientMode === 'group') {
        const res = await api.post(`/groups/${selectedGroupId}/remind`, data);
        toast.success(res.data.message);
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

  const handleSaveAsTemplate = async () => {
    const name = templateName.trim();
    if (!name) { toast.error('Please enter a template name.'); return; }
    if (!audioFile && !isEdit) { toast.error('Please record or upload audio before saving as template.'); return; }
    setSavingTemplate(true);
    try {
      if (isEdit) {
        await api.post(`/templates/from-reminder/${id}`, { name });
      } else {
        const fd = new FormData();
        fd.append('name', name);
        fd.append('title', formData.title || 'Untitled');
        fd.append('phone_number', formData.phone_number || '+910000000000');
        fd.append('audio_file', audioFile);
        if (recurrence !== 'none') fd.append('recurrence', recurrence);
        fd.append('retry_count', retryEnabled ? String(retryCount) : '0');
        fd.append('retry_gap_minutes', String(retryGapMinutes));
        await api.post('/templates', fd);
      }
      toast.success(`Template "${name}" saved!`);
      setShowTemplateSave(false);
      setTemplateName('');
      // Refresh list so it appears in the picker on next create
      api.get('/templates').then(r => setTemplates(r.data)).catch(() => {});
    } catch {
      toast.error('Could not save template. Please try again.');
    } finally {
      setSavingTemplate(false);
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
        {/* Template Picker — create mode only */}
        {!isEdit && templates.length > 0 && (
          <section className="glass-card p-6 rounded-2xl space-y-3">
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <LayoutTemplate className="w-4 h-4 text-primary-400" />
              Start from a Template
            </h2>
            <select
              value={selectedTemplateId ?? ''}
              onChange={e => applyTemplate(e.target.value)}
              className="glass-input w-full"
            >
              <option value="">— choose a template —</option>
              {templates.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
            {selectedTemplateId && (
              <p className="text-xs text-slate-500">
                Fields pre-filled from template. Audio from template will be used unless you record/upload a new one.
              </p>
            )}
          </section>
        )}

        {/* Basic Info Section */}
        <section className="glass-card p-6 rounded-2xl space-y-6">
          {/* Recipient mode toggle — create only */}
          {!isEdit && (
            <div>
              <label className="text-sm font-medium text-slate-300 mb-2 block">Send to</label>
              <div className="flex p-1 bg-white/5 rounded-xl max-w-xs">
                <button
                  type="button"
                  onClick={() => setRecipientMode('single')}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                    recipientMode === 'single' ? 'bg-primary-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Phone className="w-4 h-4" />
                  Single
                </button>
                <button
                  type="button"
                  onClick={() => setRecipientMode('group')}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                    recipientMode === 'group' ? 'bg-primary-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Users className="w-4 h-4" />
                  Group
                </button>
              </div>
            </div>
          )}

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
            {recipientMode === 'group' ? (
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                  <Users className="w-4 h-4 text-primary-400" />
                  Select Group
                </label>
                {groups.length === 0 ? (
                  <p className="text-xs text-slate-500">
                    No groups yet.{' '}
                    <a href="/groups" className="text-primary-400 hover:underline">Create a group first.</a>
                  </p>
                ) : (
                  <select
                    className="glass-input w-full"
                    value={selectedGroupId ?? ''}
                    onChange={e => setSelectedGroupId(Number(e.target.value) || null)}
                  >
                    <option value="">— choose a group —</option>
                    {groups.map(g => (
                      <option key={g.id} value={g.id}>
                        {g.name} ({g.member_count} member{g.member_count !== 1 ? 's' : ''})
                      </option>
                    ))}
                  </select>
                )}
                <p className="text-xs text-slate-500">Each group member will receive a separate call.</p>
              </div>
            ) : (
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                  <Phone className="w-4 h-4 text-emerald-400" />
                  Phone Number
                </label>
                <div className="relative">
                  <input
                    name="phone_number"
                    required={recipientMode === 'single'}
                    className="glass-input w-full pr-10"
                    placeholder="+919876543210"
                    value={formData.phone_number}
                    onChange={handleChange}
                  />
                  {contacts.length > 0 && (
                    <button
                      type="button"
                      onClick={() => { setShowContactPicker(v => !v); setContactSearch(''); }}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-primary-400 transition-colors"
                      title="Pick from contacts"
                    >
                      <BookUser className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <AnimatePresence>
                  {showContactPicker && (
                    <motion.div
                      key="contact-picker"
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="glass-card rounded-xl border border-white/10 overflow-hidden"
                    >
                      <div className="p-2 border-b border-white/10">
                        <input
                          className="glass-input w-full text-sm py-1.5"
                          placeholder="Search contacts…"
                          value={contactSearch}
                          onChange={e => setContactSearch(e.target.value)}
                          autoFocus
                        />
                      </div>
                      <ul className="max-h-48 overflow-y-auto divide-y divide-white/5">
                        {contacts
                          .filter(c =>
                            c.name.toLowerCase().includes(contactSearch.toLowerCase()) ||
                            c.phone_number.includes(contactSearch)
                          )
                          .map(c => (
                            <li key={c.id}>
                              <button
                                type="button"
                                onClick={() => {
                                  setFormData(prev => ({ ...prev, phone_number: c.phone_number }));
                                  setShowContactPicker(false);
                                }}
                                className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-white/5 transition-colors text-left"
                              >
                                <div className="bg-primary-600/20 p-1.5 rounded-full shrink-0">
                                  <Phone className="w-3.5 h-3.5 text-primary-400" />
                                </div>
                                <div className="min-w-0">
                                  <p className="text-sm text-white font-medium truncate">{c.name}</p>
                                  <p className="text-xs text-slate-400">{c.phone_number}</p>
                                </div>
                              </button>
                            </li>
                          ))
                        }
                        {contacts.filter(c =>
                          c.name.toLowerCase().includes(contactSearch.toLowerCase()) ||
                          c.phone_number.includes(contactSearch)
                        ).length === 0 && (
                          <li className="px-3 py-4 text-center text-slate-500 text-sm">No contacts found</li>
                        )}
                      </ul>
                    </motion.div>
                  )}
                </AnimatePresence>
                <p className="text-xs text-slate-500">Enter your phone number in E.164 format, e.g. +919876543210.</p>
              </div>
            )}
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
                min={new Date().toLocaleDateString('en-CA')}
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
                min={formData.scheduled_date || new Date().toLocaleDateString('en-CA')}
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

        {/* Fallback Section */}
        <section className="glass-card p-6 rounded-2xl space-y-5">
          <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-primary-400" />
            Fallback Notification (optional)
          </h2>
          <p className="text-xs text-slate-500">
            If the call is not answered after all attempts, we can send you a fallback notification.
          </p>

          {/* Fallback type selector */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-400">Notify me via</label>
            <div className="flex flex-wrap gap-2">
              {[
                { value: 'none',  label: 'None' },
                { value: 'sms',   label: '💬 SMS' },
                { value: 'email', label: '✉️ Email' },
                { value: 'both',  label: '📲 Both' },
              ].map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setFallbackType(opt.value)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    fallbackType === opt.value
                      ? 'bg-primary-600 border-primary-500 text-white'
                      : 'bg-white/5 border-white/10 text-slate-400 hover:text-white'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <AnimatePresence>
            {fallbackType !== 'none' && (
              <motion.div
                key="fallback-details"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-4 overflow-hidden"
              >
                {/* Email address — shown for email / both */}
                {(fallbackType === 'email' || fallbackType === 'both') && (
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-slate-400">Your email address</label>
                    <input
                      type="email"
                      value={fallbackEmail}
                      onChange={e => setFallbackEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="glass-input w-full text-sm"
                    />
                  </div>
                )}

                {/* Fallback message */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-slate-400">
                    Fallback message (English)
                    <span className="text-slate-600 ml-1">— leave blank for a default message</span>
                  </label>
                  <textarea
                    value={originalText}
                    onChange={e => { setOriginalText(e.target.value); setTranslationConfirmed(false); }}
                    placeholder="e.g., You missed your medication reminder."
                    maxLength={1000}
                    rows={2}
                    className="w-full glass-input text-sm resize-none"
                  />
                </div>

                {/* Translation — shown for sms / both */}
                {(fallbackType === 'sms' || fallbackType === 'both') && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                          <Languages className="w-3.5 h-3.5" />
                          Translate SMS to
                        </label>
                        <select
                          value={preferredLanguage}
                          onChange={e => { setPreferredLanguage(e.target.value); setTranslationConfirmed(false); }}
                          className="glass-input w-full text-sm"
                        >
                          <option value="">— send in English —</option>
                          {LANGUAGE_OPTIONS.map(l => (
                            <option key={l.code} value={l.code}>{l.name}</option>
                          ))}
                        </select>
                      </div>
                      <div className="flex items-end">
                        <button
                          type="button"
                          onClick={handleTranslate}
                          disabled={translating || !originalText.trim() || !preferredLanguage}
                          className="w-full btn-secondary py-2.5 flex items-center justify-center gap-2 text-sm disabled:opacity-40"
                        >
                          {translating
                            ? <Loader className="w-4 h-4 animate-spin" />
                            : <Languages className="w-4 h-4" />}
                          {translating ? 'Translating…' : 'Translate & Preview'}
                        </button>
                      </div>
                    </div>

                    {fallbackText && (
                      <motion.div
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-2"
                      >
                        <label className="text-xs font-medium text-slate-400">
                          Translated message
                          {preferredLanguage
                            ? ` (${LANGUAGE_OPTIONS.find(l => l.code === preferredLanguage)?.name ?? preferredLanguage})`
                            : ''} — edit if needed
                        </label>
                        <textarea
                          value={fallbackText}
                          onChange={e => { setFallbackText(e.target.value); setTranslationConfirmed(false); }}
                          maxLength={1000}
                          rows={2}
                          className="w-full glass-input text-sm resize-none"
                          dir={['ar', 'ur'].includes(preferredLanguage) ? 'rtl' : 'ltr'}
                        />
                        <button
                          type="button"
                          onClick={() => setTranslationConfirmed(true)}
                          className={`flex items-center gap-1.5 text-xs font-medium transition-colors ${
                            translationConfirmed ? 'text-emerald-400' : 'text-primary-400 hover:text-primary-300'
                          }`}
                        >
                          <CheckCircle className="w-3.5 h-3.5" />
                          {translationConfirmed ? 'Confirmed — will be used as SMS' : 'Confirm this translation'}
                        </button>
                      </motion.div>
                    )}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* Save as Template inline form */}
        <AnimatePresence>
          {showTemplateSave && (
            <motion.section
              key="tpl-save-form"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="glass-card p-5 rounded-2xl space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                  <Bookmark className="w-4 h-4 text-primary-400" />
                  Save as Template
                </span>
                <button type="button" onClick={() => setShowTemplateSave(false)} className="text-slate-500 hover:text-slate-300 transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <input
                value={templateName}
                onChange={e => setTemplateName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSaveAsTemplate()}
                placeholder="e.g. Weekly check-in, Medication reminder…"
                maxLength={100}
                className="glass-input w-full"
              />
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleSaveAsTemplate}
                  disabled={savingTemplate || !templateName.trim()}
                  className="flex-1 btn-primary py-2.5 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {savingTemplate ? <Loader className="w-4 h-4 animate-spin" /> : <><Bookmark className="w-4 h-4" /> Save Template</>}
                </button>
                <button type="button" onClick={() => setShowTemplateSave(false)} className="btn-secondary px-6">
                  Cancel
                </button>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

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
            onClick={() => { setShowTemplateSave(v => !v); if (!templateName) setTemplateName(formData.title); }}
            title="Save current settings as a reusable template"
            className="btn-secondary px-4 flex items-center gap-2"
          >
            <Bookmark className="w-5 h-5" />
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
