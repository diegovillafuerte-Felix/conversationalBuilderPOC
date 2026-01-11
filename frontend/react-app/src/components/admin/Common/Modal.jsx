export default function Modal({ title, children, onClose, size = 'default' }) {
  const sizeClass = size === 'large' ? 'modal-large' : size === 'small' ? 'modal-small' : '';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className={`modal-content ${sizeClass}`} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        {children}
      </div>
    </div>
  );
}
