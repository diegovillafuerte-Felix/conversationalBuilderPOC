import { useEffect, useRef } from 'react';
import { useChatStore } from '../../store/chatStore';
import Message from './Message';
import TypingIndicator from './TypingIndicator';

export default function MessageList() {
  const messages = useChatStore((state) => state.messages);
  const isLoading = useChatStore((state) => state.isLoading);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-messages">
      {messages.map((message) => (
        <Message key={message.id} content={message.content} type={message.type} />
      ))}
      {isLoading && <TypingIndicator />}
      <div ref={messagesEndRef} />
    </div>
  );
}
