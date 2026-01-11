import { useState } from 'react';
import ChatPage from './pages/ChatPage';
import AdminPage from './pages/AdminPage';
import './styles/globals.css';

function App() {
  const [currentPage, setCurrentPage] = useState('chat');

  // Simple URL-based routing
  const path = window.location.pathname;
  const page = path === '/admin' ? 'admin' : 'chat';

  if (page === 'admin') {
    return <AdminPage />;
  }

  return <ChatPage />;
}

export default App;
