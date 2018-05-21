from mininet.cli import CLI
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, info
from mininet.link import TCLink


class MyTopo(Topo):
    "Simple topology example."

    def build(self):
        "Create custom topo."

        # Initialize topology
        # Topo.__init__(self)

        # Add hosts and switches
        host1 = self.addHost('h1', ip="10.0.0.2", defaultRoute="via 10.0.0.1")
        host2 = self.addHost('h2', ip="10.0.0.3", defaultRoute="via 10.0.0.1")
        host3 = self.addHost('h3', ip="10.0.0.4", defaultRoute="via 10.0.0.1")
        host4 = self.addHost('h4', ip="10.0.0.5", defaultRoute="via 10.0.0.1")
        host5 = self.addHost('h5', ip="10.0.0.6", defaultRoute="via 10.0.0.1")

        # host1 = self.addHost('h1')
        # host2 = self.addHost('h2')
        # host3 = self.addHost('h3')

        switch1 = self.addSwitch('s1')

        # Add links
        linkopts = dict(loss=5)

        self.addLink(host1, switch1, **linkopts)
        self.addLink(host2, switch1, **linkopts)
        self.addLink(host3, switch1, **linkopts)
        self.addLink(host4, switch1, **linkopts)
        self.addLink(host5, switch1, **linkopts)


def runNodes(network):
    hosts = network.hosts
    name = 'A'
    for h in hosts:
        h.sendCmd("python3 link_layer.py node" + name + " &")
        h.sendCmd("python3 network_layer.py node" + name + " &")
        h.sendCmd("python3 application_layer.py node" + name)
        name = chr(ord(name)+1)

    results = {}
    for h in hosts:
        results[h.name] = h.waitOutput()


def runNodes2(network):
    hosts = network.hosts
    info(hosts[0].sendCmd("./run.sh nodeA"))
    info(hosts[1].sendCmd("./run.sh nodeB"))
    info(hosts[2].sendCmd("./run.sh nodeC &"))
    info(hosts[3].sendCmd("./run.sh nodeD &"))
    info(hosts[4].sendCmd("./run.sh nodeE &"))

    results = {}
    for h in hosts:
        results[h.name] = h.waitOutput()


topos = {'mytopo': (lambda: MyTopo())}


# if __name__ == '__main__':
#     lg.setLogLevel('info')
#     topo = MyTopo()
#     network = Mininet(topo, link=TCLink)
#     network.start()
#     # network.pingAll()
#     # runNodes(network)
#     CLI(network)
#     network.stop()
