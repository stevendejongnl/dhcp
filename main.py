import inspect
import ipaddress
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
                continue
            abs_path = os.path.abspath(path)
            dir_path = os.path.dirname(abs_path)
            os.makedirs(dir_path, exist_ok=True)
            with open(abs_path, "w") as f:
                json.dump(content, f, indent=2)
            print(f"Created {abs_path}")
        print("\n\n")

    @staticmethod
    def _write_leases(leases, path="data/leases.json"):
        abs_path = os.path.abspath(path)
        dir_path = os.path.dirname(abs_path)
        os.makedirs(dir_path, exist_ok=True)
        with open(abs_path, "w") as f:
            json.dump(leases, f, indent=2)
        print(f"Wrote {len(leases)} leases to {abs_path}")

    def help(self):
        """List available commands."""
        methods = [
            (name, func) for name, func in inspect.getmembers(self, predicate=inspect.ismethod)
            if not name.startswith("_")
        ]
        methods.sort(key=lambda x: (x[0] != "help", x[0]))
        print("Available commands:")
        for name, func in methods:
            doc = func.__doc__ or ""
            doc = doc.strip().split("\n")[0]
            print(f"  {name:25} {doc}")

    def get_leases(self):
        """Get the current leases from the DHCP server."""
        url = f"{self.base_url}/dhcp/leases/list"
        params = {"token": self.token}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        self._write_leases(data["response"]["leases"])

    def reserve_leases(self, path="data/reserved-leases.json"):
        """Reserve leases from a JSON file."""
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

    def cleanup_excluded_leases(self, scope_name="Default"):
        """Remove leases that are in excluded ranges."""
        url = f"{self.base_url}/dhcp/scopes/get"
        params = {"token": self.token, "name": scope_name}
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        scope = resp.json()["response"]

        exclusions = []
        for excl in scope.get("exclusions", []):
            start = ipaddress.IPv4Address(excl["startingAddress"])
            end = ipaddress.IPv4Address(excl["endingAddress"])
            exclusions.append((start, end))

        reserved = set()
        for r in scope.get("reservedLeases", []):
            reserved.add(r["address"])

        leases = self.get_leases()

        for lease in leases:
            addr = ipaddress.IPv4Address(lease["address"])
            in_exclusion = any(start <= addr <= end for start, end in exclusions)
            is_reserved = lease["address"] in reserved
            if in_exclusion and not is_reserved:
                remove_params = {
                    "token": self.token,
                    "name": lease.get("scope", scope_name),
                }
                if "hardwareAddress" in lease:
                    remove_params["hardwareAddress"] = lease["hardwareAddress"]
                elif "clientIdentifier" in lease:
                    remove_params["clientIdentifier"] = lease["clientIdentifier"]
                remove_url = f"{self.base_url}/dhcp/leases/remove"
                r = requests.post(remove_url, params=remove_params)
                if r.ok:
                    print(f"Removed lease {lease['address']} ({lease.get('hardwareAddress', lease.get('clientIdentifier'))})")
                else:
                    print(f"Failed to remove lease {lease['address']}: {r.text}")


if __name__ == "__main__":
    client = DhcpClient()
    if len(sys.argv) > 1:
        run_method = sys.argv[1]
        run_args = sys.argv[2:]
        if run_method == "help":
            client.help()

        if run_method == "get_leases":
            client.get_leases()

        elif run_method == "reserve_leases":
            client.reserve_leases()

        elif run_method == "cleanup_excluded_leases":
            scope_name = "Default"
            if len(run_args) > 0:
                scope_name = run_args[0]
            client.cleanup_excluded_leases(scope_name)