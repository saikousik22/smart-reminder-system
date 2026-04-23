import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import { toast } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users, Plus, Pencil, Trash2, Check, X,
  ChevronDown, ChevronUp, UserPlus, UserMinus,
  Bell, Phone
} from 'lucide-react';

const Groups = () => {
  const [groups, setGroups]     = useState([]);
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading]   = useState(true);

  const [showAdd, setShowAdd]   = useState(false);
  const [newName, setNewName]   = useState('');
  const [adding, setAdding]     = useState(false);

  const [editId, setEditId]     = useState(null);
  const [editName, setEditName] = useState('');
  const [saving, setSaving]     = useState(false);

  const [expandedId, setExpandedId]       = useState(null);
  const [addingMemberId, setAddingMemberId] = useState(null);

  useEffect(() => {
    Promise.all([api.get('/groups'), api.get('/contacts')])
      .then(([g, c]) => { setGroups(g.data); setContacts(c.data); })
      .catch(() => toast.error('Failed to load data'))
      .finally(() => setLoading(false));
  }, []);

  const handleCreateGroup = async () => {
    const name = newName.trim();
    if (!name) { toast.error('Group name is required.'); return; }
    setAdding(true);
    try {
      const { data } = await api.post('/groups', { name });
      setGroups(prev => [...prev, data].sort((a, b) => a.name.localeCompare(b.name)));
      setNewName('');
      setShowAdd(false);
      toast.success(`Group "${data.name}" created!`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not create group.');
    } finally {
      setAdding(false);
    }
  };

  const handleRename = async (groupId) => {
    const name = editName.trim();
    if (!name) { toast.error('Group name is required.'); return; }
    setSaving(true);
    try {
      const { data } = await api.put(`/groups/${groupId}`, { name });
      setGroups(prev => prev.map(g => g.id === groupId ? data : g).sort((a, b) => a.name.localeCompare(b.name)));
      setEditId(null);
      toast.success('Group renamed');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not rename group.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (group) => {
    toast((t) => (
      <span className="flex items-center gap-3">
        Delete <strong>{group.name}</strong>?
        <button className="bg-rose-500 text-white px-2 py-1 rounded text-xs font-medium"
          onClick={() => { toast.dismiss(t.id); confirmDelete(group.id, group.name); }}>
          Delete
        </button>
        <button className="bg-slate-600 text-white px-2 py-1 rounded text-xs font-medium"
          onClick={() => toast.dismiss(t.id)}>
          Cancel
        </button>
      </span>
    ), { duration: 5000 });
  };

  const confirmDelete = async (groupId, name) => {
    try {
      await api.delete(`/groups/${groupId}`);
      setGroups(prev => prev.filter(g => g.id !== groupId));
      toast.success(`Group "${name}" deleted`);
    } catch {
      toast.error('Could not delete group');
    }
  };

  const handleAddMember = async (groupId, contactId) => {
    try {
      const { data } = await api.post(`/groups/${groupId}/members`, { contact_id: contactId });
      setGroups(prev => prev.map(g => g.id === groupId ? data : g));
      setAddingMemberId(null);
      toast.success('Member added');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not add member.');
    }
  };

  const handleRemoveMember = async (groupId, contactId, contactName) => {
    try {
      const { data } = await api.delete(`/groups/${groupId}/members/${contactId}`);
      setGroups(prev => prev.map(g => g.id === groupId ? data : g));
      toast.success(`${contactName} removed`);
    } catch {
      toast.error('Could not remove member');
    }
  };

  const availableContacts = (group) =>
    contacts.filter(c => !group.members.some(m => m.contact_id === c.id));

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-primary-600/20 p-3 rounded-2xl">
            <Users className="w-7 h-7 text-primary-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Groups</h1>
            <p className="text-slate-400 text-sm">Send one reminder to multiple contacts</p>
          </div>
        </div>
        <button
          onClick={() => { setShowAdd(v => !v); setNewName(''); }}
          className="btn-primary flex items-center gap-2 justify-center"
        >
          <Plus className="w-4 h-4" />
          New Group
        </button>
      </div>

      {/* Add group form */}
      <AnimatePresence>
        {showAdd && (
          <motion.div
            key="add-group"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="glass-card p-5 rounded-2xl space-y-4"
          >
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Plus className="w-4 h-4 text-primary-400" /> New Group
            </h2>
            <input
              className="glass-input w-full"
              placeholder="e.g. Family, Team, Clients"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreateGroup()}
              autoFocus
            />
            <div className="flex gap-3">
              <button onClick={handleCreateGroup} disabled={adding}
                className="btn-primary flex items-center gap-2 disabled:opacity-50">
                {adding ? 'Creating…' : <><Check className="w-4 h-4" /> Create</>}
              </button>
              <button onClick={() => setShowAdd(false)} className="btn-secondary px-5">Cancel</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Groups list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2].map(i => <div key={i} className="glass-card h-20 rounded-xl animate-pulse" />)}
        </div>
      ) : groups.length === 0 ? (
        <div className="glass-card p-10 rounded-2xl text-center">
          <Users className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No groups yet. Create one to get started!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {groups.map(group => (
            <motion.div
              key={group.id}
              layout
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card rounded-xl overflow-hidden"
            >
              {/* Group header row */}
              <div className="flex items-center gap-3 p-4">
                <div className="bg-primary-600/20 p-2 rounded-full shrink-0">
                  <Users className="w-4 h-4 text-primary-400" />
                </div>

                {editId === group.id ? (
                  <input
                    className="glass-input flex-1 text-sm"
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') handleRename(group.id); if (e.key === 'Escape') setEditId(null); }}
                    autoFocus
                  />
                ) : (
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium">{group.name}</p>
                    <p className="text-slate-500 text-xs">{group.member_count} member{group.member_count !== 1 ? 's' : ''}</p>
                  </div>
                )}

                <div className="flex items-center gap-1 shrink-0">
                  {editId === group.id ? (
                    <>
                      <button onClick={() => handleRename(group.id)} disabled={saving}
                        className="p-2 text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors disabled:opacity-50">
                        <Check className="w-4 h-4" />
                      </button>
                      <button onClick={() => setEditId(null)}
                        className="p-2 text-slate-400 hover:bg-white/10 rounded-lg transition-colors">
                        <X className="w-4 h-4" />
                      </button>
                    </>
                  ) : (
                    <>
                      {/* Create Reminder for this group */}
                      <Link
                        to="/create"
                        state={{ groupId: group.id, groupName: group.name }}
                        className="p-2 text-slate-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-colors"
                        title="Create reminder for this group"
                      >
                        <Bell className="w-4 h-4" />
                      </Link>
                      <button onClick={() => { setEditId(group.id); setEditName(group.name); }}
                        className="p-2 text-slate-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-colors"
                        title="Rename">
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleDelete(group)}
                        className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                        title="Delete group">
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setExpandedId(expandedId === group.id ? null : group.id)}
                        className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                        title="Manage members">
                        {expandedId === group.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Expanded member panel */}
              <AnimatePresence>
                {expandedId === group.id && (
                  <motion.div
                    key="members"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="border-t border-white/10 p-4 space-y-3"
                  >
                    {/* Existing members */}
                    {group.members.length === 0 ? (
                      <p className="text-slate-500 text-sm text-center py-2">No members yet — add some below.</p>
                    ) : (
                      <ul className="space-y-2">
                        {group.members.map(m => (
                          <li key={m.id} className="flex items-center justify-between gap-3 px-3 py-2 bg-white/5 rounded-lg">
                            <div className="flex items-center gap-2 min-w-0">
                              <Phone className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              <span className="text-sm text-white font-medium truncate">{m.name}</span>
                              <span className="text-xs text-slate-400 shrink-0">{m.phone_number}</span>
                            </div>
                            <button
                              onClick={() => handleRemoveMember(group.id, m.contact_id, m.name)}
                              className="p-1 text-slate-500 hover:text-rose-400 transition-colors shrink-0"
                              title="Remove">
                              <UserMinus className="w-3.5 h-3.5" />
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}

                    {/* Add member from contacts */}
                    {availableContacts(group).length > 0 && (
                      <div>
                        {addingMemberId === group.id ? (
                          <div className="space-y-2">
                            <p className="text-xs text-slate-400 font-medium">Select a contact to add:</p>
                            <ul className="space-y-1 max-h-40 overflow-y-auto">
                              {availableContacts(group).map(c => (
                                <li key={c.id}>
                                  <button
                                    onClick={() => handleAddMember(group.id, c.id)}
                                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/5 transition-colors text-left"
                                  >
                                    <UserPlus className="w-3.5 h-3.5 text-primary-400 shrink-0" />
                                    <span className="text-sm text-white">{c.name}</span>
                                    <span className="text-xs text-slate-400 ml-auto">{c.phone_number}</span>
                                  </button>
                                </li>
                              ))}
                            </ul>
                            <button onClick={() => setAddingMemberId(null)} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setAddingMemberId(group.id)}
                            className="flex items-center gap-2 text-sm text-primary-400 hover:text-primary-300 transition-colors"
                          >
                            <UserPlus className="w-4 h-4" />
                            Add member
                          </button>
                        )}
                      </div>
                    )}

                    {contacts.length === 0 && (
                      <p className="text-xs text-slate-500 text-center">
                        No contacts yet. <Link to="/contacts" className="text-primary-400 hover:underline">Add contacts first.</Link>
                      </p>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Groups;
