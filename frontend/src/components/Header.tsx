import React from 'react';
import { BarChart3, FileText, PlusCircle, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  activeTab: 'log' | 'list' | 'analytics';
  setActiveTab: (tab: 'log' | 'list' | 'analytics') => void;
  systemStatus: 'connected' | 'checking' | 'error';
  openComplaintsCount?: number;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  systemStatus,
  openComplaintsCount,
}) => {
  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200/80 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Title */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-linear-to-br from-blue-600 to-indigo-700 flex items-center justify-center shadow-md shadow-blue-500/20 text-white">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-slate-900 text-lg tracking-tight">
                  PharmaQMS
                </span>
                <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                  cGMP 21 CFR
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                Customer Complaint & Triage Intelligence
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center space-x-1 bg-slate-100/90 p-1 rounded-xl border border-slate-200/60">
            <button
              onClick={() => setActiveTab('log')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'log'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
              }`}
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Log Complaint</span>
            </button>

            <button
              onClick={() => setActiveTab('list')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'list'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Complaints Directory</span>
              {openComplaintsCount !== undefined && openComplaintsCount > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                  {openComplaintsCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('analytics')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'analytics'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Analytics & KPI</span>
            </button>
          </nav>

          {/* System Status Indicator */}
          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200 text-xs">
              <span
                className={`w-2 h-2 rounded-full ${
                  systemStatus === 'connected'
                    ? 'bg-emerald-500 animate-pulse'
                    : systemStatus === 'checking'
                    ? 'bg-amber-400 animate-ping'
                    : 'bg-red-500'
                }`}
              />
              <span className="text-slate-600 font-medium text-[11px]">
                {systemStatus === 'connected'
                  ? 'Engine Online'
                  : systemStatus === 'checking'
                  ? 'Connecting...'
                  : 'Engine Offline'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
