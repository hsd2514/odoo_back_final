from __future__ import annotations

import json
import urllib.request


BASE_URL = "http://localhost:8000"


def request(method: str, path: str, data: dict | None = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text else None
    except urllib.error.HTTPError as e:  # type: ignore[attr-defined]
        body = e.read().decode("utf-8")
        print("HTTPError", e.code, body)
        raise


def main() -> None:
    # 1) Create inventory item
    created = request("POST", "/inventory/items", {
        "product_id": 1,
        "sku": "SKU-001",
        "serial": "SN-001",
        "qty": 5,
        "status": "available",
    })
    print("CREATE:", created)
    item_id = created["item_id"]

    # 2) List available items
    with urllib.request.urlopen(f"{BASE_URL}/inventory/items?status=available") as resp:
        print("LIST available:", json.loads(resp.read().decode("utf-8")))

    # 3) Update status transitions via PATCH
    for new_status in ["reserved", "rented", "available"]:
        updated = request("PATCH", f"/inventory/items/{item_id}/status?new_status={new_status}")
        print(f"STATUS -> {new_status}:", updated)

    # 4) Delete
    req = urllib.request.Request(f"{BASE_URL}/inventory/items/{item_id}", method="DELETE")
    with urllib.request.urlopen(req) as resp:
        print("DELETE:", resp.status)


if __name__ == "__main__":
    main()


