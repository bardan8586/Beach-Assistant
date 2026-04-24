/**
 * Section heading — command-centre hierarchy.
 */

interface SectionHeaderProps {
  kicker: string
  title: string
  description?: string
}

export default function SectionHeader({ kicker, title, description }: SectionHeaderProps) {
  return (
    <header className="cc-enter mb-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-400/80">{kicker}</p>
      <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-slate-100 sm:text-2xl">{title}</h2>
      {description ? (
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{description}</p>
      ) : null}
    </header>
  )
}
