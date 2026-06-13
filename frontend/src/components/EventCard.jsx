import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Clock, Info } from 'lucide-react';

export default function EventCard({ event, onVote }) {
  const THRESHOLD = 6;

  // Group markets by type
  const groupedMarkets = event.markets.reduce((acc, market) => {
    const type = market.market_type || 'Moneyline';
    if (!acc[type]) acc[type] = [];
    acc[type].push(market);
    return acc;
  }, {});

  // For some reason moneyline options are occasionally duplicated in DB, so let's deduplicate them by option_name
  const deduplicate = (markets) => {
    const seen = new Set();
    return markets.filter(m => {
      if (seen.has(m.option_name)) return false;
      seen.add(m.option_name);
      return true;
    });
  };

  const moneylineRaw = deduplicate(groupedMarkets['Moneyline'] || []);
  const spreads = groupedMarkets['Spreads'] || [];
  const rawTotals = groupedMarkets['Totals'] || [];

  // Sort Moneyline as: Home – Draw – Away
  // home_team_code comes from backend (e.g. "USA", "CAN")
  const homeCode = (moneylineRaw[0]?.home_team_code || '').toUpperCase();
  const sortedMoneyline = [...moneylineRaw].sort((a, b) => {
    const aName = a.option_name.toUpperCase();
    const bName = b.option_name.toUpperCase();
    const aIsHome = aName === homeCode;
    const bIsHome = bName === homeCode;
    const aIsDraw = aName === 'DRAW';
    const bIsDraw = bName === 'DRAW';
    if (aIsHome) return -1;
    if (bIsHome) return 1;
    if (aIsDraw) return -1;
    if (bIsDraw) return 1;
    return 0;
  });
  // Tag each outcome with a role for consistent coloring
  const moneyline = sortedMoneyline.map(m => {
    const name = m.option_name.toUpperCase();
    let role = 'away';
    if (name === homeCode) role = 'home';
    else if (name === 'DRAW') role = 'draw';
    return { ...m, _role: role };
  });

  // 1. Spreads Logic: Group them into pairs because they are inserted sequentially (Yes side, then No side)
  const spreadPairs = [];
  for (let i = 0; i < spreads.length; i += 2) {
    if (spreads[i] && spreads[i+1]) {
      spreadPairs.push([spreads[i], spreads[i+1]]);
    }
  }
  const defaultSpreadPairIndex = Math.max(0, spreadPairs.findIndex(pair => pair[0].option_name.includes("1.5")));
  const [selectedSpreadPairIdx, setSelectedSpreadPairIdx] = useState(defaultSpreadPairIndex);
  const currentSpreads = spreadPairs[selectedSpreadPairIdx] || [];

  // 2. Totals Logic: Filter out Team Totals (e.g., "CAN Over 2.5"), keep only Match Totals ("Over 2.5")
  const matchTotals = deduplicate(rawTotals.filter(m => m.option_name.startsWith("Over ") || m.option_name.startsWith("Under ")));
  const getTotalsLine = (optionName) => {
    const match = optionName.match(/(\d+(\.\d+)?)/);
    return match ? match[1] : null;
  };
  const totalLines = [...new Set(matchTotals.map(m => getTotalsLine(m.option_name)).filter(Boolean))].sort((a, b) => parseFloat(a) - parseFloat(b));
  const [selectedTotalLine, setSelectedTotalLine] = useState(totalLines.includes("2.5") ? "2.5" : totalLines[0] || null);
  const currentTotals = matchTotals.filter(m => getTotalsLine(m.option_name) === selectedTotalLine);

  const formatMarketButton = (market, index, type) => {
    const progress = Math.min((market.votes / THRESHOLD) * 100, 100);
    const isCompleted = market.votes >= THRESHOLD || market.order_placed;

    // Define background colors based on type and role
    let bgClass = "bg-[#2A2B31] hover:bg-[#34363d]";
    if (type === 'Moneyline') {
      const roleColors = {
        home:  "bg-[#1e3a5f] hover:bg-[#254d7a] border-[#2d6cb5]/30",  // Blue
        draw:  "bg-[#2f3340] hover:bg-[#3a3f50] border-[#555a6e]/30",  // Neutral
        away:  "bg-[#5c1a1a] hover:bg-[#7a2525] border-[#c0392b]/30",  // Red
      };
      bgClass = roleColors[market._role] || roleColors.draw;
    } else if (type === 'Spreads') {
      bgClass = index === 0 ? "bg-[#b2322d] hover:bg-[#d03d36] border-[#e04040]/20" : "bg-[#2546bd] hover:bg-[#2c53e3] border-[#4d7aff]/20";
    } else if (type === 'Totals') {
      bgClass = index === 0 ? "bg-[#1a5c3a] hover:bg-[#1f7048] border-[#2ecc71]/20" : "bg-[#5c3a1a] hover:bg-[#704820] border-[#e67e22]/20";
    }

    // Extract the label to display inside the button
    let displayLabel = market.option_name;
    if (type === 'Spreads') {
      displayLabel = displayLabel.replace("(", "").replace(")", ""); // "CAN -1.5"
    } else if (type === 'Totals') {
      displayLabel = displayLabel.replace("Over", "O").replace("Under", "U"); // "O 2.5"
    }

    // Odds color based on type
    let oddsColor = "text-[#00e4d0]"; // default bright cyan
    if (type === 'Spreads') oddsColor = "text-[#ffd166]"; // warm gold
    if (type === 'Totals') oddsColor = "text-[#a8e6cf]"; // soft mint

    return (
      <button 
        key={market.id}
        onClick={() => onVote(market.id)}
        disabled={isCompleted}
        className={`relative overflow-hidden flex items-center justify-between px-4 py-3 rounded-xl transition-all cursor-pointer border min-w-[120px] md:min-w-[140px] flex-1 ${bgClass} ${isCompleted ? 'opacity-50 cursor-not-allowed' : 'active:scale-[0.98]'}`}
      >
        {/* Progress Fill inside the button */}
        <div 
          className="absolute left-0 top-0 bottom-0 bg-white/15 transition-all duration-500 ease-out z-0 rounded-xl"
          style={{ width: `${progress}%` }}
        />
        
        {/* Content */}
        <div className="relative z-10 flex w-full items-center justify-between">
          <div className="flex flex-col items-start">
            <span className="font-bold text-sm text-white truncate">{displayLabel}</span>
            {/* Tiny vote indicator */}
            <span className="text-[10px] text-[#4ecdc4] font-semibold tracking-wider">[{market.votes}/{THRESHOLD}]</span>
          </div>
          <span className={`font-mono font-bold text-base ml-2 shrink-0 ${oddsColor}`}>
            {Math.round(market.odds)}¢
          </span>
        </div>
      </button>
    );
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-8"
    >
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-white">{event.event_title}</h2>
      </div>

      <div className="flex flex-col gap-4">
        
        {/* Moneyline */}
        {moneyline.length > 0 && (
          <div className="border border-white/5 rounded-2xl bg-[#1A1B20] p-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex flex-col">
                <div className="flex items-center text-white font-bold text-lg">
                  Moneyline <span className="ml-2 text-xs text-gray-500 font-medium uppercase tracking-wider flex items-center">Reg Time <Info className="w-3 h-3 ml-1"/></span>
                </div>
                <span className="text-gray-500 text-sm">$4.6M Vol.</span>
              </div>
              <div className="flex flex-row gap-2 w-full md:w-auto overflow-x-auto pb-2 md:pb-0">
                {moneyline.map((market, idx) => formatMarketButton(market, idx, 'Moneyline'))}
              </div>
            </div>
          </div>
        )}

        {/* Spreads */}
        {spreadPairs.length > 0 && (
          <div className="border border-white/5 rounded-2xl bg-[#1A1B20] p-4">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex flex-col">
                  <div className="flex items-center text-white font-bold text-lg">
                    Spreads <span className="ml-2 text-xs text-gray-500 font-medium uppercase tracking-wider flex items-center">Reg Time <Info className="w-3 h-3 ml-1"/></span>
                  </div>
                  <span className="text-gray-500 text-sm">$88.0K Vol.</span>
                </div>
                <div className="flex flex-row gap-2 w-full md:w-auto overflow-x-auto pb-2 md:pb-0">
                  {currentSpreads.map((market, idx) => formatMarketButton(market, idx, 'Spreads'))}
                </div>
              </div>
              
              {/* Spreads Selector */}
              <div className="flex items-center justify-center border-t border-white/5 pt-4 text-gray-400 font-mono text-sm gap-6 overflow-x-auto select-none">
                <span className="cursor-pointer hover:text-white">&lt;</span>
                {spreadPairs.map((pair, idx) => {
                  const label = pair[0].option_name.replace("(", "").replace(")", ""); // e.g. "CAN -1.5"
                  return (
                  <div 
                    key={idx} 
                    onClick={() => setSelectedSpreadPairIdx(idx)}
                    className={`cursor-pointer flex flex-col items-center relative transition-colors whitespace-nowrap ${selectedSpreadPairIdx === idx ? 'text-white font-bold' : 'hover:text-gray-300'}`}
                  >
                    {selectedSpreadPairIdx === idx && (
                      <div className="absolute -top-3 text-[#2546bd] text-[10px]">▼</div>
                    )}
                    {label}
                  </div>
                )})}
                <span className="cursor-pointer hover:text-white">&gt;</span>
              </div>
            </div>
          </div>
        )}

        {/* Totals */}
        {matchTotals.length > 0 && (
          <div className="border border-white/5 rounded-2xl bg-[#1A1B20] p-4">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex flex-col">
                  <div className="flex items-center text-white font-bold text-lg">
                    Totals <span className="ml-2 text-xs text-gray-500 font-medium uppercase tracking-wider flex items-center">Reg Time <Info className="w-3 h-3 ml-1"/></span>
                  </div>
                  <span className="text-gray-500 text-sm">$434K Vol.</span>
                </div>
                <div className="flex flex-row gap-2 w-full md:w-auto overflow-x-auto pb-2 md:pb-0">
                  {currentTotals.map((market, idx) => formatMarketButton(market, idx, 'Totals'))}
                </div>
              </div>
              
              {/* Totals Selector */}
              {totalLines.length > 0 && (
                <div className="flex items-center justify-center border-t border-white/5 pt-4 text-gray-400 font-mono text-sm gap-6 overflow-x-auto select-none">
                  <span className="cursor-pointer hover:text-white">&lt;</span>
                  {totalLines.map(line => (
                    <div 
                      key={line} 
                      onClick={() => setSelectedTotalLine(line)}
                      className={`cursor-pointer flex flex-col items-center relative transition-colors ${selectedTotalLine === line ? 'text-white font-bold' : 'hover:text-gray-300'}`}
                    >
                      {selectedTotalLine === line && (
                        <div className="absolute -top-3 text-[#2546bd] text-[10px]">▼</div>
                      )}
                      {line}
                    </div>
                  ))}
                  <span className="cursor-pointer hover:text-white">&gt;</span>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </motion.div>
  );
}
