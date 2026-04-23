import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import ReminderCard from '../components/ReminderCard';
import { Plus, Search, Filter, RefreshCw, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';

const Dashboard = () => {
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const debounceRef = useRef(null);

  const fetchReminders = async () => {
    setLoading(true);
    try {
      const response = await api.get('/reminders');
      setReminders(response.data);
    } catch (error) {
      toast.error('Failed to load reminders');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReminders();

    const tick = () => {
      if (!document.hidden) fetchReminders();
    };
    const interval = setInterval(tick, 30000);
    document.addEventListener('visibilitychange', tick);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', tick);
    };
  }, []);

  const handleDelete = (id) => {
    toast((t) => (
      <span className="flex items-center gap-3">
        Delete this reminder?
        <button
          className="bg-rose-500 text-white px-2 py-1 rounded text-xs font-medium"
          onClick={() => { toast.dismiss(t.id); confirmDelete(id); }}
        >
          Delete
        </button>
        <button
          className="bg-slate-600 text-white px-2 py-1 rounded text-xs font-medium"
          onClick={() => toast.dismiss(t.id)}
        >
          Cancel
        </button>
      </span>
    ), { duration: 5000 });
  };

  const confirmDelete = async (id) => {
    try {
      await api.delete(`/reminders/${id}`);
      setReminders(prev => prev.filter(r => r.id !== id));
      toast.success('Reminder deleted');
    } catch {
      toast.error('Could not delete reminder');
    }
  };

  const filteredReminders = reminders.filter(r => {
    const matchesFilter = filter === 'all' || r.status === filter;
    const matchesSearch = r.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          r.phone_number.includes(searchTerm);
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Your Reminders</h1>
          <p className="text-slate-400">Manage and track your voice call schedules</p>
        </div>
        <Link to="/create" className="btn-primary flex items-center justify-center gap-2">
          <Plus className="w-5 h-5" />
          Create Reminder
        </Link>
      </div>

      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-grow">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 w-5 h-5" />
          <input
            type="text"
            placeholder="Search by title or phone..."
            className="glass-input w-full pl-14"
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              clearTimeout(debounceRef.current);
              debounceRef.current = setTimeout(() => setSearchTerm(e.target.value), 300);
            }}
          />
        </div>
        <div className="flex gap-2">
          <select 
            className="glass-input min-w-[140px] text-white"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="calling">Calling</option>
            <option value="answered">Answered</option>
            <option value="no-answer">No Answer</option>
            <option value="busy">Busy</option>
            <option value="failed">Failed</option>
          </select>
          <button 
            onClick={fetchReminders}
            className="p-2 glass-card rounded-lg border-white/10 hover:bg-white/10 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {loading && reminders.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="glass-card h-48 rounded-xl animate-pulse"></div>
          ))}
        </div>
      ) : filteredReminders.length > 0 ? (
        <motion.div 
          layout
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          <AnimatePresence>
            {filteredReminders.map(reminder => (
              <ReminderCard 
                key={reminder.id} 
                reminder={reminder} 
                onDelete={() => handleDelete(reminder.id)} 
              />
            ))}
          </AnimatePresence>
        </motion.div>
      ) : (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="glass-card p-12 rounded-2xl text-center flex flex-col items-center"
        >
          <div className="bg-white/5 p-4 rounded-full mb-4">
            <AlertCircle className="w-12 h-12 text-slate-500" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">No reminders found</h3>
          <p className="text-slate-400 mb-6 max-w-sm">
            {searchTerm || filter !== 'all' 
              ? "Try adjusting your filters or search terms to find what you're looking for." 
              : "You haven't created any reminders yet. Start by creating your first voice reminder!"}
          </p>
          {!searchTerm && filter === 'all' && (
            <Link to="/create" className="btn-secondary">
              Create First Reminder
            </Link>
          )}
        </motion.div>
      )}
    </div>
  );
};

export default Dashboard;
