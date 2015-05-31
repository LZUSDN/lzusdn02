from slldp import slldp
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from slldp import SLLDP_MAC_DST
from slldp import SLLDP_MAC_SRC
from slldp import ETH_TYPE_SLLDP

pkt = packet.Packet()
pkt.add_protocol(ethernet.ethernet(ethertype=ETH_TYPE_SLLDP,
                dst=SLLDP_MAC_DST, src=SLLDP_MAC_SRC))
pkt.add_protocol(slldp(2))
pkt.serialize()
bin_packet = pkt.data

eth, _, buff = ethernet.ethernet.parser(bin_packet)
dpid,buf = slldp.parser(buff)
print eth
print dpid
print len(buf)
