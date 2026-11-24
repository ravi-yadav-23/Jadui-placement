import { Target } from 'lucide-react'
import {
  ResponsiveContainer,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  Tooltip
} from 'recharts'

export default function ReadinessRadar({ readinessData }) {
  return (
    <div className="lg:col-span-2 glass border border-border rounded-2xl p-6 shadow-glow flex flex-col h-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <Target className="w-5 h-5 text-primary" />
            Readiness Radar
          </h3>
          <p className="text-xs text-muted mt-1">Cross-module candidate analysis</p>
        </div>
        <div className="flex gap-2">
           <span className="text-[10px] uppercase font-bold text-primary bg-primary/10 px-2 py-1 rounded">Resume</span>
           <span className="text-[10px] uppercase font-bold text-success bg-success/10 px-2 py-1 rounded">Interview</span>
        </div>
      </div>
      
      <div className="flex-1 w-full min-h-[300px]">
        {readinessData ? (
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="80%" data={readinessData}>
              <PolarGrid stroke="#333" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} axisLine={false} tick={false} />
              <Radar
                 name="Candidate"
                 dataKey="value"
                 stroke="#6366f1"
                 fill="#6366f1"
                 fillOpacity={0.5}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#111120', border: '1px solid #333', borderRadius: '8px' }}
                itemStyle={{ color: '#fff' }}
              />
            </RadarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full text-xs text-muted">
            Review your resume and take a mock interview to fill the radar
          </div>
        )}
      </div>
    </div>
  )
}
