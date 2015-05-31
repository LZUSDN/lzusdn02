# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
#from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib import hub
from ryu.lib.dpid import dpid_to_str
from ryu.lib.dpid import str_to_dpid
from ryu.topology import event
from kazoo.client import KazooClient
import abc
import json
from kazoo.recipe.watchers import DataWatch
from ryu.ofproto.ofproto_v1_3 import OFPCR_ROLE_EQUAL
from ryu.ofproto.ofproto_v1_3 import OFPCR_ROLE_MASTER
from ryu.ofproto.ofproto_v1_3 import OFPCR_ROLE_SLAVE
from uuid import uuid4
import random
from slldp import slldp
from slldp import SLLDP_MAC_DST
from slldp import SLLDP_MAC_SRC
from slldp import ETH_TYPE_SLLDP
import time

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.zkConf = {'root':'/multicontroller', 'topo':'/topology',
                       'swstat':'/swstat', 'counter': '/counter'}
        self.zk = KazooClient('127.0.0.1:2181')
        self.zk.start()
        self.ip = '202.201.3.51'
        self.sws = {}
        self.gid = random.randint(0, 10000)
        self.dps = {}
        self.links = []
        self.interval = 5
        self.role = OFPCR_ROLE_EQUAL
        self.topoThread = hub.spawn(self._topoThread)
        self.linkThread = hub.spawn(self._linkDiscover)
        self.clearLinkThread = hub.spawn(self._cleanLinks)
        self.clearLinkThread = hub.spawn(self._cleanSwitches)

    def _cleanSwitches(self):
        while  True:
            self.sws = {k:self.sws[k] for k in self.sws if self.sws[k]}
            hub.sleep(self.interval)

    def _topoThread(self):
        linkNode = self.zkConf['root'] + self.zkConf['topo'] + self.ip
        if self.zk.exists(linkNode):
            self.zk.set(linkNode, json.dumps(self.links))
        else:
            self.zk.create(linkNode, json.dumps(self.links))
        hub.sleep(self.interval)

    def _linkDiscover(self):
        while True:
            for dpid in self.dps:
                self.sendSlldp(dpid)
            hub.sleep(self.interval)

    def sendSlldp(self, dpid):
        dp = self.dps.get(dpid)
        if dp is None:
            return
        actions = [dp.ofproto_parser.OFPActionOutput(dp.ofproto.OFPP_FLOOD)]
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=ETH_TYPE_SLLDP,
                        dst=SLLDP_MAC_DST, src=SLLDP_MAC_SRC))
        pkt.add_protocol(slldp(dp.id))
        pkt.serialize()
        slldpPacket = pkt.data
        out = dp.ofproto_parser.OFPPacketOut(
            datapath=dp, in_port=dp.ofproto.OFPP_CONTROLLER,
            buffer_id=dp.ofproto.OFP_NO_BUFFER, actions=actions,
            data=slldpPacket)
        dp.send_msg(out)

    def getLinks(self):
        topoNode = self.zkConf['root'] + self.zkConf['topo']
        ips = self.zk.get_children(topoNode)
        res = []
        for ip in ips:
            links = self.zk.get(topoNode + ip)[0]
            for link in links:
                res.append(link)
        return res

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):

        msg = ev.msg
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst

        # SLLDP packet
        if dst == SLLDP_MAC_DST:
            self.handleSlldp(ev)
            return
        # process packet_in message in subclass
        self.packet_in_process(ev)

    def handleSlldp(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        inPort = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        slldpBuff = pkt.get_protocols(ethernet.ethernet)[2]
        dpidSrc, _ = slldp.parser(slldpBuff)
        self.links.append({'srcdpid': dpidSrc,
            'dst': {'dpid': dpid, 'port': inPort},
            'time': time.time()})

    def _cleanLinks(self):
        while True:
            now = time.time()
            self.links = [l for l in self.links if now - l['time'] < self.interval]
            hub.sleep(self.interval)

    @abc.abstractmethod
    def packet_in_process(self, ev):
        pass

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter(self, ev):
        dpid = ev.datapath.id
        self.sws[dpid] = True
        self.dps[dpid] = ev.datapath
        dpNode = self.zkConf['root'] + self.zkConf['swstat'] \
                + '/' + dpid_to_str(dpid)
        self.zk.ensure_path(dpNode)
        if self.election(dpid):
            self.role = OFPCR_ROLE_MASTER
        else:
            self.role = OFPCR_ROLE_SLAVE
        self.countUp(dpid)
        self.roleRequest(dpid, self.role)
        mflag = dpNode + '/' + 'master'
        DataWatch(self.zk, mflag, self.masterWatcher)

    def masterWatcher(self, data, stat, ev):
        if ev and ev.type == 'DELETED':
            _, _, dpid, _ = ev.path.split('/')
            dpid = str_to_dpid(dpid)
            if self.sws.get(dpid):
                if self.election(dpid):
                    self.role = OFPCR_ROLE_MASTER
                    self.roleRequest(dpid, self.role)
            return self.sws.get(dpid)

    def election(self, dpid):
        dpNode = self.zkConf['root'] + self.zkConf['swstat'] \
                + '/' + dpid_to_str(dpid)
        mflag = dpNode + '/' + 'master'
        while not self.zk.exists(mflag):
            mlock = self.zk.Lock(dpNode + '/' + 'mlock', self.ip)
            with mlock:
                if not self.zk.exists(mflag):
                    self.zk.create(mflag, self.ip, ephemeral=True)
            if self.zk.exists(mflag):
                if self.zk.get(mflag) == self.ip:
                    return True
                else:
                    return False
            else:
                time.sleep(random.randint(0, 100)/500.0)
        return False

    def roleRequest(self, dp, role):
        msg = dp.ofproto_parser.OFPRoleRequest(dp, role, self.gid)
        dp.send_msg(msg)

    def getCount(self, dpid):
        dpNode =  self.zkConf['root'] + self.zkConf['swstat'] \
                + '/' + dpid_to_str(dpid)
        countNode = dpNode + self.zkConf['counter']
        counters = self.zk.get_children(countNode)
        return len(counters)

    def countUp(self, dpid):
        countNode = self.zkConf['root'] + self.zkConf['swstat'] \
                + '/' + dpid_to_str(dpid) + self.zkConf['counter']
        self.zk.ensure_path(countNode)
        self.zk.create(countNode+uuid4().hex, 'alive', ephemeral=True)

    @set_ev_cls(event.EventSwitchLeave)
    def switch_levave(self, ev):
        dpid = ev.datapath
        count = self.getCount(dpid)
        self.sws[dpid] = False
        if count == 0:
            dpNode =  self.zkConf['root'] + self.zkConf['swstat'] \
                    + '/' + dpid_to_str(dpid)
        self.zk.delete(dpNode, recursive=True)