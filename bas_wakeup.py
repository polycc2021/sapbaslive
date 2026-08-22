import os
import sys
import time
import requests

BAS_URL = os.environ["BAS_URL"].rstrip("/")
USERNAME = os.environ["BAS_USERNAME"]
PASSWORD = os.environ["BAS_PASSWORD"]
DEVSPACE = os.environ["BAS_DEVSPACE"]
DEVSPACE_ID = os.environ["BAS_DEVSPACE_ID"]

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

print("[BAS] URL:", BAS_URL)
print("[BAS] Workspace:", DEVSPACE)
print("[BAS] Workspace ID:", DEVSPACE_ID)


def get_jwt():
    print("[BAS] Getting JWT...")

    r = session.get(
        f"{BAS_URL}/jwt",
        auth=(USERNAME, PASSWORD),
        timeout=30
    )

    print("[BAS] JWT status:", r.status_code)

    if r.status_code != 200:
        print("[BAS] Failed to obtain JWT")
        print(r.text[:1000])
        sys.exit(1)

    return r.text.strip()


def wake_workspace(jwt):
    url = (
        f"{BAS_URL}/ws-manager/api/v1/workspace/"
        f"{DEVSPACE_ID}"
    )

    headers = {
        "X-Approuter-Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json"
    }

    data = {
        "suspended": False,
        "WorkspaceDisplayName": DEVSPACE
    }

    print("[BAS] Sending wake-up request...")

    r = session.put(
        url,
        headers=headers,
        params={
            "all": "false",
            "username": USERNAME
        },
        json=data,
        timeout=30
    )

    print("[BAS] Wake status:", r.status_code)
    print("[BAS] Response:", r.text[:2000])

    if r.status_code not in (200, 201, 202):
        print("[BAS] Wake-up failed")
        sys.exit(1)


def main():
    jwt = get_jwt()
    wake_workspace(jwt)

    print("[BAS] Wake-up request completed.")
    print("[BAS] Waiting for Dev Space to become RUNNING...")

    time.sleep(10)


if __name__ == "__main__":
    main()