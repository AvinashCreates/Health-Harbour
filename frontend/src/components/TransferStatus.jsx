export default function TransferStatus({ children = 'Transferring securely' }) {
  return (
    <span className="transfer-status" role="status" aria-live="polite">
      <span className="transfer-track" aria-hidden="true"><i /><i /><i /></span>
      {children}…
    </span>
  )
}
