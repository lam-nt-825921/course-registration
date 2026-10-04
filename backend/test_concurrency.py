import concurrent.futures
import requests

URL = "http://localhost:8000/api/courses/1/register"


def register(student_id):
    try:
        response = requests.post(
            URL,
            params={"student_id": student_id},
            timeout=10,
        )

        return {
            "student_id": student_id,
            "status": response.status_code,
            "body": response.text,
        }

    except Exception as e:
        return {
            "student_id": student_id,
            "status": "ERROR",
            "body": str(e),
        }


def main():
    total_requests = 100

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=100
    ) as executor:

        futures = [
            executor.submit(register, student_id)
            for student_id in range(1, total_requests + 1)
        ]

        results = [
            future.result()
            for future in concurrent.futures.as_completed(futures)
        ]

    success = [
        result for result in results
        if result["status"] == 200
    ]

    failed = [
        result for result in results
        if result["status"] == 400
    ]

    errors = [
        result for result in results
        if result["status"] not in [200, 400]
    ]

    print("=" * 50)
    print("CONCURRENT REGISTRATION TEST")
    print("=" * 50)

    print(f"Total requests : {total_requests}")
    print(f"Success        : {len(success)}")
    print(f"Rejected (400) : {len(failed)}")
    print(f"Other errors   : {len(errors)}")

    print("\nSuccess responses:")
    for result in success:
        print(result)

    print("\nOther errors:")
    for result in errors:
        print(result)


if __name__ == "__main__":
    main()