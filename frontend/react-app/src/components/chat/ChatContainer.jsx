import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ConfirmationButtons from './ConfirmationButtons';
import ChatInput from './ChatInput';

export default function ChatContainer() {
  return (
    <div className="chat-container">
      <ChatHeader />
      <MessageList />
      <ConfirmationButtons />
      <ChatInput />
    </div>
  );
}
