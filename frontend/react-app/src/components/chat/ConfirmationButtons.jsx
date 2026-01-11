import { useState, useEffect } from 'react';
import { useChatStore } from '../../store/chatStore';

export default function ConfirmationButtons() {
  const pendingConfirmation = useChatStore((state) => state.pendingConfirmation);
  const confirmationExpiresAt = useChatStore((state) => state.confirmationExpiresAt);
  const sendConfirmation = useChatStore((state) => state.sendConfirmation);
  const clearConfirmation = useChatStore((state) => state.clearConfirmation);
  const addMessage = useChatStore((state) => state.addMessage);
  const isLoading = useChatStore((state) => state.isLoading);

  const [timeRemaining, setTimeRemaining] = useState(null);
  const [isDisabled, setIsDisabled] = useState(false);

  useEffect(() => {
    if (!confirmationExpiresAt) {
      setTimeRemaining(null);
      setIsDisabled(false);
      return;
    }

    const updateTimer = () => {
      const remaining = Math.max(0, new Date(confirmationExpiresAt) - Date.now());
      setTimeRemaining(remaining);

      if (remaining === 0) {
        setIsDisabled(true);
        clearConfirmation();
        addMessage('La confirmación ha expirado. Por favor intenta de nuevo.', 'system');
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [confirmationExpiresAt, clearConfirmation, addMessage]);

  if (!pendingConfirmation) return null;

  const formatTime = (ms) => {
    const seconds = Math.floor(ms / 1000);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleConfirm = async (confirmed) => {
    setIsDisabled(true);
    await sendConfirmation(confirmed);
  };

  return (
    <div className="confirmation-buttons">
      {timeRemaining !== null && (
        <span className="countdown">Expira en {formatTime(timeRemaining)}</span>
      )}
      <button
        className="confirm-btn yes"
        onClick={() => handleConfirm(true)}
        disabled={isDisabled || isLoading}
      >
        Confirmar
      </button>
      <button
        className="confirm-btn no"
        onClick={() => handleConfirm(false)}
        disabled={isDisabled || isLoading}
      >
        Cancelar
      </button>
    </div>
  );
}
