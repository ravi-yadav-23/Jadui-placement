import { CheckCircle2 } from 'lucide-react'

export default function RiskAlerts({ riskAlerts }) {
  return (
    <div className="glass border border-border rounded-xl p-8">
      <h3 className="text-xl font-bold text-white mb-4">Risk Alerts</h3>
      {riskAlerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="w-12 h-12 rounded-full bg-success/10 flex items-center justify-center mb-3">
            <CheckCircle2 className="w-6 h-6 text-success" />
          </div>
          <p className="text-sm text-success font-medium">All clear! No critical risks detected.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {riskAlerts.map((alert) => (
            <li key={alert} className="text-sm text-warning rounded-xl border border-warning/10 bg-warning/5 px-4 py-3 flex items-start gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-warning mt-1.5 shrink-0" />
              {alert}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
