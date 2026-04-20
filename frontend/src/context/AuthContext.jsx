import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/axios';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await api.get('/auth/me');
        setUser(response.data);
      } catch {
        // Not authenticated — normal on first load
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, []);

  const login = async (email, password) => {
    await api.post('/auth/login', { email, password });
    // Cookie is set by the server; fetch the user profile to populate state
    const userResponse = await api.get('/auth/me');
    setUser(userResponse.data);
    return userResponse.data;
  };

  const signup = async (username, email, password) => {
    await api.post('/auth/signup', { username, email, password });
    return login(email, password);
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Clear local state regardless of network errors
    }
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
