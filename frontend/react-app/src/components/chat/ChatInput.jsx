import { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../../store/chatStore';

export default function ChatInput() {
  const [text, setText] = useState('');
  const inputRef = useRef(null);
  const sendMessage = useChatStore((state) => state.sendMessage);
  const isLoading = useChatStore((state) => state.isLoading);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    setText('');
    await sendMessage(trimmed);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className="chat-input-container" onSubmit={handleSubmit}>
      <input
        ref={inputRef}
        type="text"
        className="chat-input"
        placeholder="Escribe tu mensaje..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
      />
      <button type="submit" className="send-button" disabled={isLoading || !text.trim()}>
        ➤
      </button>
    </form>
  );
}
