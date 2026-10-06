import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    print("Testing /health ...", end=" ")
    try:
        res = requests.get(f"{BASE_URL}/health")
        if res.status_code == 200:
            print("OK")
            return True
        else:
            print(f"FAIL ({res.status_code})")
            return False
    except Exception as e:
        print(f"FAIL ({e})")
        return False

def login(username, password):
    print(f"Testing login for {username} ...", end=" ")
    # The API uses OAuth2PasswordRequestForm which requires form-data: username, password
    data = {"username": username, "password": password}
    res = requests.post(f"{BASE_URL}/api/auth/login", data=data)
    if res.status_code == 200:
        print("OK")
        return res.json()["access_token"]
    print(f"FAIL ({res.status_code}): {res.text}")
    return None

def test_student_get_courses(token):
    print("Testing student get courses ...", end=" ")
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/courses/", headers=headers)
    if res.status_code == 200:
        data = res.json()
        print(f"OK (Fetched {len(data)} classes)")
        return data
    print(f"FAIL ({res.status_code}): {res.text}")
    return None

def test_admin_get_logs(token):
    print("Testing admin get logs ...", end=" ")
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/admin/logs", headers=headers)
    if res.status_code == 200:
        data = res.json()
        print("OK")
        return data
    print(f"FAIL ({res.status_code}): {res.text}")
    return None

def test_rbac_student_access_admin_api(student_token):
    print("Testing RBAC (Student -> Admin API) ...", end=" ")
    headers = {"Authorization": f"Bearer {student_token}"}
    res = requests.get(f"{BASE_URL}/api/admin/logs", headers=headers)
    if res.status_code == 403:
        print("OK (Forbidden as expected)")
    else:
        print(f"FAIL: Expected 403, got {res.status_code}")

def test_rbac_admin_access_student_api(admin_token):
    print("Testing RBAC (Admin -> Student API) ...", end=" ")
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = requests.get(f"{BASE_URL}/api/courses/", headers=headers)
    if res.status_code == 403:
        print("OK (Forbidden as expected)")
    else:
        print(f"FAIL: Expected 403, got {res.status_code}")

def main():
    if not test_health():
        print("Server is not running. Please start the server first.")
        sys.exit(1)

    print("\n--- Testing Authentication ---")
    admin_token = login("admin@vnu.edu.vn", "1")
    student_token = login("20020000", "1")

    if not admin_token or not student_token:
        print("Login failed, aborting tests.")
        sys.exit(1)

    print("\n--- Testing Success Scenarios ---")
    courses = test_student_get_courses(student_token)
    logs = test_admin_get_logs(admin_token)
    
    # We can also check if the student only sees courses mapped to their major or general courses
    if courses is not None:
        course_codes = [c['course_code'] for c in courses]
        print(f"  [Info] Student 20020000 (Major: Kỹ thuật phần mềm) sees courses: {set(course_codes)}")
        # Check if they see INT3110 (Kỹ thuật phần mềm) and INT1000 (General) but NOT INT3202 (Hệ thống thông tin)
        if "INT3110" in course_codes and "INT3202" not in course_codes:
            print("  [Pass] Major filtering works perfectly!")
        else:
            print("  [Fail] Major filtering might be incorrect.")

    print("\n--- Testing RBAC (Role-Based Access Control) ---")
    test_rbac_student_access_admin_api(student_token)
    test_rbac_admin_access_student_api(admin_token)
    
    print("\nAll tests finished.")

if __name__ == "__main__":
    main()
