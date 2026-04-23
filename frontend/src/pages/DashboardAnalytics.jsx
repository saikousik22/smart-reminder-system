import React, { useEffect, useState } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  AreaChart, Area,
} from 'recharts';
import {
  Bell, MessageSquare, RotateCcw, TrendingUp,
  CheckCircle, AlertTriangle, RefreshCw, LayoutTemplate,
  Users, ChevronDown, ChevronUp, Phone, Calendar,
  PhoneCall, PhoneMissed, PhoneOff,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../api/axios';

// ─── colour palette ────────────────────────────────────────────────────────
const COLORS = {
  failed: '#ef4444',
  no_answer: '#f97316',
  busy: '#eab308',
  accent: '#6366f1',
  success: '#22c55e',
  muted: '#64748b',
};

const RETRY_COLORS = ['#6366f1', '#8b5cf6', '#a78bfa'];

// ─── skeleton ──────────────────────────────────────────────────────────────
const Skeleton = ({ className = '' }) => (
  <div className={`animate-pulse rounded-lg bg-white/5 ${className}`} />
);

// ─── stat card ─────────────────────────────────────────────────────────────
const StatCard = ({ icon: Icon, label, value, sub, iconColor = 'text-primary-400' }) => (
  <div className="card p-5 flex items-start gap-4">
    <div className={`p-2.5 rounded-xl bg-white/5 ${iconColor}`}>
      <Icon className="w-5 h-5" />
    </div>
    <div className="min-w-0 flex-1">
      <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">{label}</p>
      <p className="text-2xl font-bold text-white mt-0.5">{value}</p>
      {sub && <div className="mt-1.5">{sub}</div>}
    </div>
  </div>
);

// ─── progress bar ──────────────────────────────────────────────────────────
const SuccessBar = ({ pct }) => {
  const color =
    pct >= 75 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="w-full bg-white/10 rounded-full h-1.5 mt-1">
      <div
        className={`${color} h-1.5 rounded-full transition-all duration-700`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
};

// ─── chart card wrapper ────────────────────────────────────────────────────
const ChartCard = ({ title, children }) => (
  <div className="card p-5">
    <h3 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">
      {title}
    </h3>
    {children}
  </div>
);

// ─── custom tooltip ────────────────────────────────────────────────────────
const DarkTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-sm shadow-xl">
      {label && <p className="text-slate-400 mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color || p.fill || '#fff' }}>
          {p.name ?? p.dataKey}: <span className="font-bold">{p.value}</span>
        </p>
      ))}
    </div>
  );
};

// ─── status config for batch member rows ──────────────────────────────────
const MEMBER_STATUS = {
  answered:     { color: 'text-emerald-400', bg: 'bg-emerald-400/10', icon: CheckCircle,  label: 'Answered' },
  'no-answer':  { color: 'text-orange-400',  bg: 'bg-orange-400/10',  icon: PhoneMissed,  label: 'No Answer' },
  busy:         { color: 'text-orange-400',  bg: 'bg-orange-400/10',  icon: PhoneOff,     label: 'Busy' },
  failed:       { color: 'text-rose-400',    bg: 'bg-rose-400/10',    icon: AlertTriangle,label: 'Failed' },
  calling:      { color: 'text-blue-400',    bg: 'bg-blue-400/10',    icon: PhoneCall,    label: 'Calling' },
  processing:   { color: 'text-blue-400',    bg: 'bg-blue-400/10',    icon: PhoneCall,    label: 'Processing' },
  pending:      { color: 'text-yellow-400',  bg: 'bg-yellow-400/10',  icon: Bell,         label: 'Pending' },
};

