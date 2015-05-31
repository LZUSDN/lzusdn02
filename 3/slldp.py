# Copyright (C) 2012 Nippon Telegraph and Telephone Corporation.
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

import struct
from ryu.lib.packet import packet_base

SLLDP_MAC_DST = '01:80:c2:00:00:0b'
SLLDP_MAC_SRC = '00:00:00:00:00:00'
ETH_TYPE_SLLDP = 0x88cb

class slldp(packet_base.PacketBase):


    _PACK_STR = '!Q'
    _MIN_LEN = struct.calcsize(_PACK_STR)

    def __init__(self, dpid):
        super(slldp, self).__init__()
        self.dpid = dpid

    @classmethod
    def parser(cls, buf):
        dpid, = struct.unpack_from(cls._PACK_STR, buf)
        return (dpid, buf[slldp._MIN_LEN:],)

    def serialize(self, payload, prev):
        return struct.pack(slldp._PACK_STR, self.dpid)