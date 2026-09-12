import { useEffect } from 'react';
import { CheckCircle2, X } from 'lucide-react';
import { Header } from './components/Header';
import { ComplaintForm } from './components/ComplaintForm';
import { AIAssistantPanel } from './components/AIAssistantPanel';
import { PasteTextModal } from './components/PasteTextModal';
import { ComplaintsList } from './components/ComplaintsList';
import { ComplaintDetailModal } from './components/ComplaintDetailModal';
import { StatsDashboard } from './components/StatsDashboard';
import { useAppDispatch, useAppSelector } from './store/hooks';
import { setToastMessage, setSystemStatus } from './store/slices/uiSlice';
import { useGetHealthQuery } from './store/api/complaintsApi';

export function App() {
  const dispatch = useAppDispatch();
  const { activeTab, toastMessage } = useAppSelector((state) => state.ui);
  const { data: health, isError: healthError } = useGetHealthQuery();

  useEffect(() => {
    if (health) dispatch(setSystemStatus('connected'));
    if (healthError) dispatch(setSystemStatus('error'));
  }, [dispatch, health, healthError]);

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-800 flex flex-col antialiased">
      <Header />
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 animate-bounce-in max-w-md">
          <div className={`p-4 rounded-xl shadow-xl flex items-start space-x-3 text-xs border ${toastMessage.type === 'success' ? 'bg-slate-900 text-white border-slate-700' : 'bg-red-900 text-white border-red-700'}`}>
            {toastMessage.type === 'success' ? <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" /> : <X className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />}
            <div className="flex-1 leading-relaxed">{toastMessage.text}</div>
            <button onClick={() => dispatch(setToastMessage(null))} className="text-slate-400 hover:text-white p-0.5"><X className="w-4 h-4" /></button>
          </div>
        </div>
      )}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === 'log' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-7 xl:col-span-8"><ComplaintForm /></div>
            <div className="lg:col-span-5 xl:col-span-4 sticky top-24"><AIAssistantPanel /></div>
          </div>
        )}
        {activeTab === 'list' && <ComplaintsList />}
        {activeTab === 'analytics' && <StatsDashboard />}
      </main>
      <PasteTextModal />
      <ComplaintDetailModal />
    </div>
  );
}

export default App;
