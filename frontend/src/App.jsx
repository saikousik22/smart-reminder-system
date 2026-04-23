import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import DashboardAnalytics from './pages/DashboardAnalytics';
import CreateReminder from './pages/CreateReminder';
import CalendarView from './components/CalendarView';
import Contacts from './pages/Contacts';
import Groups from './pages/Groups';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-[60vh] text-center px-4">
          <h2 className="text-2xl font-bold text-white mb-2">Something went wrong</h2>
          <p className="text-slate-400 mb-6">Please refresh the page to try again.</p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="btn-secondary"
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <AuthProvider>
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-grow container mx-auto px-4 py-8">
          <ErrorBoundary>
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />

              {/* Protected Routes */}
              <Route element={<ProtectedRoute />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/analytics" element={<DashboardAnalytics />} />
                <Route path="/calendar" element={<CalendarView />} />
                <Route path="/create" element={<CreateReminder />} />
                <Route path="/edit/:id" element={<CreateReminder />} />
                <Route path="/contacts" element={<Contacts />} />
                <Route path="/groups" element={<Groups />} />
              </Route>

              {/* Default Redirects */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
    </AuthProvider>
  );
}

export default App;
