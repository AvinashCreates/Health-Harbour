import http from 'k6/http'
import { check } from 'k6'

const baseUrl = (__ENV.TARGET_URL || 'http://localhost:8000').replace(/\/$/, '')

export const options = {
  scenarios: {
    increasing_workload: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: __ENV.RAMP_DURATION || '1m', target: 10 },
        { duration: __ENV.RAMP_DURATION || '1m', target: 30 },
        { duration: __ENV.RAMP_DURATION || '1m', target: 50 },
        { duration: __ENV.RAMP_DURATION || '1m', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000'],
    'http_req_duration{endpoint:health}': ['p(95)<500'],
  },
}

export default function () {
  const health = http.get(`${baseUrl}/health`, { tags: { endpoint: 'health' } })
  check(health, {
    'health endpoint responds successfully': (response) => response.status === 200,
    'health endpoint reports healthy': (response) => response.json('status') === 'healthy',
  })

  if (__ENV.AUTH_TOKEN) {
    const profilePath = __ENV.AUTH_PATH || '/auth/me'
    const profile = http.get(`${baseUrl}${profilePath}`, {
      headers: { Authorization: `Bearer ${__ENV.AUTH_TOKEN}` },
      tags: { endpoint: profilePath === '/auth/me' ? 'authenticated-profile' : 'authenticated-read' },
    })
    check(profile, {
      'authenticated request responds successfully': (response) => response.status === 200,
    })
  }
}
