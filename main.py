import os
import sys
import requests
import json

class DhcpClient:
    def __init__(self):
        self.host = os.environ.get("HOST")
        if not self.host:
            raise ValueError("HOST environment variable not set")
        self.base_url = f"{self.host}/api"
        self.token = os.environ.get("API_TOKEN")
        if not self.token:
            raise ValueError("API_TOKEN environment variable not set")

        self._create_initial_files()

    @staticmethod
    def _create_initial_files():
        initial_files = {
            "data/leases.json": [],
            "data/reserved-leases.json": []
        }
        for path, content in initial_files.items():
            if os.path.exists(path):
                print(f"File already exists: {path}")
                continue
            abs_path = os.path.abspath(path)
            dir_path = os.path.dirname(abs_path)
            os.makedirs(dir_path, exist_ok=True)
            with open(abs_path, "w") as f:
                json.dump(content, f, indent=2)
            print(f"Created {abs_path}")

    def get_leases(self):
        url = f"{self.base_url}/dhcp/leases/list"
        params = {"token": self.token}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data["response"]["leases"]

    @staticmethod
    def write_leases(leases, path="data/leases.json"):
        abs_path = os.path.abspath(path)
        dir_path = os.path.dirname(abs_path)
        os.makedirs(dir_path, exist_ok=True)
        with open(abs_path, "w") as f:
            json.dump(leases, f, indent=2)
        print(f"Wrote {len(leases)} leases to {abs_path}")

    def reserve_leases(self, path="data/reserved-leases.json"):
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            print(f"File not found: {abs_path}")
            return
        with open(abs_path) as f:
            leases = json.load(f)
        for lease in leases:
            params = {
                "token": self.token,
                "name": lease.get("scope", "Default"),
                "hardwareAddress": lease["hardwareAddress"],
                "ipAddress": lease["address"],
            }
            if "hostName" in lease:
                params["hostName"] = lease["hostName"]
            if "comments" in lease:
                params["comments"] = lease["comments"]
            url = f"{self.base_url}/dhcp/scopes/addReservedLease"
            response = requests.post(url, params=params)
            if response.ok:
                print(f"{lease['hardwareAddress']:20} {lease['hostName']:20} {lease['address']:15}")
            else:
                print(f"Failed to add reserved lease for {lease['hardwareAddress']}: {response.text}")


if __name__ == "__main__":
    client = DhcpClient()
    if len(sys.argv) > 1:
        if sys.argv[1] == "get_leases":
            current_leases = client.get_leases()
            client.write_leases(current_leases)
        elif sys.argv[1] == "reserve_leases":
            client.reserve_leases()