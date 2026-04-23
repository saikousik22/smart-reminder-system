import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { toast } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Plus, Pencil, Trash2, Check, X, Phone, User, Search } from 'lucide-react';

const E164_RE = /^\+[1-9]\d{0,14}$/;

const emptyForm = { name: '', phone_number: '' };

const ContactRow = ({ contact, onSaved, onDelete }) => {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ name: contact.name, phone_number: contact.phone_number });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('Name is required.'); return; }
    if (!E164_RE.test(form.phone_number)) {
      toast.error('Enter a valid E.164 phone number, e.g. +919876543210');
      return;
    }
    setSaving(true);
    try {
      const { data } = await api.put(`/contacts/${contact.id}`, form);
      onSaved(data);
      setEditing(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not update contact.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setForm({ name: contact.name, phone_number: contact.phone_number });
    setEditing(false);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="glass-card p-4 rounded-xl flex items-center gap-4"
    >
      <div className="bg-primary-600/20 p-2.5 rounded-full shrink-0">
        <User className="w-5 h-5 text-primary-400" />
      </div>

      {editing ? (
        <div className="flex flex-1 flex-col sm:flex-row gap-2">
          <input
            className="glass-input flex-1 text-sm"
            placeholder="Name"
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          />
          <input
            className="glass-input flex-1 text-sm"
            placeholder="+919876543210"
            value={form.phone_number}
            onChange={e => setForm(f => ({ ...f, phone_number: e.target.value }))}
          />
        </div>
      ) : (
        <div className="flex-1 min-w-0">
          <p className="text-white font-medium truncate">{contact.name}</p>
          <p className="text-slate-400 text-sm flex items-center gap-1.5">
            <Phone className="w-3.5 h-3.5" />
            {contact.phone_number}
          </p>
        </div>
      )}

      <div className="flex items-center gap-1 shrink-0">
        {editing ? (
          <>
            <button
              onClick={handleSave}
              disabled={saving}
              className="p-2 text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors disabled:opacity-50"
              title="Save"
            >
              <Check className="w-4 h-4" />
            </button>
            <button
              onClick={handleCancel}
              className="p-2 text-slate-400 hover:bg-white/10 rounded-lg transition-colors"
              title="Cancel"
            >
              <X className="w-4 h-4" />
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => setEditing(true)}
              className="p-2 text-slate-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-colors"
              title="Edit"
            >
              <Pencil className="w-4 h-4" />
            </button>
            <button
              onClick={() => onDelete(contact)}
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </>
        )}
      </div>
    </motion.div>
  );
};

const Contacts = () => {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState(emptyForm);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    api.get('/contacts')
      .then(r => setContacts(r.data))
      .catch(() => toast.error('Failed to load contacts'))
      .finally(() => setLoading(false));
  }, []);

  const handleAdd = async () => {
    if (!addForm.name.trim()) { toast.error('Name is required.'); return; }
    if (!E164_RE.test(addForm.phone_number)) {
      toast.error('Enter a valid E.164 phone number, e.g. +919876543210');
      return;
    }
    setAdding(true);
    try {
      const { data } = await api.post('/contacts', addForm);
      setContacts(prev => [...prev, data].sort((a, b) => a.name.localeCompare(b.name)));
      setAddForm(emptyForm);
      setShowAdd(false);
      toast.success(`Contact "${data.name}" added!`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not add contact.');
    } finally {
      setAdding(false);
    }
  };

  const handleSaved = (updated) => {
    setContacts(prev =>
      prev.map(c => c.id === updated.id ? updated : c).sort((a, b) => a.name.localeCompare(b.name))
    );
    toast.success('Contact updated');
  };

  const handleDelete = (contact) => {
    toast((t) => (
      <span className="flex items-center gap-3">
        Delete <strong>{contact.name}</strong>?
        <button
          className="bg-rose-500 text-white px-2 py-1 rounded text-xs font-medium"
          onClick={() => { toast.dismiss(t.id); confirmDelete(contact); }}
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

  const confirmDelete = async (contact) => {
    try {
      await api.delete(`/contacts/${contact.id}`);
      setContacts(prev => prev.filter(c => c.id !== contact.id));
      toast.success('Contact deleted');
    } catch {
      toast.error('Could not delete contact');
    }
  };

  const filtered = contacts.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.phone_number.includes(search)
  );

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-primary-600/20 p-3 rounded-2xl">
            <Users className="w-7 h-7 text-primary-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Contacts</h1>
            <p className="text-slate-400 text-sm">Saved numbers for quick reminder setup</p>
          </div>
        </div>
        <button
          onClick={() => { setShowAdd(v => !v); setAddForm(emptyForm); }}
          className="btn-primary flex items-center gap-2 justify-center"
        >
          <Plus className="w-4 h-4" />
          Add Contact
        </button>
      </div>

      <AnimatePresence>
        {showAdd && (
          <motion.div
            key="add-form"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="glass-card p-5 rounded-2xl space-y-4"
          >
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Plus className="w-4 h-4 text-primary-400" />
              New Contact
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <input
                className="glass-input"
                placeholder="Name"
                value={addForm.name}
                onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))}
                onKeyDown={e => e.key === 'Enter' && handleAdd()}
              />
              <input
                className="glass-input"
                placeholder="+919876543210"
                value={addForm.phone_number}
                onChange={e => setAddForm(f => ({ ...f, phone_number: e.target.value }))}
                onKeyDown={e => e.key === 'Enter' && handleAdd()}
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleAdd}
                disabled={adding}
                className="btn-primary flex items-center gap-2 disabled:opacity-50"
              >
                {adding ? 'Saving…' : <><Check className="w-4 h-4" /> Save</>}
              </button>
              <button onClick={() => setShowAdd(false)} className="btn-secondary px-5">
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
        <input
          className="glass-input w-full pl-11"
          placeholder="Search by name or number…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="glass-card h-16 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <motion.div layout className="space-y-3">
          <AnimatePresence>
            {filtered.map(c => (
              <ContactRow
                key={c.id}
                contact={c}
                onSaved={handleSaved}
                onDelete={handleDelete}
              />
            ))}
          </AnimatePresence>
        </motion.div>
      ) : (
        <div className="glass-card p-10 rounded-2xl text-center">
          <Users className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">
            {search ? 'No contacts match your search.' : 'No contacts yet. Add one to get started!'}
          </p>
        </div>
      )}
    </div>
  );
};

export default Contacts;
