"""Stage 2: the 30-day baselines every event is compared against (PLAN 6.3)."""

import ipaddress
import json

INSIDE = ipaddress.ip_network("10.0.0.0/8")


class Profile:
    def __init__(self, history):
        self.users = history["users"]
        self.service_accounts = history["service_accounts"]
        self.hosts = history["hosts"]

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def is_service(self, name):
        return name in self.service_accounts

    def is_outside(self, address):
        if address in self.hosts:
            return False
        return ipaddress.ip_address(address) not in INSIDE

    def message(self):
        count = len(self.users) + len(self.service_accounts) + len(self.hosts)
        return f"{count} baselines from 30 days"
