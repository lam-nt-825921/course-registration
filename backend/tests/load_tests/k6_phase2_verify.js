import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate } from 'k6/metrics';

/**
 * Kịch bản Kiểm thử Chịu tải & Chống Vượt Sĩ Số (Phase 2 QA Verification - NFR-01 & NFR-02)
 *
 * Cách chạy:
 *   k6 run -e BASE_URL=http://localhost:8000 -e HOT_CLASS_ID=<uuid> -e TOKEN=<jwt> \
 *          backend/tests/load_tests/k6_phase2_verify.js
 */

export const enrolledSuccessCounter = new Counter('enrolled_200_total');
export const rejectedFullCounter = new Counter('rejected_400_total');
export const rateLimitedCounter = new Counter('rate_limited_429_total');
export const serverErrorRate = new Rate('server_5xx_error_rate');

export const options = {
  scenarios: {
    // Kịch bản 1: 100 sinh viên đồng thời tranh 1 lớp học phần nóng tại cùng 1 mili-giây (NFR-02)
    zero_overselling_race: {
      executor: 'per-vu-iterations',
      vus: 100,
      iterations: 1,
      maxDuration: '30s',
      exec: 'raceHotClass',
    },
    // Kịch bản 2: Thundering Herd đọc danh sách môn học & thời khóa biểu ở cường độ cao (NFR-01)
    thundering_herd_catalog: {
      executor: 'ramping-arrival-rate',
      startRate: 100,
      timeUnit: '1s',
      preAllocatedVUs: 200,
      maxVUs: 1000,
      stages: [
        { target: 500, duration: '15s' },
        { target: 1000, duration: '30s' },
        { target: 0, duration: '10s' },
      ],
      exec: 'browseCatalog',
      startTime: '5s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500'],        // NFR-01: p95 < 500ms
    server_5xx_error_rate: ['rate<0.01'],    // Tỷ lệ lỗi 5xx < 1%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const HOT_CLASS_ID = __ENV.HOT_CLASS_ID || '00000000-0000-0000-0000-000000000001';
const TOKEN = __ENV.TOKEN || '';

function buildHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (TOKEN) {
    headers['Authorization'] = `Bearer ${TOKEN}`;
  }
  return headers;
}

export function raceHotClass() {
  const url = `${BASE_URL}/api/courses/register`;
  const payload = JSON.stringify({ course_class_id: HOT_CLASS_ID });
  const res = http.post(url, payload, { headers: buildHeaders() });

  if (res.status === 200) {
    enrolledSuccessCounter.add(1);
  } else if (res.status === 400) {
    rejectedFullCounter.add(1);
  } else if (res.status === 429 || res.status === 503) {
    rateLimitedCounter.add(1);
  }

  serverErrorRate.add(res.status >= 500 && res.status !== 503);

  check(res, {
    'status is controlled (200/400/429/503)': (r) =>
      [200, 400, 429, 503].includes(r.status),
  });
}

export function browseCatalog() {
  const url = `${BASE_URL}/api/courses/?page=1&size=20&can_register=true`;
  const res = http.get(url, { headers: buildHeaders() });

  serverErrorRate.add(res.status >= 500 && res.status !== 503);

  check(res, {
    'catalog read fast (<500ms)': (r) => r.timings.duration < 500,
  });
  sleep(0.05);
}
