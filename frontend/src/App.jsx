import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import OverviewPage from './pages/OverviewPage';
import UploadPage from './pages/UploadPage';
import LeadsPage from './pages/LeadsPage';
import ReviewQueuePage from './pages/ReviewQueuePage';
import DuplicateManagementPage from './pages/DuplicateManagementPage';
import SectorAdminPage from './pages/SectorAdminPage';
import BatchHistoryPage from './pages/BatchHistoryPage';
import { getReviewQueue } from './services/api';

export default function App() {
  const [pendingReviewCount, setPendingReviewCount] = useState(0);

  useEffect(() => {
    fetchReviewCount();
    const interval = setInterval(fetchReviewCount, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchReviewCount = async () => {
    try {
      const data = await getReviewQueue({ page: 1, page_size: 1 });
      setPendingReviewCount(data.total || 0);
    } catch (err) {
      // Ignore initial network errors before backend starts
    }
  };

  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100">
        <Navbar />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar pendingReviewCount={pendingReviewCount} />
          <main className="flex-1 overflow-y-auto bg-slate-950">
            <Routes>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/leads" element={<LeadsPage />} />
              <Route
                path="/review"
                element={<ReviewQueuePage onReviewProcessed={fetchReviewCount} />}
              />
              <Route path="/duplicates" element={<DuplicateManagementPage />} />
              <Route path="/sectors" element={<SectorAdminPage />} />
              <Route path="/batches" element={<BatchHistoryPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}
