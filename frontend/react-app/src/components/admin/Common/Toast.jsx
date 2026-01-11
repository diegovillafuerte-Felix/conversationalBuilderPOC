import { useAdminStore } from '../../../store/adminStore';

export default function Toast() {
  const toast = useAdminStore((state) => state.toast);

  if (!toast) return null;

  return (
    <div className={`toast ${toast.type}`}>
      {toast.message}
    </div>
  );
}
