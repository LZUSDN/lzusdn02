/*!
* Ext JS Library 4.0
* Copyright(c) 2006-2011 Sencha Inc.
* licensing@sencha.com
* http://www.sencha.com/license
*/

var windowIndex = 0;

Ext.define('MyDesktop.AboutWindow', {
    extend: 'Ext.ux.desktop.Module',
    id: 'bogus-win',
    init : function(){
        this.launcher = {
            text: 'about',
            iconCls:'bogus',
            handler : this.createWindow,
            scope: this,
        }
    },

    createWindow : function(src){
        var desktop = this.app.getDesktop();
        var win = desktop.getWindow('bogus-win');
        if(!win){
            win = desktop.createWindow({
                id: 'bogus-win',
                title:'about',
                width:320,
                height:240,
                html : '<p style=" text-align:center; margin:60px auto;font-size:18px">兰州大学SDN大赛复赛作品</p>',
                iconCls: 'bogus',
                animCollapse:false,
                constrainHeader:true
            });
        }
        win.show();
        return win;
    }
});