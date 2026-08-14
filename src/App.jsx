import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { AuthProvider } from '@/auth/AuthContext';
import ProtectedRoute from '@/auth/ProtectedRoute';

import AppLayout from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import NewAnalysis from './pages/NewAnalysis';
import Results from './pages/Results';
import History from './pages/History';
import Login from './pages/Login';

function App() {
  return (
    <QueryClientProvider client={queryClientInstance}>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/new-analysis" element={<NewAnalysis />} />
                <Route path="/results/:id" element={<Results />} />
                <Route path="/history" element={<History />} />
              </Route>
            </Route>
            <Route path="*" element={<PageNotFound />} />
          </Routes>
        </Router>
        <Toaster />
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
