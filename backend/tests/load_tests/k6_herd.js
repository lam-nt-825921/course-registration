import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000/api/courses";

const systemErrorRate = new Rate("baseline_system_errors");     
const businessErrorRate = new Rate("baseline_business_errors"); 
const successRate = new Rate("baseline_success_rate");         
const registrationLatency = new Trend("registration_duration")

const CLASSCODES = open("./class_codes.txt")
    .trim()
    .split("\n")
    .map((code) => code.trim());
export const options = {

  scenarios: {
    registration_herd: {
      executor: "ramping-vus",
      startVUs: 0,

      stages: [
        { duration: "30s", target: 50 },
        { duration: "30s", target: 200 },
        { duration: "30s", target: 500 },
        { duration: "30s", target: 1000 },
        { duration: "60s", target: 1000 },
        { duration: "30s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
  },

  thresholds: {
    baseline_system_errors: ["rate<0.05"],

    http_req_duration: [
      "p(95)<2000",
      "p(99)<5000",
    ],
  },
};

export default function () {
    const studentId = String(20240000 + (__VU * 10000) + __ITER);

    const classIndex = Math.floor(Math.random() * CLASSCODES.length);
    const CLASS_CODE = CLASSCODES[classIndex];
    
    const url =
    `${BASE_URL}/register` +
    `?class_code=${encodeURIComponent(CLASS_CODE)}` +
    `&student_id=${encodeURIComponent(studentId)}`;

    const startTime = new Date();
    const res = http.post(
        url,
        null,
        {
        headers: {
            "Content-Type": "application/json",
        },

        tags: {
          name: "POST /register",
          endpoint: "course_registration",
        },
        }
    );
    const duration = new Date() - startTime;

    registrationLatency.add(duration);

    const is2xx = res.status >= 200 && res.status < 300;
    const is4xx = res.status >= 400 && res.status < 500;
    const is5xx = res.status >= 500 || res.status === 0;

    successRate.add(is2xx);
    businessErrorRate.add(is4xx);
    systemErrorRate.add(is5xx);

    check(res, {
        "Server responded (Not 5xx/Timeout)": () => !is5xx,
        "Response time < 2000ms": () => res.timings.duration < 2000,
    });
    if (res.status >= 400 && res.status < 500) {
      console.log(`Lỗi 4xx (${res.status}): ${res.body}`);
    }
    sleep(Math.random() * 0.4 + 0.1);
    }
