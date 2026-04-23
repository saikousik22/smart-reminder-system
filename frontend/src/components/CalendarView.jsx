import React, { useState, useEffect } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Phone, Clock, Calendar, Download, Repeat } from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../api/axios';

const STATUS_COLORS = {
  pending:      '#eab308',
  processing:   '#3b82f6',
  calling:      '#3b82f6',
  answered:     '#10b981',
  'no-answer':  '#f97316',
  busy:         '#f97316',
  failed:       '#f43f5e',
};

const RECURRENCE_LABELS = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
  weekdays: 'Weekdays',
};

const parseUtcDate = (iso) => {
  const normalized = /[+-]\d{2}:\d{2}$|Z$/.test(iso) ? iso : `${iso}Z`;
  return new Date(normalized);
};

const CalendarView = () => {
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedReminder, setSelectedReminder] = useState(null);

  useEffect(() => {
    api.get('/reminders')
      .then(({ data }) => setReminders(data))
      .catch(() => toast.error('Failed to load reminders for calendar'))
      .finally(() => setLoading(false));
  }, []);

  const events = reminders.map((r) => ({
    id: String(r.id),
    title: r.title,
    start: parseUtcDate(r.scheduled_time).toISOString(),
    backgroundColor: STATUS_COLORS[r.status] ?? '#6366f1',
    borderColor:     STATUS_COLORS[r.status] ?? '#6366f1',
    extendedProps: { reminder: r },
  }));

  const handleExportIcs = async (id, title) => {
    try {
      const response = await api.get(`/reminders/${id}/export-ics`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([response.data], { type: 'text/calendar' }));
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${title.replace(/[^\w-]/g, '_')}.ics`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Failed to export calendar file');
    }
  };

  if (loading) {
    return <div className="glass-card rounded-xl p-8 animate-pulse h-[600px]" />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Calendar</h1>
        <p className="text-slate-400">View your reminders by date</p>
      </div>

      <div className="glass-card rounded-xl p-4 fc-dark">
        <FullCalendar
          plugins={[dayGridPlugin]}
          initialView="dayGridMonth"
          events={events}
          eventClick={({ event }) => setSelectedReminder(event.extendedProps.reminder)}
          height="auto"
          headerToolbar={{ left: 'prev,next today', center: 'title', right: '' }}
          eventTimeFormat={{ hour: '2-digit', minute: '2-digit', meridiem: 'short' }}
          eventDisplay="block"
        />
      </div>

      <AnimatePresence>
        {selectedReminder && (
          <EventModal
            reminder={selectedReminder}
            onClose={() => setSelectedReminder(null)}
            onExport={handleExportIcs}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

const EventModal = ({ reminder, onClose, onExport }) => {
  const date = parseUtcDate(reminder.scheduled_time);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.92, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.92, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        className="glass-card rounded-2xl p-6 w-full max-w-md space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-xl font-bold text-white leading-tight">{reminder.title}</h2>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-colors shrink-0"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3 text-sm">
          <DetailRow icon={<Phone className="w-4 h-4 text-emerald-400" />} label={reminder.phone_number} />
          <DetailRow
            icon={<Calendar className="w-4 h-4 text-primary-400" />}
            label={date.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          />
          <DetailRow
            icon={<Clock className="w-4 h-4 text-primary-400" />}
            label={date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
          />
          {reminder.recurrence && (
            <DetailRow
              icon={<Repeat className="w-4 h-4 text-primary-400" />}
              label={`Repeats ${RECURRENCE_LABELS[reminder.recurrence] ?? reminder.recurrence}`}
            />
          )}
        </div>

        <div className="pt-1 flex flex-col gap-2">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold w-fit"
            style={{
              backgroundColor: `${STATUS_COLORS[reminder.status] ?? '#6366f1'}20`,
              color: STATUS_COLORS[reminder.status] ?? '#6366f1',
            }}
          >
            {reminder.status.replace('-', ' ').replace(/^\w/, (c) => c.toUpperCase())}
          </div>

          <button
            onClick={() => onExport(reminder.id, reminder.title)}
            className="w-full flex items-center justify-center gap-2 btn-secondary py-2.5 text-sm mt-2"
          >
            <Download className="w-4 h-4" />
            Export to Calendar (.ics)
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

const DetailRow = ({ icon, label }) => (
  <div className="flex items-center gap-3 text-slate-300">
    <span className="shrink-0">{icon}</span>
    <span>{label}</span>
  </div>
);

export default CalendarView;
