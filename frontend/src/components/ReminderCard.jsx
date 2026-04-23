import React, { useState } from 'react';
import {
  Phone, Calendar, Clock, Trash2, Edit, Play,
  CheckCircle, AlertCircle, PhoneCall, PhoneMissed, PhoneOff, Repeat, RefreshCw,
  Star, MessageSquare, X, Loader, Bookmark, Download, Languages, Send, Users
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import api from '../api/axios';

const RECURRENCE_LABELS = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
  weekdays: 'Weekdays',
};

const LANGUAGE_NAMES = {
  hi: 'Hindi', te: 'Telugu', ta: 'Tamil', kn: 'Kannada', ml: 'Malayalam',
  mr: 'Marathi', bn: 'Bengali', gu: 'Gujarati', pa: 'Punjabi', ur: 'Urdu',
  fr: 'French', es: 'Spanish', de: 'German', ar: 'Arabic', 'zh-CN': 'Chinese',
  ja: 'Japanese', ko: 'Korean', pt: 'Portuguese', ru: 'Russian', it: 'Italian',
};

const TERMINAL_STATUSES = new Set(['answered', 'no-answer', 'busy', 'failed']);

const ReminderCard = ({ reminder, onDelete }) => {
  const parseUtcDate = (isoString) => {
    const normalized = isoString.match(/[+-]\d{2}:\d{2}$|Z$/)
      ? isoString
      : `${isoString}Z`;
    return new Date(normalized);
  };

  const date = parseUtcDate(reminder.scheduled_time);

  // Track submitted feedback locally so UI updates immediately after submit
  const [localRating, setLocalRating]   = useState(reminder.feedback_rating ?? null);
  const [localComment, setLocalComment] = useState(reminder.feedback_comment ?? '');
  const [showForm, setShowForm]         = useState(false);
  const [hoverStar, setHoverStar]       = useState(0);
  const [pendingRating, setPendingRating]   = useState(0);
  const [pendingComment, setPendingComment] = useState('');
  const [submitting, setSubmitting]     = useState(false);

  const [showTemplateSave, setShowTemplateSave] = useState(false);
  const [templateName, setTemplateName]         = useState('');
  const [savingTemplate, setSavingTemplate]     = useState(false);

  const handleSaveAsTemplate = async () => {
    const name = templateName.trim();
    if (!name) { toast.error('Please enter a template name.'); return; }
    setSavingTemplate(true);
    try {
      await api.post(`/templates/from-reminder/${reminder.id}`, { name });
      toast.success(`Template "${name}" saved!`);
      setShowTemplateSave(false);
      setTemplateName('');
    } catch {
      toast.error('Could not save template. Please try again.');
    } finally {
      setSavingTemplate(false);
    }
  };

  const isTerminal = TERMINAL_STATUSES.has(reminder.status);
  const hasRating  = localRating !== null;

  const handleFeedbackSubmit = async () => {
    if (!pendingRating) {
      toast.error('Please select a star rating first.');
      return;
    }
    setSubmitting(true);
    try {
      await api.put(`/reminders/${reminder.id}/feedback`, {
        rating: pendingRating,
        comment: pendingComment.trim() || null,
      });
      setLocalRating(pendingRating);
      setLocalComment(pendingComment.trim());
      setShowForm(false);
      toast.success('Feedback saved!');
    } catch {
      toast.error('Could not save feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const openForm = () => {
    setPendingRating(localRating ?? 0);
    setPendingComment(localComment ?? '');
    setHoverStar(0);
    setShowForm(true);
  };

  const statusConfig = {
    pending:      { color: 'text-yellow-400',  bg: 'bg-yellow-400/10',  icon: Clock,        label: 'Pending' },
    processing:   { color: 'text-blue-400',    bg: 'bg-blue-400/10',    icon: PhoneCall,    label: 'Processing…', pulse: true },
    calling:      { color: 'text-blue-400',    bg: 'bg-blue-400/10',    icon: PhoneCall,    label: 'Calling…', pulse: true },
    answered:     { color: 'text-emerald-400', bg: 'bg-emerald-400/10', icon: CheckCircle,  label: 'Answered' },
    'no-answer':  { color: 'text-orange-400',  bg: 'bg-orange-400/10',  icon: PhoneMissed,  label: 'No Answer' },
    busy:         { color: 'text-orange-400',  bg: 'bg-orange-400/10',  icon: PhoneOff,     label: 'Busy' },
    failed:       { color: 'text-rose-400',    bg: 'bg-rose-400/10',    icon: AlertCircle,  label: 'Failed' },
    sent:         { color: 'text-emerald-400', bg: 'bg-emerald-400/10', icon: CheckCircle,  label: 'Sent' },
  };

  const statusCfg = statusConfig[reminder.status] || statusConfig.pending;
  const StatusIcon = statusCfg.icon;

  const handlePlayAudio = () => {
    if (!reminder.audio_filename || !/^[a-f0-9-]{36}\.(wav|mp3)$/.test(reminder.audio_filename)) {
      toast.error('Invalid audio file.');
      return;
    }
    const audio = new Audio(`/audio/${reminder.audio_filename}`);
    audio.play().catch(() => toast.error('Could not play audio'));
  };

  const handleExportIcs = async () => {
    try {
      const response = await api.get(`/reminders/${reminder.id}/export-ics`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([response.data], { type: 'text/calendar' }));
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${reminder.title.replace(/[^\w-]/g, '_')}.ics`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Failed to export calendar file');
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="glass-card rounded-xl p-5 hover:border-primary-500/30 transition-colors group flex flex-col h-full"
    >
      {/* ── Header ── */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex flex-col gap-1.5">
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold w-fit ${statusCfg.bg} ${statusCfg.color}`}>
            <StatusIcon className={`w-3.5 h-3.5 ${statusCfg.pulse ? 'animate-pulse' : ''}`} />
            {statusCfg.label}
          </div>
          {reminder.recurrence && (
            <div className="flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-medium bg-primary-500/10 text-primary-400 w-fit">
              <Repeat className="w-3 h-3" />
              {RECURRENCE_LABELS[reminder.recurrence] ?? reminder.recurrence}
            </div>
          )}
          {reminder.retry_count > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 w-fit">
              <RefreshCw className="w-3 h-3" />
              Attempt {reminder.attempt_number} of {reminder.retry_count + 1}
            </div>
          )}
          {reminder.group_name && (
            <div className="flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 w-fit">
              <Users className="w-3 h-3" />
              {reminder.group_name}
            </div>
          )}
          {reminder.fallback_sent && (
            <div className="flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-medium bg-sky-500/10 text-sky-400 w-fit">
              <Send className="w-3 h-3" />
              SMS Sent
            </div>
          )}
          {reminder.preferred_language && !reminder.fallback_sent && (
            <div className="flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-medium bg-violet-500/10 text-violet-400 w-fit">
              <Languages className="w-3 h-3" />
              SMS: {LANGUAGE_NAMES[reminder.preferred_language] ?? reminder.preferred_language}
            </div>
          )}
        </div>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => { setShowTemplateSave(v => !v); setTemplateName(reminder.title); }}
            aria-label="Save as template"
            className="p-1.5 hover:bg-primary-500/10 rounded-lg text-slate-400 hover:text-primary-400 transition-colors"
          >
            <Bookmark className="w-4 h-4" />
          </button>
          <Link
            to={`/edit/${reminder.id}`}
            aria-label={`Edit ${reminder.title}`}
            className="p-1.5 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <Edit className="w-4 h-4" />
          </Link>
          <button
            onClick={onDelete}
            aria-label={`Delete ${reminder.title}`}
            className="p-1.5 hover:bg-rose-500/10 rounded-lg text-slate-400 hover:text-rose-400 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <h3 className="text-lg font-bold text-white mb-3 line-clamp-1">{reminder.title}</h3>

      {/* ── Details ── */}
      <div className="space-y-2.5 mb-4 flex-grow">
        <div className="flex items-center gap-3 text-slate-400">
          <Phone className="w-4 h-4 text-emerald-500" />
          <span className="text-sm font-medium">{reminder.phone_number}</span>
        </div>
        <div className="flex items-center gap-3 text-slate-400">
          <Calendar className="w-4 h-4 text-primary-400" />
          <span className="text-sm">
            {date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
          </span>
        </div>
        <div className="flex items-center gap-3 text-slate-400">
          <Clock className="w-4 h-4 text-primary-400" />
          <span className="text-sm">
            {date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>

      {/* ── Feedback Section ── */}
      <AnimatePresence mode="wait">
        {isTerminal && (
          <motion.div
            key="feedback-area"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mb-3"
          >
            {!showForm ? (
              /* ── Display state ── */
              <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/5 border border-white/5">
                {hasRating ? (
                  <>
                    <div className="flex items-center gap-1.5">
                      <div className="flex gap-0.5">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <Star
                            key={s}
                            className={`w-3.5 h-3.5 ${s <= localRating ? 'text-amber-400 fill-amber-400' : 'text-slate-600'}`}
                          />
                        ))}
                      </div>
                      {localComment && (
                        <span className="text-xs text-slate-400 truncate max-w-[120px]" title={localComment}>
                          "{localComment}"
                        </span>
                      )}
                    </div>
                    <button
                      onClick={openForm}
                      aria-label="Edit feedback"
                      className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      Edit
                    </button>
                  </>
                ) : (
                  <>
                    <span className="text-xs text-slate-500 flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5" />
                      How was this call?
                    </span>
                    <button
                      onClick={openForm}
                      aria-label="Rate this call"
                      className="text-xs text-primary-400 hover:text-primary-300 font-medium transition-colors"
                    >
                      Rate it
                    </button>
                  </>
                )}
              </div>
            ) : (
              /* ── Form state ── */
              <motion.div
                key="feedback-form"
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="rounded-lg bg-white/5 border border-white/10 p-3 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-300">Rate this call</span>
                  <button
                    onClick={() => setShowForm(false)}
                    aria-label="Close feedback form"
                    className="text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Stars */}
                <div className="flex gap-1" onMouseLeave={() => setHoverStar(0)}>
                  {[1, 2, 3, 4, 5].map((s) => (
                    <button
                      key={s}
                      type="button"
                      aria-label={`Rate ${s} star${s > 1 ? 's' : ''}`}
                      onClick={() => setPendingRating(s)}
                      onMouseEnter={() => setHoverStar(s)}
                      className="transition-transform hover:scale-110"
                    >
                      <Star
                        className={`w-6 h-6 transition-colors ${
                          s <= (hoverStar || pendingRating)
                            ? 'text-amber-400 fill-amber-400'
                            : 'text-slate-600'
                        }`}
                      />
                    </button>
                  ))}
                </div>

                {/* Comment */}
                <textarea
                  value={pendingComment}
                  onChange={(e) => setPendingComment(e.target.value)}
                  placeholder="Optional comment… (max 500 chars)"
                  maxLength={500}
                  rows={2}
                  className="w-full glass-input text-xs resize-none"
                />

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleFeedbackSubmit}
                    disabled={submitting || !pendingRating}
                    className="flex-1 btn-primary py-1.5 text-xs flex items-center justify-center gap-1.5 disabled:opacity-50"
                  >
                    {submitting ? <Loader className="w-3.5 h-3.5 animate-spin" /> : 'Submit'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="flex-1 btn-secondary py-1.5 text-xs"
                  >
                    Cancel
                  </button>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Save as Template ── */}
      <AnimatePresence>
        {showTemplateSave && (
          <motion.div
            key="template-save"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-3 rounded-lg bg-white/5 border border-white/10 p-3 space-y-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                <Bookmark className="w-3.5 h-3.5 text-primary-400" />
                Save as Template
              </span>
              <button onClick={() => setShowTemplateSave(false)} className="text-slate-500 hover:text-slate-300 transition-colors">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <input
              value={templateName}
              onChange={e => setTemplateName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSaveAsTemplate()}
              placeholder="Template name…"
              maxLength={100}
              className="w-full glass-input text-xs"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSaveAsTemplate}
                disabled={savingTemplate || !templateName.trim()}
                className="flex-1 btn-primary py-1.5 text-xs flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                {savingTemplate ? <Loader className="w-3.5 h-3.5 animate-spin" /> : 'Save'}
              </button>
              <button type="button" onClick={() => setShowTemplateSave(false)} className="flex-1 btn-secondary py-1.5 text-xs">
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Preview Button ── */}
      <button
        onClick={handlePlayAudio}
        aria-label="Preview voice message"
        className="w-full flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 text-slate-200 py-2.5 rounded-lg border border-white/5 transition-colors text-sm font-medium"
      >
        <Play className="w-4 h-4 fill-current" />
        Preview Message
      </button>

      {/* ── Export to Calendar ── */}
      <button
        onClick={handleExportIcs}
        aria-label="Export to calendar"
        className="w-full flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-slate-200 py-2 rounded-lg border border-white/5 transition-colors text-xs font-medium mt-1"
      >
        <Download className="w-3.5 h-3.5" />
        Export to Calendar
      </button>
    </motion.div>
  );
};

export default ReminderCard;
