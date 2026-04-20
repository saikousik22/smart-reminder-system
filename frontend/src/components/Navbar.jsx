import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Bell, LogOut, User as UserIcon, Plus } from 'lucide-react';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav className="border-b border-white/10 bg-black/20 backdrop-blur-md sticky top-0 z-50">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group">
          <div className="bg-primary-600 p-2 rounded-lg group-hover:rotate-12 transition-transform">
            <Bell className="text-white w-5 h-5" />
          </div>
          <span className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            SmartReminder
          </span>
        </Link>

        {user ? (
          <div className="flex items-center gap-4">
            <Link 
              to="/create" 
              className="hidden sm:flex items-center gap-2 bg-primary-600/10 hover:bg-primary-600/20 text-primary-400 px-4 py-2 rounded-full border border-primary-500/20 transition-all font-medium"
            >
              <Plus className="w-4 h-4" />
              New Reminder
            </Link>
            
            <div className="h-8 w-px bg-white/10 mx-2 hidden sm:block"></div>
            
            <div className="flex items-center gap-3">
              <div className="flex flex-col items-end hidden md:flex">
                <span className="text-sm font-medium text-slate-200">{user.username}</span>
                <span className="text-xs text-slate-500">{user.email}</span>
              </div>
              <button 
                onClick={handleLogout}
                className="p-2 hover:bg-white/10 rounded-full text-slate-400 hover:text-white transition-colors"
                title="Logout"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-4">
            <Link to="/login" className="text-slate-400 hover:text-white transition-colors font-medium">
              Login
            </Link>
            <Link to="/signup" className="btn-primary py-1.5 px-5">
              Get Started
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
