import Modal from './Modal'

export default function ConfirmDialog({
  title = 'Are you sure?',
  message,
  confirmLabel = 'Confirm',
  onConfirm,
  onCancel,
  isWorking = false,
}) {
  return (
    <Modal
      title={title}
      onClose={onCancel}
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onCancel} disabled={isWorking}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary bg-red-600 hover:bg-red-700"
            onClick={onConfirm}
            disabled={isWorking}
          >
            {isWorking ? 'Working…' : confirmLabel}
          </button>
        </>
      }
    >
      <p className="text-sm text-slate-700">{message}</p>
    </Modal>
  )
}
