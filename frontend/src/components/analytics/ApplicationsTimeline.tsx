import { TimeSeriesData } from '@/types'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { format, parseISO } from 'date-fns'

interface ApplicationsTimelineProps {
  data: TimeSeriesData[]
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-lg space-y-1">
        <p className="text-sm font-medium text-slate-900 dark:text-white">{label}</p>
        {payload.map((entry: any) => (
          <p key={entry.dataKey} className="text-xs" style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export function ApplicationsTimeline({ data }: ApplicationsTimelineProps) {
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Applications Over Time</CardTitle>
          <CardDescription>Application activity over the past 30 days</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-500 dark:text-slate-400 text-center py-8">
            No activity data available yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  const chartData = data.map((d) => ({
    date: format(parseISO(d.date), 'MMM d'),
    applications: d.applications,
    interviews: d.interviews,
    offers: d.offers,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Applications Over Time</CardTitle>
        <CardDescription>Application activity, interviews, and offers over the past 30 days</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 0, left: 0, bottom: 20 }}>
              <XAxis
                dataKey="date"
                axisLine={false}
                tick={{ fontSize: 12, fill: 'currentColor', opacity: 0.6 }}
                tickLine={false}
                tickMargin={5}
              />
              <YAxis
                axisLine={false}
                tick={{ fontSize: 12, fill: 'currentColor', opacity: 0.6 }}
                tickLine={false}
                width={30}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{
                  color: 'currentColor',
                  fontSize: '12px',
                }}
              />
              <Line
                type="monotone"
                dataKey="applications"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                name="Applications"
              />
              <Line
                type="monotone"
                dataKey="interviews"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                name="Interviews"
              />
              <Line
                type="monotone"
                dataKey="offers"
                stroke="#22c55e"
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                name="Offers"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
