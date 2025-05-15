# Usage

To run the available commands, use:

```sh
make run get_leases
# Fetches the current DHCP leases and writes them to `data/leases.json`.
```

```sh
make run reserve_leases
# Adds reserved leases from `data/reserved-leases.json` to the DHCP server.
```

Make sure to set the HOST and API_TOKEN environment variables before running these commands.