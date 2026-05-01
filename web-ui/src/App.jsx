import { useEffect, useMemo, useRef, useState } from 'react'
import mqtt from 'mqtt'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'

const DEVICE_IDS = ['device_01', 'device_02', 'device_03', 'device_04', 'device_05']
const MAX_POINTS = 120
const MIN_TEMP = 20
const MAX_TEMP = 60

const emptyDevice = () => ({
  actual: null,
  predicted: null,
  trend: 'warming_up',
  trendSlope: null,
  threshold: null,
  status: 'NORMAL',
  statusMessage: 'Waiting for data...',
  lastSeen: null,
  series: [],
})

const formatClock = (value) => {
  if (!value) return 'N/A'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'N/A'
  return date.toLocaleTimeString('en-GB', { hour12: false })
}

const formatDate = (value) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'N/A'
  return date.toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  })
}

const getDeviceId = (topic, payload) => {
  if (payload?.device_id) return payload.device_id
  const parts = (topic || '').split('/')
  if (parts.length >= 4) return parts[3]
  return 'device'
}

const clamp = (value, min, max) => Math.min(Math.max(value, min), max)

function App() {
  const [activeDevice, setActiveDevice] = useState(DEVICE_IDS[0])
  const [connection, setConnection] = useState('disconnected')
  const [devices, setDevices] = useState(() =>
    DEVICE_IDS.reduce((acc, id) => ({ ...acc, [id]: emptyDevice() }), {})
  )
  const [alerts, setAlerts] = useState([])
  const [thresholdInput, setThresholdInput] = useState(35)
  const [clock, setClock] = useState(() => new Date())
  const clientRef = useRef(null)

  useEffect(() => {
    const timer = setInterval(() => setClock(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const url =
      import.meta.env.VITE_MQTT_WS_URL?.trim() || 'ws://localhost:9001'
    const client = mqtt.connect(url, {
      clientId: `web-ui-${Math.random().toString(16).slice(2, 10)}`,
      reconnectPeriod: 2000,
      connectTimeout: 5000,
      clean: true,
    })
    clientRef.current = client

    client.on('connect', () => {
      setConnection('connected')
      client.subscribe('sensors/+/project33/+/data')
      client.subscribe('alerts/+/project33/+/status')
    })

    client.on('reconnect', () => setConnection('reconnecting'))
    client.on('close', () => setConnection('disconnected'))
    client.on('error', () => setConnection('error'))

    client.on('message', (topic, payload) => {
      let data
      try {
        data = JSON.parse(payload.toString())
      } catch (err) {
        return
      }

      if (topic.includes('/data')) {
        const deviceId = getDeviceId(topic, data)
        setDevices((prev) => {
          if (!prev[deviceId]) {
            return prev
          }
          const actual = Number(data.actual_temp)
          const predicted =
            typeof data.predicted_temp === 'number'
              ? data.predicted_temp
              : Number(data.predicted_temp)
          const timestamp = data.timestamp || new Date().toISOString()
          const nextPoint = {
            ts: timestamp,
            actual: Number.isNaN(actual) ? null : actual,
            predicted: Number.isNaN(predicted) ? null : predicted,
          }
          const series = [...prev[deviceId].series, nextPoint].slice(-MAX_POINTS)

          return {
            ...prev,
            [deviceId]: {
              ...prev[deviceId],
              actual: Number.isNaN(actual) ? null : actual,
              predicted: Number.isNaN(predicted) ? null : predicted,
              trend: data.trend || prev[deviceId].trend,
              trendSlope:
                typeof data.trend_slope === 'number'
                  ? data.trend_slope
                  : prev[deviceId].trendSlope,
              threshold:
                typeof data.threshold === 'number'
                  ? data.threshold
                  : prev[deviceId].threshold,
              lastSeen: timestamp,
              series,
            },
          }
        })
      }

      if (topic.includes('/status')) {
        const deviceId = getDeviceId(topic, data)
        setDevices((prev) => {
          if (!prev[deviceId]) {
            return prev
          }
          return {
            ...prev,
            [deviceId]: {
              ...prev[deviceId],
              status: data.status || prev[deviceId].status,
              statusMessage: data.message || prev[deviceId].statusMessage,
              lastSeen: data.timestamp || prev[deviceId].lastSeen,
            },
          }
        })
        setAlerts((prev) => {
          const next = [
            {
              deviceId,
              status: data.status || 'UNKNOWN',
              message: data.message || 'No message',
              timestamp: data.timestamp || new Date().toISOString(),
            },
            ...prev,
          ]
          return next.slice(0, 10)
        })
      }
    })

    return () => {
      client.end(true)
    }
  }, [])

  const activeData = devices[activeDevice] || emptyDevice()
  useEffect(() => {
    if (typeof activeData.threshold === 'number') {
      setThresholdInput(activeData.threshold)
    }
  }, [activeDevice, activeData.threshold])
  const deviceRows = useMemo(
    () =>
      Object.entries(devices)
        .map(([id, data]) => ({
          id,
          lastSeen: data.lastSeen,
          status: data.status,
          actual: data.actual,
        }))
        .sort((a, b) => (b.lastSeen || '').localeCompare(a.lastSeen || '')),
    [devices]
  )

  const onlineCount = useMemo(() => {
    const now = Date.now()
    return deviceRows.filter((row) => {
      if (!row.lastSeen) return false
      const ts = Date.parse(row.lastSeen)
      return !Number.isNaN(ts) && now - ts < 120000
    }).length
  }, [deviceRows])

  const criticalCount = useMemo(
    () => deviceRows.filter((row) => row.status === 'CRITICAL').length,
    [deviceRows]
  )

  const avgThreshold = useMemo(() => {
    const values = Object.values(devices)
      .map((item) => item.threshold)
      .filter((value) => typeof value === 'number')
    if (!values.length) return null
    return values.reduce((sum, value) => sum + value, 0) / values.length
  }, [devices])

  const handleThresholdApply = () => {
    if (!clientRef.current) return
    const value = Number(thresholdInput)
    if (Number.isNaN(value)) return
    const payload = JSON.stringify({ threshold: value })
    clientRef.current.publish('controls/group_33/project33/threshold', payload)
  }

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div className="top-left">
          <p className="eyebrow">Industrial Edge Suite</p>
          <h1>Predictive Temperature Command Center</h1>
          <p className="subhead">Plant Line A - Sector 3 | Live MQTT Telemetry</p>
        </div>
        <div className="top-right">
          <div className="clock-stack">
            <span>{formatDate(clock)}</span>
            <strong>{formatClock(clock)}</strong>
          </div>
          <div className={`connection-pill ${connection}`}>
            <span className="dot" />
            {connection.toUpperCase()}
          </div>
        </div>
      </header>

      <section className="hero-strip">
        <div className="hero-card">
          <p className="label">Fleet Online</p>
          <p className="value-xl">
            {onlineCount}/{DEVICE_IDS.length}
          </p>
          <span className="hint">Last 2 minutes</span>
        </div>
        <div className="hero-card">
          <p className="label">Critical Alerts</p>
          <p className={`value-xl ${criticalCount ? 'critical' : 'normal'}`}>
            {criticalCount}
          </p>
          <span className="hint">Active devices</span>
        </div>
        <div className="hero-card">
          <p className="label">Avg Threshold</p>
          <p className="value-xl">
            {avgThreshold === null ? 'N/A' : avgThreshold.toFixed(1)}
            <span className="unit">degC</span>
          </p>
          <span className="hint">Config baseline</span>
        </div>
        <div className="hero-card">
          <p className="label">Active Device</p>
          <p className="value-xl">{activeDevice}</p>
          <span className="hint">Operator focus</span>
        </div>
      </section>

      <section className="status-strip">
        <div>
          <p className="label">Last Seen</p>
          <p className="value-xl">{formatClock(activeData.lastSeen)}</p>
        </div>
        <div>
          <p className="label">Alert Status</p>
          <p className={`value-xl ${activeData.status.toLowerCase()}`}>
            {activeData.status}
          </p>
        </div>
        <div>
          <p className="label">Threshold</p>
          <p className="value-xl">
            {activeData.threshold ?? 'N/A'}
            <span className="unit">degC</span>
          </p>
        </div>
        <div>
          <p className="label">Recent Alerts</p>
          <p className="value-xl">{alerts.length}</p>
        </div>
      </section>

      <div className="layout">
        <aside className="device-rail">
          <h2>Device Stack</h2>
          <div className="device-tabs">
            {DEVICE_IDS.map((id) => (
              <button
                key={id}
                type="button"
                className={`device-tab ${activeDevice === id ? 'active' : ''}`}
                onClick={() => setActiveDevice(id)}
              >
                <span>{id}</span>
                <span className={`status-chip ${devices[id]?.status || ''}`}>
                  {devices[id]?.status || 'N/A'}
                </span>
              </button>
            ))}
          </div>
          <div className="control-panel">
            <h3>Threshold Control</h3>
            <p className="muted">Broadcast to all devices</p>
            <div className="threshold-display">
              <span>Active</span>
              <strong>{activeData.threshold ?? 'N/A'} degC</strong>
            </div>
            <div className="slider-wrap">
              <input
                type="range"
                min="28"
                max="45"
                step="0.5"
                value={thresholdInput}
                onChange={(event) => setThresholdInput(event.target.value)}
              />
              <div className="slider-labels">
                <span>28</span>
                <span>{thresholdInput} degC</span>
                <span>45</span>
              </div>
            </div>
            <button
              type="button"
              className="apply-btn"
              onClick={handleThresholdApply}
              disabled={connection !== 'connected'}
            >
              Apply Threshold
            </button>
          </div>
          <div className="alert-panel">
            <h3>Alert Feed</h3>
            <div className="alert-list">
              {alerts.length === 0 && <p className="muted">No alerts yet.</p>}
              {alerts.map((alert, index) => (
                <div key={`${alert.timestamp}-${index}`} className="alert-item">
                  <span className={`badge ${alert.status.toLowerCase()}`}>
                    {alert.status}
                  </span>
                  <div>
                    <p className="alert-device">{alert.deviceId}</p>
                    <p className="alert-message">{alert.message}</p>
                    <p className="alert-time">{formatClock(alert.timestamp)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </aside>

        <main className="main-panel">
          <section className="panel-grid">
            <div className="panel span-2">
              <div className="panel-header">
                <h2>{activeDevice} Telemetry</h2>
                <p className="muted">Actual vs predicted temperature</p>
              </div>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={activeData.series} margin={{ left: 10, right: 20 }}>
                    <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                    <XAxis dataKey="ts" tickFormatter={formatClock} stroke="#8fa3b8" />
                    <YAxis stroke="#8fa3b8" tickFormatter={(v) => `${v}`} />
                    <Tooltip
                      contentStyle={{
                        background: '#111923',
                        border: '1px solid #2c3b4d',
                        color: '#f8fafc',
                      }}
                      labelFormatter={(value) => formatClock(value)}
                    />
                    <Line
                      type="monotone"
                      dataKey="actual"
                      stroke="#2aa3ff"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="predicted"
                      stroke="#ffb020"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <h2>Live KPIs</h2>
                <p className="muted">Device health snapshot</p>
              </div>
              <div className="kpi-grid">
                <div>
                  <p className="label">Actual Temp</p>
                  <p className="value-lg">
                    {activeData.actual ?? 'N/A'}
                    <span className="unit">degC</span>
                  </p>
                </div>
                <div>
                  <p className="label">Predicted Temp</p>
                  <p className="value-lg">
                    {activeData.predicted ?? 'N/A'}
                    <span className="unit">degC</span>
                  </p>
                </div>
                <div>
                  <p className="label">Trend</p>
                  <p className="value-lg">{activeData.trend}</p>
                </div>
                <div>
                  <p className="label">Trend Slope</p>
                  <p className="value-lg">
                    {activeData.trendSlope ?? 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="label">Last Seen</p>
                  <p className="value-lg">{formatClock(activeData.lastSeen)}</p>
                </div>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <h2>Device Fleet</h2>
                <p className="muted">Latest signal timestamps</p>
              </div>
              <div className="table">
                <div className="table-head">
                  <span>Device</span>
                  <span>Status</span>
                  <span>Last Seen</span>
                </div>
                {deviceRows.map((row) => (
                  <div key={row.id} className="table-row">
                    <span className="mono">{row.id}</span>
                    <span className={`badge ${row.status.toLowerCase()}`}>
                      {row.status}
                    </span>
                    <span>{formatClock(row.lastSeen)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel span-2 gauges-panel">
              <div className="panel-header">
                <h2>Device Gauges</h2>
                <p className="muted">Live actual temperature per edge device</p>
              </div>
              <div className="gauge-grid">
                {deviceRows.map((row) => {
                  const actual = typeof row.actual === 'number' ? row.actual : null
                  const normalized = actual === null
                    ? 0
                    : clamp((actual - MIN_TEMP) / (MAX_TEMP - MIN_TEMP), 0, 1)
                  const needle = -90 + normalized * 180
                  const fill = normalized * 180
                  return (
                    <div key={row.id} className="gauge-card">
                      <div className="gauge-meta">
                        <span className="mono">{row.id}</span>
                        <span className={`badge ${row.status.toLowerCase()}`}>
                          {row.status}
                        </span>
                      </div>
                      <div className="gauge-wrap">
                        <div
                          className="gauge-dial"
                          style={{
                            '--fill-angle': `${fill}deg`,
                            '--needle-angle': `${needle}deg`,
                          }}
                        >
                          <span className="gauge-needle" />
                          <span className="gauge-center" />
                        </div>
                      </div>
                      <div className="gauge-readout">
                        <span>{actual === null ? 'N/A' : actual.toFixed(1)}</span>
                        <span className="unit">degC</span>
                      </div>
                      <div className="gauge-scale">
                        <span>{MIN_TEMP}</span>
                        <span>{MAX_TEMP}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  )
}

export default App
