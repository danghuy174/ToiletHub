import React, { useState, useEffect } from 'react';
import axios from 'axios';
import EventCard from './EventCard';
import { Wallet } from 'lucide-react';

const API_URL = '/api';

export default function Dashboard({ token }) {
  const [events, setEvents] = useState([]);
  const [fundBalance, setFundBalance] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [eventsRes, fundRes] = await Promise.all([
        axios.get(`${API_URL}/markets`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/fund`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setEvents(eventsRes.data);
      setFundBalance(fundRes.data.balance);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [token]);

  const handleVote = async (marketId) => {
    try {
      const res = await axios.post(`${API_URL}/vote/${marketId}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Re-fetch all data to ensure vote toggles and changed votes are accurately reflected
      await fetchData();
      
      if (res.data.order_triggered) {
        alert('Threshold reached! Polymarket Buy Order Triggered!');
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Error voting');
    }
  };

  if (loading) {
    return <div className="text-center mt-20 text-xl text-gray-400">Loading events...</div>;
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Shared Fund Top Bar */}
      {fundBalance !== null && (
        <div className="mb-8 p-6 glass-panel rounded-2xl flex items-center justify-between border border-primary/30 shadow-lg shadow-primary/10 bg-gradient-to-r from-primary/10 to-transparent">
          <div>
            <h3 className="text-sm font-semibold text-primary uppercase tracking-wider mb-1">Group Shared Fund</h3>
            <p className="text-gray-400 text-sm">Pool used for automated Polymarket orders</p>
          </div>
          <div className="flex items-center text-3xl font-bold text-white font-mono">
            <Wallet className="w-8 h-8 mr-3 text-primary" />
            ${fundBalance.toFixed(2)} <span className="text-xl text-gray-500 ml-2">USDC</span>
          </div>
        </div>
      )}

      <div className="mb-8">
        <h2 className="text-3xl font-bold mb-2">Live Polymarket Events</h2>
        <p className="text-gray-400">Vote on markets to trigger automated Polymarket execution (Threshold: 3 votes, Cost: 10 USDC).</p>
      </div>
      
      <div className="flex flex-col space-y-6">
        {events.map(event => (
          <EventCard 
            key={event.event_id} 
            event={event} 
            onVote={handleVote} 
          />
        ))}
        {events.length === 0 && (
          <div className="text-center text-gray-500 py-10 border border-dashed border-gray-700 rounded-xl">
            No active events found. Try checking back later.
          </div>
        )}
      </div>
    </div>
  );
}
