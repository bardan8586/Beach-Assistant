/**
 * Stats Card Component
 * ====================
 * Reusable card for displaying statistics
 */

interface StatsCardProps {
  title: string
  value: string | number
  icon?: string
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'gray'
  subtitle?: string
}

const colorClasses = {
  blue: 'text-primary-600',
  green: 'text-green-600',
  yellow: 'text-yellow-600',
  red: 'text-red-600',
  gray: 'text-gray-900',
}

export default function StatsCard({ 
  title, 
  value, 
  icon, 
  color = 'gray',
  subtitle 
}: StatsCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow">
      <div className="text-center">
        {icon && (
          <div className="text-3xl mb-2">{icon}</div>
        )}
        <div className={`text-4xl font-bold ${colorClasses[color]}`}>
          {value}
        </div>
        <div className="text-sm text-gray-600 mt-2 font-medium">
          {title}
        </div>
        {subtitle && (
          <div className="text-xs text-gray-500 mt-1">
            {subtitle}
          </div>
        )}
      </div>
    </div>
  )
}

