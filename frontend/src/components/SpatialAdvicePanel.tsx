import type { CheckDetail, FurnitureMove, PlacementCheckResponse } from "../types"

interface SpatialAdvicePanelProps {
  checking: boolean
  report: PlacementCheckResponse | null
  error: string
  onApplyMove: (move: FurnitureMove) => void
  onRecheck: () => void
  onRequestAgents: () => void
}

const STATUS_LABEL: Record<string, string> = {
  pass: "通过",
  warn: "注意",
  fail: "问题",
}

function statusClass(status: string) {
  if (status === "pass") return "is-pass"
  if (status === "warn") return "is-warn"
  return "is-fail"
}

function CheckRow({ check }: { check: CheckDetail }) {
  return (
    <li className={`spatial-check ${statusClass(check.status)}`}>
      <strong>
        {check.name}
        <span>{STATUS_LABEL[check.status] || check.status}</span>
      </strong>
      <p>{check.message}</p>
      {check.suggestion ? <small>{check.suggestion}</small> : null}
    </li>
  )
}

export function SpatialAdvicePanel({
  checking,
  report,
  error,
  onApplyMove,
  onRecheck,
  onRequestAgents,
}: SpatialAdvicePanelProps) {
  if (!checking && !report && !error) return null

  const move = report?.layout?.moves?.[0] ?? null

  return (
    <section className="spatial-advice" aria-live="polite">
      <header>
        <div>
          <span>SPATIAL ADAPTER</span>
          <h3>空间可行性</h3>
        </div>
        {report ? (
          <em className={statusClass(report.overallStatus)}>
            {STATUS_LABEL[report.overallStatus] || report.overallStatus}
          </em>
        ) : null}
      </header>

      {checking ? <p className="spatial-advice__loading">几何检测中…</p> : null}
      {error ? <p className="spatial-advice__error">{error}</p> : null}

      {report ? (
        <>
          <p className="spatial-advice__feedback">{report.feedback}</p>
          <ul className="spatial-check-list">
            {report.checks.map((check) => (
              <CheckRow key={check.ruleId} check={check} />
            ))}
          </ul>

          {move ? (
            <div className="spatial-move">
              <strong>几何建议</strong>
              <p>{move.reason}</p>
              <code>
                → [{move.toPosition.map((v) => v.toFixed(2)).join(", ")}]
              </code>
              <div className="spatial-move__actions">
                <button type="button" onClick={() => onApplyMove(move)}>
                  应用建议位姿
                </button>
                <button type="button" className="is-ghost" onClick={onRecheck}>
                  复检
                </button>
              </div>
            </div>
          ) : (
            <div className="spatial-move__actions">
              <button type="button" className="is-ghost" onClick={onRecheck}>
                再次检测
              </button>
            </div>
          )}

          <button type="button" className="spatial-advice__agents" onClick={onRequestAgents}>
            获取优化建议文案（Agent）
          </button>
        </>
      ) : null}
    </section>
  )
}
