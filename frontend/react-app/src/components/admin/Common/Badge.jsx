export default function Badge({ children, variant = 'default' }) {
  return (
    <span className={`badge ${variant}`}>
      {children}
    </span>
  );
}
