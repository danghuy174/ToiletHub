import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import Login from './components/Login';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  const handleLogin = (newToken) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  };
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background elements for modern look */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-accent/20 rounded-full blur-[120px] pointer-events-none" />
      
      <header className="relative z-10 glass-panel border-b border-white/5 px-6 py-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
          World Cup Prediction
        </h1>
        {token && (
          <button 
            onClick={handleLogout}
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            Logout
          </button>
        )}
      </header>

      <main className="relative z-10 container mx-auto px-4 py-8">
        {!token ? (
          <Login onLogin={handleLogin} />
        ) : (
          <Dashboard token={token} />
        )}
      </main>
    </div>
  );
}

export default App;
