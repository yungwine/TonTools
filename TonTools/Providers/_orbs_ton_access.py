"""ORBS TON ACCESS PART BY @arterialist"""


import time
from typing import List, Set, Optional
import random
import requests

STALE_PERIOD = 10 * 60 * 1000  # 10 Min


class Nodes:
    committee: Set[str]
    topology: List[dict]
    node_index: int
    init_time: int

    def __init__(self):
        self.node_index = -1
        self.committee = set()
        self.topology = []
        self.init_time = 0

    def init(self, nodes_url: str):
        self.node_index = -1
        self.committee.clear()
        self.topology = []
        self.init_time = int(time.time() * 1000)

        try:
            response = requests.get(nodes_url)
            response.raise_for_status()
            data = response.json()
            topology = data
        except Exception as e:
            raise ValueError(f"exception in fetch({nodes_url}): {e}")

        # remove unhealthy nodes
        for node in topology:
            if node["Healthy"] == "1":
                self.topology.append(node)

        if len(self.topology) == 0:
            raise ValueError("no healthy nodes retrieved")

    def get_healthy_for(self, protonet: str) -> List[dict]:
        res = []
        stale_count = 0
        for node in self.topology:
            stale = self.init_time - node["Mngr"]["successTS"] > STALE_PERIOD
            if not stale and node["Weight"] > 0 and node["Mngr"]["health"].get(protonet, False):
                res.append(node)
            elif stale:
                stale_count += 1

        if stale_count == len(self.topology):
            raise ValueError("all nodes manager's data are stale")

        return res


class Access:
    nodes: Nodes
    host: str
    url_version: int

    def __init__(self):
        self.host = "ton.access.orbs.network"
        self.url_version = 1
        self.nodes = Nodes()

    def init(self):
        self.nodes.init(f"https://{self.host}/mngr/nodes?npm_version=2.3.1")

    @staticmethod
    def make_protonet(edge_protocol: str, network: str) -> str:
        res = ""
        if edge_protocol == "toncenter-api-v2":
            res += "v2-"
        elif edge_protocol == "ton-api-v4":
            res += "v4-"
        res += network
        return res

    @staticmethod
    def weighted_random(nodes: List[dict]) -> Optional[dict]:
        sum_weights = sum(node["Weight"] for node in nodes)
        rnd = random.randint(0, sum_weights - 1)

        cur = 0
        for node in nodes:
            if cur <= rnd < cur + node["Weight"]:
                return node
            cur += node["Weight"]
        return None

    def build_urls(
            self,
            network: str = "mainnet",
            edge_protocol: str = "toncenter-api-v2",
            suffix: str = "",
            single: bool = False
    ) -> List[str]:
        if not suffix:
            suffix = ""
        if not edge_protocol:
            edge_protocol = "toncenter-api-v2"
        if not network:
            network = "mainnet"

        suffix = suffix.lstrip("/")

        res = []
        protonet = self.make_protonet(edge_protocol, network)
        healthy_nodes = self.nodes.get_healthy_for(protonet)
        if not healthy_nodes:
            raise ValueError(f"no healthy nodes for {protonet}")

        if single and healthy_nodes:
            chosen = self.weighted_random(healthy_nodes)
            if not chosen:
                raise ValueError("weighted_random returned empty")
            healthy_nodes = [chosen]

        for node in healthy_nodes:
            url = f"https://{self.host}/{node['NodeId']}/{self.url_version}/{network}/{edge_protocol}/"
            if suffix:
                url += f"{suffix}"
            res.append(url)
        return res


def get_endpoints(
        network: str = "mainnet",
        edge_protocol: str = "toncenter-api-v2",
        suffix: str = "",
        single: bool = False
) -> List[str]:
    access = Access()
    access.init()
    return access.build_urls(network, edge_protocol, suffix, single)


def get_http_endpoints(config: dict = None, single: bool = False) -> List[str]:
    network = config.get("network") if config and config.get("network") else "mainnet"
    suffix = "jsonRPC" if not config or config.get("protocol") != "rest" else ""
    return get_endpoints(network, "toncenter-api-v2", suffix, single)


def get_http_endpoint(config: dict = None) -> str:
    endpoints = get_http_endpoints(config, True)
    return endpoints[0]