// ─── group analytics sub-components ──────────────────────────────────────
const AnswerRateBar = ({ pct }) => {
  const color = pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-rose-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-white/10 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full transition-all duration-700`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs font-semibold" style={{ color: pct >= 75 ? '#22c55e' : pct >= 50 ? '#eab308' : '#ef4444' }}>
        {pct}%
      </span>
    </div>
  );
};

const BatchRow = ({ batch }) => {
  const [open, setOpen] = useState(false);
  const dt = new Date(batch.scheduled_time + 'Z');
  return (
    <div className="border border-white/5 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors text-left"
      >
        <div className="flex items-center gap-3 min-w-0">
          <Calendar className="w-4 h-4 text-slate-500 shrink-0" />
          <div className="min-w-0">
            <p className="text-sm text-white font-medium truncate">{batch.title}</p>
            <p className="text-xs text-slate-500">
              {dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              {' · '}
              {dt.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0 ml-3">
          <span className="text-xs text-slate-400">
            <span className="text-emerald-400 font-semibold">{batch.answered}</span>/{batch.total} answered
          </span>
          {open ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
        </div>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-white/5"
          >
            <ul className="divide-y divide-white/5">
              {batch.members.map((m, i) => {
                const cfg = MEMBER_STATUS[m.status] || MEMBER_STATUS.pending;
                const Icon = cfg.icon;
                return (
                  <li key={i} className="flex items-center justify-between px-4 py-2.5 gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <Phone className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      <span className="text-sm text-white truncate">{m.name}</span>
                      <span className="text-xs text-slate-500 hidden sm:block">{m.phone_number}</span>
                    </div>
                    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium shrink-0 ${cfg.bg} ${cfg.color}`}>
                      <Icon className="w-3 h-3" />
                      {cfg.label}
                    </div>
                  </li>
                );
              })}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const GroupCard = ({ group }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between p-5 hover:bg-white/5 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <div className="bg-indigo-500/10 p-2.5 rounded-xl shrink-0">
            <Users className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <p className="text-white font-semibold">{group.group_name}</p>
            <p className="text-xs text-slate-500">{group.member_count} members · {group.total_batches} batch{group.total_batches !== 1 ? 'es' : ''}</p>
          </div>
        </div>
        <div className="flex items-center gap-4 shrink-0 ml-4">
          <div className="hidden sm:block w-32">
            <p className="text-xs text-slate-500 mb-1">Answer rate</p>
            <AnswerRateBar pct={group.answer_rate} />
          </div>
          <div className="text-right hidden md:block">
            <p className="text-xs text-slate-500">Last used</p>
            <p className="text-xs text-slate-300">{group.last_used ?? '—'}</p>
          </div>
          {open ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
        </div>
      </button>

      {/* Mobile answer rate */}
      <div className="sm:hidden px-5 pb-3">
        <AnswerRateBar pct={group.answer_rate} />
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-white/10 p-4 space-y-2"
          >
            {group.batches.length === 0 ? (
              <p className="text-slate-500 text-sm text-center py-4">No reminders sent to this group yet.</p>
            ) : (
              group.batches.map((batch, i) => <BatchRow key={i} batch={batch} />)
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ─── main component ────────────────────────────────────────────────────────
export default function DashboardAnalytics() {
  const [data, setData] = useState(null);
  const [groupData, setGroupData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const [res, gres] = await Promise.all([
        api.get('/dashboard/analytics'),
        api.get('/dashboard/group-analytics'),
      ]);
      setData(res.data);
      setGroupData(gres.data);
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to load analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAnalytics(); }, []);

  // ── loading skeleton ──
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-8 w-24" />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  // ── error state ──
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 mb-3" />
        <p className="text-slate-300 font-medium mb-4">{error}</p>
        <button onClick={fetchAnalytics} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  // ── derived chart data ──
  const failedPieData = [
    { name: 'Failed', value: data.failed_distribution.failed, color: COLORS.failed },
    { name: 'No Answer', value: data.failed_distribution.no_answer, color: COLORS.no_answer },
    { name: 'Busy', value: data.failed_distribution.busy, color: COLORS.busy },
  ].filter((d) => d.value > 0);

  const retryBarData = Object.entries(data.retry_distribution).map(([k, v]) => ({
    label: `${k} retr${k === '1' ? 'y' : 'ies'}`,
    count: v,
  }));

  const trendData = data.trend_7_days.map((d) => ({
    date: d.date.slice(5), // MM-DD
    count: d.count,
  }));

  return (
    <div className="space-y-6">
      {/* header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Reliability Dashboard</h1>
          <p className="text-slate-400 text-sm mt-0.5">Insights into call performance and reminder trends</p>
        </div>
        <button
          onClick={fetchAnalytics}
          className="btn-secondary flex items-center gap-2 text-sm py-1.5 px-4"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* tab switcher */}
      <div className="flex p-1 bg-white/5 rounded-xl w-fit">
        {[
          { key: 'overview', label: 'Overview', icon: TrendingUp },
          { key: 'groups',   label: 'Groups',   icon: Users },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === key ? 'bg-primary-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && <>
      {/* ── row 1: stat cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          icon={Bell}
          label="Total Reminders"
          value={data.total_reminders}
          iconColor="text-primary-400"
        />
        <StatCard
          icon={CheckCircle}
          label="Success Rate"
          value={`${data.success_rate}%`}
          iconColor={
            data.success_rate >= 75
              ? 'text-green-400'
              : data.success_rate >= 50
              ? 'text-yellow-400'
              : 'text-red-400'
          }
          sub={<SuccessBar pct={data.success_rate} />}
        />
        <StatCard
          icon={MessageSquare}
          label="SMS Fallbacks"
          value={data.sms_fallback_count}
          iconColor="text-blue-400"
        />
        <StatCard
          icon={RotateCcw}
          label="Total Retries"
          value={data.total_retries}
          iconColor="text-purple-400"
        />
        <StatCard
          icon={LayoutTemplate}
          label="Saved Templates"
          value={data.template_count}
          iconColor="text-teal-400"
        />
      </div>

      {/* ── row 2: donut + bar ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* donut – failed distribution */}
        <ChartCard title="Failed Calls Distribution">
          {failedPieData.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-16">No failed calls — great job!</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={failedPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {failedPieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<DarkTooltip />} />
                <Legend
                  formatter={(value) => (
                    <span className="text-slate-300 text-xs">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
          <div className="flex justify-center gap-6 mt-2">
            {[
              { label: 'Failed', val: data.failed_distribution.failed, color: COLORS.failed },
              { label: 'No Answer', val: data.failed_distribution.no_answer, color: COLORS.no_answer },
              { label: 'Busy', val: data.failed_distribution.busy, color: COLORS.busy },
            ].map((item) => (
              <div key={item.label} className="text-center">
                <p className="text-lg font-bold" style={{ color: item.color }}>{item.val}</p>
                <p className="text-xs text-slate-500">{item.label}</p>
              </div>
            ))}
          </div>
        </ChartCard>

        {/* bar – retry usage */}
        <ChartCard title="Retry Configuration Usage">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={retryBarData} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="label"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<DarkTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
              <Bar dataKey="count" name="Reminders" radius={[4, 4, 0, 0]}>
                {retryBarData.map((_, i) => (
                  <Cell key={i} fill={RETRY_COLORS[i % RETRY_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* ── row 3: 7-day trend ── */}
      <ChartCard title="7-Day Reminder Trend">
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={trendData} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
            <defs>
              <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<DarkTooltip />} />
            <Area
              type="monotone"
              dataKey="count"
              name="Reminders"
              stroke="#6366f1"
              strokeWidth={2}
              fill="url(#trendGrad)"
              dot={{ fill: '#6366f1', strokeWidth: 0, r: 3 }}
              activeDot={{ r: 5, fill: '#818cf8' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>
      </>}

      {/* ── Groups tab ── */}
      {activeTab === 'groups' && (
        <div className="space-y-6">
          {!groupData || groupData.groups.length === 0 ? (
            <div className="card p-12 text-center">
              <Users className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400 font-medium">No group reminders sent yet.</p>
              <p className="text-slate-500 text-sm mt-1">
                Create a group and send a reminder to see analytics here.
              </p>
            </div>
          ) : (
            <>
              {/* ── Group summary cards ── */}
              <div>
                <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                  Group Performance
                </h2>
                <div className="space-y-3">
                  {groupData.groups.map(g => <GroupCard key={g.group_id} group={g} />)}
                </div>
              </div>

              {/* ── Member reliability table ── */}
              {groupData.member_reliability.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                    Member Reliability
                  </h2>
                  <div className="card overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-white/10">
                          <th className="text-left px-5 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider">Contact</th>
                          <th className="text-right px-5 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider hidden sm:table-cell">Calls</th>
                          <th className="text-right px-5 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider hidden sm:table-cell">Answered</th>
                          <th className="px-5 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider">Answer Rate</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {groupData.member_reliability.map((m, i) => (
                          <tr key={i} className="hover:bg-white/5 transition-colors">
                            <td className="px-5 py-3">
                              <p className="text-white font-medium">{m.name}</p>
                              <p className="text-xs text-slate-500">{m.phone_number}</p>
                            </td>
                            <td className="px-5 py-3 text-right text-slate-300 hidden sm:table-cell">{m.total_calls}</td>
                            <td className="px-5 py-3 text-right text-emerald-400 font-medium hidden sm:table-cell">{m.answered}</td>
                            <td className="px-5 py-3">
                              <AnswerRateBar pct={m.answer_rate} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
