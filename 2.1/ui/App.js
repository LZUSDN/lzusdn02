/*!
 * Ext JS Library 4.0
 * Copyright(c) 2006-2011 Sencha Inc.
 * licensing@sencha.com
 * http://www.sencha.com/license
 */

Ext.define('MyDesktop.App', {
    extend: 'Ext.ux.desktop.App',

    requires: [
        'Ext.window.MessageBox',
        'Ext.ux.desktop.ShortcutModel',
        'MyDesktop.ProxyWindow',
        'MyDesktop.ClientWindow',
        'MyDesktop.AboutWindow',
    ],

    init: function() {
        this.callParent();
    },

    getModules : function(){
        return [
            new MyDesktop.ProxyWindow(),
            new MyDesktop.ClientWindow(),
            new MyDesktop.AboutWindow()
        ];
    },

    getDesktopConfig: function () {
        var me = this, ret = me.callParent();

        return Ext.apply(ret, {
            //cls: 'ux-desktop-black'
            shortcuts: Ext.create('Ext.data.Store', {
                model: 'Ext.ux.desktop.ShortcutModel',
                data: [
                    { name: '代理管理', iconCls: 'grid-shortcut', module: 'proxy-win' },
                    { name: '客户端管理', iconCls: 'grid-shortcut', module: 'client-win' },
                    { name: '关于', iconCls: 'accordion-shortcut', module: 'bogus-win' }
                ]
            }),

            wallpaper: 'wallpapers/woodDesk.jpg',
            wallpaperStretch: true
        });
    },

    // config for the start menu
    getStartConfig : function() {
        var me = this, ret = me.callParent();

        return Ext.apply(ret, {
            title: 'SDN',
            iconCls: 'user',
            height: 300,
            toolConfig: {
                width: 100,
                items: [
                    {
                        text:'退出系统',
                        iconCls:'logout',
                        handler: me.onLogout,
                        scope: me
                    }
                ]
            }
        });
    },

    getTaskbarConfig: function () {
        var ret = this.callParent();
        return Ext.apply(ret, {
        });
    },

    onLogout: function () {
        Ext.Msg.confirm('Logout', 'Are you sure you want to logout?');
    },
});
