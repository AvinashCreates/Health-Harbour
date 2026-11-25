export default function LoadingSkeleton({ cards = 3, label = 'Loading workspace' }) {
  return (
    <div className="skeleton-layout" role="status" aria-label={label} aria-busy="true">
      <span className="sr-only">{label}…</span>
      {Array.from({ length: cards }, (_, index) => (
        <section className="card skeleton-card" key={index} aria-hidden="true">
          <span className="skeleton-line skeleton-line-short" />
          <span className="skeleton-line skeleton-line-title" />
          <span className="skeleton-line" />
          <span className="skeleton-line skeleton-line-medium" />
        </section>
      ))}
    </div>
  )
}
