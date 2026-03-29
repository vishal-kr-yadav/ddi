import { useEffect } from 'react'
import AuthScreen from './AuthScreen'

export default function AuthModal({ onAuthenticated, onClose }) {
  // Lock body scroll while modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Modal */}
      <div className="relative z-10 w-full max-w-md">
        <button
          onClick={onClose}
          className="absolute -top-3 -right-3 w-8 h-8 bg-gray-800 border border-gray-700
            rounded-full flex items-center justify-center text-gray-400
            hover:text-white hover:bg-gray-700 transition z-20 text-sm"
        >
          ×
        </button>
        <AuthScreen onAuthenticated={onAuthenticated} inline />
      </div>
    </div>
  )
}
