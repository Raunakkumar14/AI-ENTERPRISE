// src/App.tsx
import AppLayout from './components/layout/AppLayout';
import { AuthProvider } from './auth/AuthContext';

export default function App() {
  return <AuthProvider><AppLayout /></AuthProvider>;
}
