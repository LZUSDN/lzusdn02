
(function () {
    Ext.ns('MyDesktop.Utils');

    var Utils = MyDesktop.Utils = {};
    var str2ipFun = function (str) {
        var REG = /^(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])$/;
        var result = REG.exec(str);
        if (!result) return 0;
        return (parseInt(result[1]) << 24
    			| parseInt(result[2]) << 16
    			| parseInt(result[3]) << 8
    			| parseInt(result[4]));
    };
    Ext.apply(Utils, {
        ip2str: function (ip) {
            return ((ip >> 24) & 0xff)
		            + '.' + ((ip >> 16) & 0xff)
		            + '.' + ((ip >> 8) & 0xff)
		            + '.' + (ip & 0xff);
        },
        str2ip: str2ipFun,
        validatIp: function (value) {
            var ip = str2ipFun(value);
            if (ip == 0) {
                return false;
            }
            return true;
        },
        validatPort: function (value) {
            var port = parseInt(value);
            if (!port) {
                return false;
            } else if (port > 0 && port < 65535) {
                return true;
            }
            return false;
        },
        validatMask: function (value) {
            var mask = parseInt(value);
            if(mask == 0){
                return true;
            } else if(!mask){
                return false;
            } else if(mask < 0){
                return false;
            } else if(mask > 32){
                return false;
            }
            return true;
        }
    });
} ());
