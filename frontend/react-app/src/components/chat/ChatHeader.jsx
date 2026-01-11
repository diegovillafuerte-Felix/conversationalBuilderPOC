import { useChatStore } from '../../store/chatStore';

export default function ChatHeader() {
  const agentName = useChatStore((state) => state.agentName);

  return (
    <div className="chat-header">
      <div className="header-info">
        <h1>{agentName}</h1>
        <div className="status">En línea</div>
      </div>
    </div>
  );
}
