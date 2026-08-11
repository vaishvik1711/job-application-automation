import { ScoreDistribution } from '@/types'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

interface MatchScoreDistributionProps {
  distribution: ScoreDistribution[]
}

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#10b981']

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-lg">
        <p className="text-sm font-medium text-slate-900 dark:text-white">{label}</p>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {payload[0].value} jobs
        </p>
      </div>
    )
  }
  return null
}

export function MatchScoreDistribution({ distribution }: MatchScoreDistributionProps) {
  if (!distribution || distribution.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Match Score Distribution</CardTitle>
          <CardDescription>Distribution of job match scores</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-500 dark:text-slate-400 text-center py-8">
            No match data available yet. Run job matching to see score distribution.
          </p>
        </CardContent>
      </Card>
    )
  }

  const chartData = distribution.map((d) => ({
    range: d.range,
    count: d.count,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart className="w-5 h-5" />
          Match Score Distribution
        </CardTitle>
        <CardDescription>
          Distribution of match scores across analyzed jobs
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 0, left: 0, bottom: 20 }}>
              <XAxis
                dataKey="range"
                axisLine={false}
                tick={{ fontSize: 12, fill: 'currentColor', opacity: 0.6 }}
                tickLine={false}
              />
              <YAxis
                axisLine={false}
                tick={{ fontSize: 12, fill: 'currentColor', opacity: 0.6 }}
                tickLine={false}
                width={30}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
