export default function Message({ content, type }) {
  return (
    <div className={`message ${type}`}>
      <div className="message-content">{content}</div>
    </div>
  );
}
