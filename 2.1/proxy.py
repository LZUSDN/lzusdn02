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
import logging
import time
import random
import json
import os
from copy import deepcopy
from ryu.base import app_manager
from webob import Response
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.app import wsgi as app_wsgi
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.mac import haddr_to_bin
from ryu.lib.ip import ipv4_to_bin
from ryu.lib.packet import packet, ethernet, ipv4, arp, tcp
from ryu.lib import hub
from ryu.ofproto import ether



class ProxySwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(ProxySwitch, self).__init__(*args, **kwargs)
        self.proxy_priority = 10
        self.nwtp_priority = 8
        self.http_priority = 5
        self.forward_priority = 3

        self.HTTP_PORT = 80
        self.IP_TYPE = 0x0800
        self.TCP_PROTO = 6

        self.mac_to_port = {}
        self.ip_to_mac = {}
        self.pktCheck = {}

        self.clients = []
        self.servers = []

        self.cookie = 13           # cookie for flow modify
        self.idleTimeout = 5       # idle timeout for flow modify
        self.macTimeout = 30       # mac address timeout for forward table
        self.macCheckPeriod = 3    # the period of check forward table
        self.pktThreshold = 0.005  # min time for the same packet
        self.logger.setLevel(logging.INFO)
        self.readConf()
#        self.pktInHandler = [self._learn, self._pktCheck, self._proxy, self._forwarding]
        self.pktInHandler = [self._learn, self._proxy, self._forwarding]
        wsgi = kwargs['wsgi']
        wsgi.register(ProxyRest, {'proxy_app': self})
        
    def readConf(self):
        self.clients.append(ProxyClient(cid=1, ip="202.201.3.98",
                                        mask=32, name="client1",
                                        comment="a http client"))
        self.clients.append(ProxyClient(cid=2, ip="202.201.3.9",
                                        mask=32, name="client2",
                                        comment="another http client"))
        self.servers.append(ProxyServer(sid=1, ip="202.201.3.90",
                                        port=3128, comment="a http proxy"))
        self.servers.append(ProxyServer(sid=2, ip="202.201.3.103",
                                        port=3128, comment="another http proxy"))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(dl_type=0x0800, nw_proto=6, tp_dst=80)
        actions = [datapath.ofproto_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.add_flow(datapath, self.http_priority, match, actions)


    def add_flow(self, datapath, prior, match, actions):
        ofproto = datapath.ofproto
        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=self.cookie,
            command=ofproto.OFPFC_ADD, idle_timeout=self.idleTimeout,
            hard_timeout=0, priority=prior,
            flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
        datapath.send_msg(mod)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        for pktInFun in self.pktInHandler:
            isContinue = pktInFun(ev)
            if not isContinue:
                break

    def _learn(self, ev):
        # learn mac from packet
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.in_port
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid].setdefault(src, in_port)
        nw_pkt = pkt.get_protocol(ipv4.ipv4)
        if nw_pkt:
            self.ip_to_mac.setdefault(dpid, {})
            self.ip_to_mac[dpid].setdefault(nw_pkt.src, src)
        return True

    def _pktCheck(self, ev):
        # check the same packet from one port for loop link
        msg = ev.msg
        datapath = msg.datapath
        dpid = msg.datapath.id
        ofproto = datapath.ofproto
        pkt = packet.Packet(msg.data)
        pktHash = hash(pkt)
        if dpid in self.pktCheck:
            if pktHash in self.pktCheck[dpid]:
                now = time.time()
                lastSeen = self.pktCheck[dpid][pktHash]
                if now - lastSeen < self.pktThreshold:
                    actions = [datapath.ofproto_parser.OFPActionOutput(ofproto.OFPP_NONE)]
                    pktOut = datapath.ofproto_parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port, actions=actions)
                    datapath.send_msg(pktOut)
                    return False
                else:
                    self.pktCheck[dpid][pktHash] = time.time()
                    return True
        else:
            self.pktCheck[dpid] = {}
            self.pktCheck[dpid][pktHash] = time.time()
            return True

    def _proxy(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = msg.datapath.id
        ofproto = datapath.ofproto
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        nw_pkt = pkt.get_protocol(ipv4.ipv4)
        if not nw_pkt:
            return True
        tp_pkt = pkt.get_protocol(tcp.tcp)
        if not tp_pkt:
            return True

        dlsrc = eth.src
        dldst = eth.dst
        nwsrc = nw_pkt.src
        nwdst = nw_pkt.dst
        tpsrc = tp_pkt.src_port
        tpdst = tp_pkt.dst_port

#        print "from %s:%s to %s:%s" % (nwsrc,tpsrc,nwdst,tpdst)
        if tpdst != self.HTTP_PORT:
            return self._nwtp_forwarding(ev)

        checkedClient = False
        for client in self.clients:
            if client.contain(nwsrc):
                checkedClient = True
                break
        if not checkedClient:
            for server in self.servers:
                if nwdst == server.ip and tpdst == server.port:
                    return False
            return True
        server = self._pickServer();
        if not server:
            return True

        if server.ip in self.ip_to_mac[dpid]:
            server.mac = self.ip_to_mac[dpid][server.ip]
            outport = self.mac_to_port[dpid][server.mac]
        else:
            return True

        print "add flow for %s:%s access %s:%s" % (nwsrc,tpsrc,nwdst,tpdst),
        print "and choose the server %s" % server.ip
        # flow for request
        actions = [datapath.ofproto_parser.OFPActionSetDlDst(haddr_to_bin(server.mac)),
                   datapath.ofproto_parser.OFPActionSetNwDst(ipv4_to_int(server.ip)),
                   datapath.ofproto_parser.OFPActionSetTpDst(server.port),
                   datapath.ofproto_parser.OFPActionOutput(outport)]
        match = datapath.ofproto_parser.OFPMatch(dl_src=haddr_to_bin(dlsrc),
                                                 dl_type=self.IP_TYPE,
                                                 nw_src=ipv4_to_int(nwsrc),
                                                 nw_proto=self.TCP_PROTO,
                                                 tp_src=tpsrc)
        self.add_flow(datapath, self.proxy_priority, match, actions)

        # flow for response
        actions2 = [datapath.ofproto_parser.OFPActionSetDlSrc(haddr_to_bin(dldst)),
                   datapath.ofproto_parser.OFPActionSetNwSrc(ipv4_to_int(nwdst)),
                   datapath.ofproto_parser.OFPActionSetTpSrc(tpdst),
                   datapath.ofproto_parser.OFPActionOutput(msg.in_port)]
        match2 = datapath.ofproto_parser.OFPMatch(dl_dst=haddr_to_bin(dlsrc),
                                                  dl_type=self.IP_TYPE,
                                                  nw_dst=ipv4_to_int(nwsrc),
                                                  nw_proto=self.TCP_PROTO,
                                                  tp_dst=tpsrc)
        self.add_flow(datapath, self.proxy_priority, match2, actions2)
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions)
        datapath.send_msg(out)
        return False

    def _nwtp_forwarding(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = msg.datapath.id
        ofproto = datapath.ofproto
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        nw_pkt = pkt.get_protocol(ipv4.ipv4)
        tp_pkt = pkt.get_protocol(tcp.tcp)
        dlsrc = eth.src
        dldst = eth.dst
        nwsrc = nw_pkt.src
        nwdst = nw_pkt.dst
        tpsrc = tp_pkt.src_port
        tpdst = tp_pkt.dst_port
        if not dldst in self.mac_to_port[dpid]:
            return True
        outport = self.mac_to_port[dpid][dldst]
        match = datapath.ofproto_parser.OFPMatch(dl_src=haddr_to_bin(dlsrc),
                                                 dl_dst=haddr_to_bin(dldst),
                                                 dl_type=self.IP_TYPE,
                                                 nw_src=ipv4_to_int(nwsrc),
                                                 nw_dst=ipv4_to_int(nwdst),
                                                 nw_proto=self.TCP_PROTO,
                                                 tp_src=tpsrc,
                                                 tp_dst=tpdst)
        actions = [datapath.ofproto_parser.OFPActionOutput(outport)]
        self.add_flow(datapath, self.nwtp_priority, match, actions)
        return False

    def _forwarding(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.in_port
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        dpid = datapath.id
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD
        actions = [parser.OFPActionOutput(out_port)]
        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, dl_dst=haddr_to_bin(dst))
            self.add_flow(datapath, self.forward_priority, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
        return True

    def _pickServer(self):
        size = len(self.servers)
        if size == 0:
            return False
        r = random.randint(1, 100)
        return self.servers[r%size]

class ProxyClient:
    def __init__(self, cid, ip, mask, name, comment):
        self.cid = cid
        self.ip = ip
        self.mask = mask
        self.name = name
        self.comment = comment

    def __str__(self):
        format = '{"id":%s, "ip":"%s", "mask":%s, "name":"%s", "comment":"%s"}'
        values = (self.cid, ipv4_to_int(self.ip), self.mask, self.name, self.comment)
        return format % values
    def fromMap(self, m):
        self.cid = m['id']
        self.ip = m['ip']
        self.mask = m['mask']
        self.name = m['name']
        self.comment = m['comment']

    def contain(self, ip):
        net1 = ipv4_to_int(self.ip) >> (32-self.mask)
        net2 = ipv4_to_int(ip) >> (32-self.mask)
        if net1 == net2:
            return True
        return False

class ProxyServer:
    def __init__(self, sid, ip, port, comment):
        self.sid = sid
        self.ip = ip
        self.port = port
        self.comment = comment

    def __str__(self):
        format = '{"id":%s, "ip":"%s", "port":%s, "comment":"%s"}'
        values = (self.sid, ipv4_to_int(self.ip), self.port, self.comment)
        return format % values

    def fromMap(self, m):
        self.sid = m['id']
        self.ip = m['ip']
        self.port = m['port']
        self.comment = m['comment']

class ProxyRest(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(ProxyRest, self).__init__(req, link, data, **config)
        self.proxy_app = data['proxy_app']
        self.clients = self.proxy_app.clients
        self.servers = self.proxy_app.servers
        self.errCode = {'success':0, 'illArg':1, 'unkonwn':2}
        self.okRes = {'success':True, 'errorCode':self.errCode['success']}
        self.errRes = {'success':False}
        self.mediaType = {'js':'text/javascript','css':'text/css',
                          'html':'text/html', 'jpg':'image/png',
                          'gif':'image/png','png':'image/png',
                          'default':'text/plain'}

    #client CURD
    @route('proxy', '/proxy/clients/list', methods=['GET'])
    def clientList(self, req, **kwargs):
        res = deepcopy(self.okRes)
        res.setdefault('total', len(self.clients))
        body = str(res)
        body = body[0:-1]
        body = body + ',' + " 'root':"
        body = body + lst_to_str(self.clients) + '}'
        body = body.replace('True', 'true')
        return Response(content_type='application/json', body=body)

    @route('proxy', '/proxy/clients/add', methods=['POST'])
    def clientAdd(self, req, **kwargs):
        cid = get_next_cid(self.clients)
        ip = req.params['ip']
        mask = int(req.params['mask'])
        name = req.params['name']
        comment = req.params['comment']
        newClient = ProxyClient(cid=cid, ip=ip, mask=mask,
                                name=name, comment=comment)
        hasId = False
        for i in xrange(len(self.clients)):
            if self.clients[i].cid == cid:
                hasId = True
                break
        if hasId:
            self.clients[i] = newClient;
        else:
            self.clients.append(newClient)
        res = deepcopy(self.okRes)
        body = str(res)
        body = body.replace('True', 'true')
        return Response(content_type='application/json', body=body)

    @route('proxy', '/proxy/clients/edit', methods=['POST'])
    def clientEdit(self, req, **kwargs):
        cid = int(req.params['id'])
        ip = req.params['ip']
        mask = int(req.params['mask'])
        name = req.params['name']
        comment = req.params['comment']
        newClient = ProxyClient(cid=cid, ip=ip, mask=mask,
                                name=name, comment=comment)
        hasId = False
        for i in xrange(len(self.clients)):
            if self.clients[i].cid == cid:
                hasId = True
                break
        if hasId:
            self.clients[i] = newClient;
        else:
            self.clients.append(newClient)
        res = deepcopy(self.okRes)
        body = str(res)
        body = body.replace('True', 'true')
        return Response(content_type='application/json', body=body)

    @route('proxy', '/proxy/clients/del', methods=['POST'])
    def clientDel(self, req, **kwargs):
        cid = int(req.params['id'])
        delIds = []
        for i in xrange(len(self.clients)):
            if self.clients[i].cid == cid:
                delIds.append(i)

        for i in xrange(len(delIds)-1,-1,-1):
            del self.clients[delIds[i]]

        res = deepcopy(self.okRes)
        body = str(res)
        body = body.replace('True', 'true')
        return Response(content_type='application/json', body=body)

    #server CURD
    @route('proxy', '/proxy/servers/list', methods=['GET'])
    def serverList(self, req, **kwargs):
        res = deepcopy(self.okRes)
        res.setdefault('total', len(self.servers))
        body = str(res).lower()
        body = body[0:-1]
        body = body + ',' + " 'root':"
        body = body + lst_to_str(self.servers) + '}'
        body = body.replace('True', 'true')
        return Response(content_type='application/json', body=body)

    @route('proxy', '/proxy/servers/add', methods=['POST'])
    def serverAdd(self, req, **kwargs):
        sid = get_next_sid(self.servers)
        ip = req.params['ip']
        port = int(req.params['port'])
        comment = req.params['comment']
        newServer = ProxyServer(sid=sid, ip=ip, port=port,
                                comment=comment)
        hasId = False
        for i in xrange(len(self.servers)):
            if self.servers[i].sid == sid:
                hasId = True
                break
        if hasId:
            self.servers[i] = newServer;
        else:
            self.servers.append(newServer)
        res = deepcopy(self.okRes)
        body = str(res)
        body = body.replace('True', 'true')
        return Response(content_type='application/json', body=body)

    @route('proxy', '/proxy/servers/edit', methods=['POST'])
    def serverEdit(self, req, **kwargs):
        sid = int(req.params['id'])
        ip = req.params['ip']
        port = int(req.params['port'])
        comment = req.params['comment']
        newServer = ProxyServer(sid=sid, ip=ip, port=port,
                                comment=comment)
        hasId = False
        for i in xrange(len(self.servers)):
            if self.servers[i].sid == sid:
                hasId = True
                break
        if hasId:
            self.servers[i] = newServer;
        else:
            self.servers.append(newServer)
        res = deepcopy(self.okRes)
        body = str(res)
        body = body.replace('True', 'true')
        return Response(content_type='application/json', body=body)

    @route('proxy', '/proxy/servers/del', methods=['POST'])
    def serverDel(self, req, **kwargs):
        sid = int(req.params['id'])
        delIds = []
        for i in xrange(len(self.servers)):
            if self.servers[i].sid == sid:
                delIds.append(i)

        for i in xrange(len(delIds)-1,-1,-1):
            del self.servers[delIds[i]]

        res = deepcopy(self.okRes)
        body = str(res)
        body = body.replace('True', 'true')
        return Response(content_type='application/json', body=body)

    @route('proxy_ui', '/proxy/ui/{filename:.*}', methods=['GET'])
    def staticFile(self, req, **kwargs):
        basePath = '/home/shang/Development/python/proxy/ui/'
        filename = basePath + kwargs['filename']
        if not os.path.isfile(filename):
            print filename
            return Response(status=404)
        else:
            postfix = filename.lower().split('.')[-1]
            if not postfix in self.mediaType:
                postfix = 'default'
            media = self.mediaType[postfix]
            fh = open(filename, 'rb')
            body = fh.read()
            fh.close()
            body = body.replace('True', 'true')
            return Response(content_type=media, body=body)

def ipv4_to_int(string):
    ip = string.split('.')
    assert len(ip) == 4
    i = 0
    for b in ip:
        b = int(b)
        i = (i << 8) | b
    return i

def lst_to_str(lst):
    res = '['
    for l in lst:
        res = res + str(l) + ','
    res = res[0:-1] + ']'
    return res

def get_next_cid(clients):
    maxid = 0
    for client in clients:
        if client.cid > maxid:
            maxid = client.cid
    return maxid+1

def get_next_sid(servers):
    maxid = 0
    for server in servers:
        if server.sid > maxid:
            maxid = server.sid
    return maxid+1