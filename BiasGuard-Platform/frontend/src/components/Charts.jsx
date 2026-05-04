import React from 'react'
import { motion } from 'framer-motion'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Card } from './UI'

const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe']

export function BiasChart({ data, title }) {
  return (
    <Card className="h-96">
      <h3 className="text-lg font-semibold text-white mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
          <XAxis dataKey="name" stroke="#cbd5e1" />
          <YAxis stroke="#cbd5e1" />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' }} />
          <Legend />
          <Bar dataKey="value" fill="#667eea" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}

export function PerformanceChart({ data }) {
  return (
    <Card className="h-96">
      <h3 className="text-lg font-semibold text-white mb-4">Model Performance</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
          <XAxis dataKey="name" stroke="#cbd5e1" />
          <YAxis stroke="#cbd5e1" domain={[0, 1]} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' }} />
          <Legend />
          <Line type="monotone" dataKey="accuracy" stroke="#667eea" strokeWidth={2} dot={{ fill: '#667eea' }} />
          <Line type="monotone" dataKey="precision" stroke="#764ba2" strokeWidth={2} dot={{ fill: '#764ba2' }} />
          <Line type="monotone" dataKey="recall" stroke="#f093fb" strokeWidth={2} dot={{ fill: '#f093fb' }} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}

export function BiasDistributionChart({ groupData }) {
  if (!groupData || Object.keys(groupData).length === 0) {
    return (
      <Card className="h-96 flex items-center justify-center">
        <p className="text-slate-400">No group data available</p>
      </Card>
    )
  }

  const data = Object.entries(groupData).map(([name, value]) => ({
    name: name.substring(0, 20),
    value: Number((value * 100).toFixed(1)),
  }))

  return (
    <Card className="h-96">
      <h3 className="text-lg font-semibold text-white mb-4">Prediction Rate by Group</h3>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" labelLine={false} label={({ name, value }) => `${name}: ${value}%`} outerRadius={100} fill="#667eea" dataKey="value">
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => `${value}%`} contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' }} />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  )
}

export function BeforeAfterComparison({ before, after }) {
  const data = [
    { metric: 'Bias Score', before: Number(((before?.bias_score || 0) * 100).toFixed(1)), after: Number(((after?.bias_score || 0) * 100).toFixed(1)) },
    { metric: 'Accuracy', before: Number(((before?.accuracy || 0) * 100).toFixed(1)), after: Number(((after?.accuracy || 0) * 100).toFixed(1)) },
    { metric: 'Fairness', before: Number((((1 - (before?.bias_score || 0)) * 100)).toFixed(1)), after: Number((((1 - (after?.bias_score || 0)) * 100)).toFixed(1)) },
  ]

  return (
    <Card className="h-96">
      <h3 className="text-lg font-semibold text-white mb-4">Before vs After Mitigation</h3>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
          <XAxis dataKey="metric" stroke="#cbd5e1" />
          <YAxis stroke="#cbd5e1" domain={[0, 100]} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' }} formatter={(value) => `${value}%`} />
          <Legend />
          <Bar dataKey="before" fill="#667eea" radius={[8, 8, 0, 0]} />
          <Bar dataKey="after" fill="#10b981" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}

export function FeatureImportanceChart({ data }) {
  const chartData = Object.entries(data)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([name, value]) => ({
      name: name.substring(0, 15),
      importance: Number((value * 100).toFixed(1)),
    }))

  return (
    <Card className="h-96">
      <h3 className="text-lg font-semibold text-white mb-4">Top 10 Important Features</h3>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
          <XAxis type="number" stroke="#cbd5e1" />
          <YAxis dataKey="name" type="category" width={100} stroke="#cbd5e1" />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' }} formatter={(value) => `${value}%`} />
          <Bar dataKey="importance" fill="#667eea" radius={[0, 8, 8, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}
