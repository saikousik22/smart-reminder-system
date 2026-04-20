import React from 'react';
import {
  Phone, Calendar, Clock, Trash2, Edit, Play,
  CheckCircle, AlertCircle, PhoneCall, PhoneMissed, PhoneOff, Repeat, RefreshCw
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

const RECURRENCE_LABELS = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
  weekdays: 'Weekdays',
};

const ReminderCard = ({ reminder, onDelete }) => {
  const parseUtcDate = (isoString) => {
    const normalized = isoString.match(/[+-]\d{2}:\d{2}$|Z$/)
      ? isoString
      : `${isoString}Z`;
    return new Date(normalized);
  };

  const date = parseUtcDate(reminder.scheduled_time);

  const statusConfig = {
    pending:   { color: 'text-yellow-400',  bg: 'bg-yellow-400/10',  icon: Clock,        label: 'Pending' },
    calling:   { color: 'text-blue-400',    bg: 'bg-blue-400/10',    icon: PhoneCall,    label: 'Calling…', pulse: true },
    answered:  { color: 'text-emerald-400', bg: 'bg-emerald-400/10', icon: CheckCircle,  label: 'Answered' },
    'no-answer': { color: 'text-orange-400', bg: 'bg-orange-400/10', icon: PhoneMissed,  label: 'No Answer' },
    busy:      { color: 'text-orange-400',  bg: 'bg-orange-400/10',  icon: PhoneOff,     label: 'Busy' },
    failed:    { color: 'text-rose-400',    bg: 'bg-rose-400/10',    icon: AlertCircle,  label: 'Failed' },
    // legacy status kept for any existing records
    sent:      { color: 'text-emerald-400', bg: 'bg-emerald-400/10', icon: CheckCircle,  label: 'Sent' },
  };

  const statusCfg = statusConfig[reminder.status] || statusConfig.pending;
  const StatusIcon = statusCfg.icon;

  const handlePlayAudio = () => {
    const audio = new Audio(`/audio/${reminder.audio_filename}`);
    audio.play().catch(e => console.error('Playback failed', e));
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="glass-card rounded-xl p-5 hover:border-primary-500/30 transition-colors group flex flex-col h-full"
    >
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
        </div>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Link
            to={`/edit/${reminder.id}`}
            className="p-1.5 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <Edit className="w-4 h-4" />
          </Link>
          <button
            onClick={onDelete}
            className="p-1.5 hover:bg-rose-500/10 rounded-lg text-slate-400 hover:text-rose-400 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <h3 className="text-lg font-bold text-white mb-3 line-clamp-1">{reminder.title}</h3>

      <div className="space-y-2.5 mb-6 flex-grow">
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

      <button
        onClick={handlePlayAudio}
        className="w-full flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 text-slate-200 py-2.5 rounded-lg border border-white/5 transition-colors text-sm font-medium"
      >
        <Play className="w-4 h-4 fill-current" />
        Preview Message
      </button>
    </motion.div>
  );
};

export default ReminderCard;
