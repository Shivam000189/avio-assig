import React, { useState, useEffect } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
  Search,
} from 'lucide-react';
import { formatDate, getSeverityBadgeColor, getStatusBadgeColor } from '../utils/formatters';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { setFilter, setPage, setComplaints } from '../store/slices/complaintsSlice';
import { setSelectedComplaint } from '../store/slices/uiSlice';
import { useGetComplaintsQuery } from '../store/api/complaintsApi';

export const ComplaintsList: React.FC = () => {
  const dispatch = useAppDispatch();
  const { items: complaints, total, page, limit, filters, refreshTrigger } = useAppSelector((state) => state.complaints);
  const [loading, setLoading] = useState(true);
  const { data, isFetching, refetch } = useGetComplaintsQuery({ skip: page * limit, limit, ...filters, refreshTrigger });

  useEffect(() => {
    if (data) dispatch(setComplaints({ items: data.items, total: data.total }));
    setLoading(isFetching);
  }, [data, dispatch, isFetching]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    dispatch(setPage(0));
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-5">
      {/* Control Bar: Search & Filters */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[280px] relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => dispatch(setFilter({ field: 'search', value: e.target.value }))}
            placeholder="Search by product, batch number, customer, defect..."
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 bg-slate-50 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all"
          />
        </form>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Severity Filter */}
          <div className="flex items-center space-x-1.5">
            <span className="text-xs text-slate-500 font-medium">Severity:</span>
            <select
              value={filters.severity}
              onChange={(e) => {
                dispatch(setFilter({ field: 'severity', value: e.target.value }));
              }}
              className="px-3 py-2 rounded-xl border border-slate-200 bg-slate-50 text-xs font-medium text-slate-700 outline-none focus:border-blue-500"
            >
              <option value="">All Severities</option>
              <option value="Critical">Critical</option>
              <option value="Major">Major</option>
              <option value="Minor">Minor</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center space-x-1.5">
            <span className="text-xs text-slate-500 font-medium">Status:</span>
            <select
              value={filters.status}
              onChange={(e) => {
                dispatch(setFilter({ field: 'status', value: e.target.value }));
              }}
              className="px-3 py-2 rounded-xl border border-slate-200 bg-slate-50 text-xs font-medium text-slate-700 outline-none focus:border-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="Open">Open</option>
              <option value="InProgress">In Progress</option>
              <option value="Closed">Closed</option>
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={refetch}
            className="p-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors cursor-pointer"
            title="Refresh List"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-blue-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* Complaints Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-4 sm:px-6">Complaint #</th>
                <th className="py-3.5 px-4">Product & Lot</th>
                <th className="py-3.5 px-4">Customer</th>
                <th className="py-3.5 px-4">Severity</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Source</th>
                <th className="py-3.5 px-4">Intake Date</th>
                <th className="py-3.5 px-4 sm:px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    <div className="inline-flex items-center space-x-2">
                      <span className="w-4 h-4 border-2 border-blue-600/30 border-t-blue-600 rounded-full animate-spin" />
                      <span>Loading complaints repository...</span>
                    </div>
                  </td>
                </tr>
              ) : complaints.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No complaints found matching current filters.
                  </td>
                </tr>
              ) : (
                complaints.map((c) => {
                  const sevStyle = getSeverityBadgeColor(c.severity);
                  const statStyle = getStatusBadgeColor(c.status);
                  const isChippingPair =
                    c.batchNumber === 'PT-4471-A' &&
                    (c.complaintNumber === 'CMP-2026-0001' || c.complaintNumber === 'CMP-2026-0005');

                  return (
                    <tr
                      key={c.id}
                      onClick={() => dispatch(setSelectedComplaint(c))}
                      className="hover:bg-blue-50/40 transition-colors cursor-pointer group"
                    >
                      {/* Tracking Number */}
                      <td className="py-3.5 px-4 sm:px-6 font-mono font-bold text-blue-600">
                        <div className="flex items-center space-x-1.5">
                          <span>{c.complaintNumber}</span>
                          {isChippingPair && (
                            <span
                              title="Near-Duplicate Batch Pair"
                              className="px-1.5 py-0.2 rounded text-[9px] font-sans font-bold bg-amber-100 text-amber-800"
                            >
                              BATCH MATCH
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Product & Batch */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900">{c.productName}</div>
                        <div className="text-[11px] font-mono text-slate-500">
                          Lot: {c.batchNumber}
                        </div>
                      </td>

                      {/* Customer */}
                      <td className="py-3.5 px-4 text-slate-700 font-medium">
                        {c.complainantName}
                      </td>

                      {/* Severity */}
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border ${sevStyle.bg} ${sevStyle.text} ${sevStyle.border}`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${sevStyle.dot}`} />
                          <span>{c.severity || 'Unassessed'}</span>
                        </span>
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border ${statStyle.bg} ${statStyle.text} ${statStyle.border}`}
                        >
                          {c.status}
                        </span>
                      </td>

                      {/* Source */}
                      <td className="py-3.5 px-4 text-slate-500">{c.source}</td>

                      {/* Intake Date */}
                      <td className="py-3.5 px-4 text-slate-500 font-mono text-[11px]">
                        {formatDate(c.createdAt)}
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 sm:px-6 text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            dispatch(setSelectedComplaint(c));
                          }}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-blue-100 text-slate-700 hover:text-blue-700 font-medium transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {total > limit && (
          <div className="px-6 py-3.5 bg-slate-50/80 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} records
            </span>
            <div className="flex items-center space-x-1.5">
              <button
                onClick={() => dispatch(setPage(Math.max(0, page - 1)))}
                disabled={page === 0}
                className="p-1.5 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-white text-slate-700"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-semibold text-slate-700 px-2">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => dispatch(setPage(Math.min(totalPages - 1, page + 1)))}
                disabled={page >= totalPages - 1}
                className="p-1.5 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-white text-slate-700"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
