import React, { useState, useEffect } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  Clock,
  Layers,
  PieChart,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../api/client';
import type { ComplaintStatsResponse } from '../api/types';

export const StatsDashboard: React.FC = () => {
  const [stats, setStats] = useState<ComplaintStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await api.getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-slate-500">
        <div className="inline-flex items-center space-x-2">
          <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />
          <span>Computing Quality Assurance Metrics...</span>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-400">
        Failed to load analytics.
      </div>
    );
  }

  const criticalCount = stats.bySeverity?.Critical || 0;
  const majorCount = stats.bySeverity?.Major || 0;
  const minorCount = stats.bySeverity?.Minor || 0;

  const openCount = stats.byStatus?.Open || 0;
  const inProgressCount = stats.byStatus?.InProgress || 0;
  const closedCount = stats.byStatus?.Closed || 0;

  return (
    <div className="space-y-6">
      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Complaints */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
              Total Complaints
            </span>
            <span className="text-2xl font-black text-slate-900">{stats.total}</span>
          </div>
        </div>

        {/* Critical Severity */}
        <div className="bg-white p-5 rounded-2xl border border-red-200/80 shadow-xs flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center shrink-0">
            <AlertOctagon className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-red-500 uppercase tracking-wider block">
              Critical (Class I)
            </span>
            <span className="text-2xl font-black text-red-700">{criticalCount}</span>
          </div>
        </div>

        {/* Major Severity */}
        <div className="bg-white p-5 rounded-2xl border border-amber-200/80 shadow-xs flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-amber-600 uppercase tracking-wider block">
              Major Defects
            </span>
            <span className="text-2xl font-black text-amber-700">{majorCount}</span>
          </div>
        </div>

        {/* Open Investigations */}
        <div className="bg-white p-5 rounded-2xl border border-emerald-200/80 shadow-xs flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-emerald-600 uppercase tracking-wider block">
              Open Investigations
            </span>
            <span className="text-2xl font-black text-emerald-700">{openCount + inProgressCount}</span>
          </div>
        </div>
      </div>

      {/* Breakdown Grids */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Severity Distribution */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-blue-600" />
            <span>Severity Distribution & Regulatory Risk</span>
          </h3>

          <div className="space-y-3 pt-2 text-xs">
            <div>
              <div className="flex justify-between font-semibold text-slate-700 mb-1">
                <span>Critical (Safety / Recall Hazard)</span>
                <span className="text-red-600 font-bold">{criticalCount}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-red-500 rounded-full"
                  style={{ width: `${stats.total ? (criticalCount / stats.total) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between font-semibold text-slate-700 mb-1">
                <span>Major (Quality / Physical Defect)</span>
                <span className="text-amber-600 font-bold">{majorCount}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-amber-500 rounded-full"
                  style={{ width: `${stats.total ? (majorCount / stats.total) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between font-semibold text-slate-700 mb-1">
                <span>Minor (Cosmetic / Packaging)</span>
                <span className="text-blue-600 font-bold">{minorCount}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full"
                  style={{ width: `${stats.total ? (minorCount / stats.total) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-slate-500 text-[11px]">
              <span>Closed & Resolved Records:</span>
              <span className="font-bold text-slate-700 font-mono">{closedCount}</span>
            </div>
          </div>
        </div>

        {/* Open Defects by Complaint Type */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
            <PieChart className="w-4 h-4 text-blue-600" />
            <span>Open Defects by Classification Category</span>
          </h3>

          <div className="space-y-2.5 pt-2 text-xs">
            {Object.entries(stats.openByType || {}).map(([type, count]) => (
              <div
                key={type}
                className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100"
              >
                <span className="font-semibold text-slate-700">{type}</span>
                <span className="px-2 py-0.5 rounded-md font-bold bg-blue-100 text-blue-800 text-[11px]">
                  {count} open
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
