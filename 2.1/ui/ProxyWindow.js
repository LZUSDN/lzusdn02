/*!
 * Ext JS Library 4.0
 * Copyright(c) 2006-2011 Sencha Inc.
 * licensing@sencha.com
 * http://www.sencha.com/license
 */


Ext.define('MyDesktop.ProxyWindow', {
    extend: 'Ext.ux.desktop.Module',

    requires: [
        'Ext.data.ArrayStore',
        'Ext.util.Format',
        'Ext.grid.Panel',
        'Ext.grid.RowNumberer',
        'MyDesktop.Utils'
    ],

    id: 'proxy-win',


    init: function () {
        this.launcher = {
            text: '代理管理',
            iconCls: 'icon-grid'
        };
    },
    createWindow: function () {
        var desktop = this.app.getDesktop();
        var win = desktop.getWindow('proxy-win');
        var ActionURL = {list:'/proxy/servers/list',
            add:'/proxy/servers/add',
            update:'/proxy/servers/edit',
            del:'/proxy/servers/del'
        };
        var dataStore = new Ext.data.ArrayStore({
            pageSize:10,
            proxy: {
                type: 'ajax',
                url: ActionURL.list,
                reader: {
                    type: 'json',
                    root: 'root'
                }
            },
            fields:["ip","port","comment"]
        });
        
        var submitError =function(form, action){
            Ext.MessageBox.alert('Error', '数据提交失败');
        };

        var delProxyHandler = function(obj, e){
            var gd = obj.up("panel").child("grid");
            var sel = gd.selModel.getSelection();
            if(sel.length != 1){
                return;
            }
            var delProxyItem = function(proxyId){
                Ext.Ajax.request({
                    url: ActionURL.del,
                    method: 'POST',
                    params: {id: proxyId},
                    success: function(response, opts) {
                        var res = Ext.decode(response.responseText);
                        if(res.errorCode == 0){
                            dataStore.load();
                            return;
                        }
                        submitError();
                    },
                    failure: function(response, opts) {
                        submitError();
                    }
                });               
            }
            Ext.MessageBox.confirm('请确认', '删除所选代理服务器', function(option){
                if(option == 'yes'){
                    delProxyItem(sel[0].data.id);
                }
            });
        };

        var updateProxyHandler = function(obj, e){
            var gd = obj.up("panel").child("grid");
            var sel = gd.selModel.getSelection();
            if(sel.length != 1){
                return;
            }
            var submitBtn = Ext.create('Ext.button.Button',{
                margin:'0 0 0 75',
                text:'提交',
                handler:function(obj, e){
                    var formPanel = obj.up('form');
                    var form = formPanel.getForm();
                    updateProxyWin = formPanel.up('window');
                    if(form.isValid()){
                        form.submit({
                            method : 'post',
                            success : function(f, a){
                                if(a.result.errorCode == 0){
                                    dataStore.load();
                                    updateProxyWin.destroy();
                                    return;
                                }
                                submitError(f, a);
                            },
                            failure : function(f, a){
                                submitError(f, a);
                            }
                        });
                    }
                }
            });

            var cancelBtn = Ext.create('Ext.button.Button',{
                margin:'0 0 0 50',
                text:'取消',
                handler:function(obj, e){
                    obj.up('window').destroy();
                }
            });

            var updateProxyForm = Ext.create('Ext.form.Panel', {
                url: ActionURL.update, 
                bbar:[submitBtn,cancelBtn],
                items:[
                    {
                        xtype:'hiddenfield',
                        name:'id',
                        allowBlank: false,
                        value:sel[0].data.id
                    },
                    {
                        xtype:'textfield',
                        fieldLabel:'ip地址',
                        id:'ipField',
                        name:'ip',
                        msgTarget:'none',
                        labelAlign:'left',
                        validator:MyDesktop.Utils.validatIp,
                        value:MyDesktop.Utils.ip2str(sel[0].data.ip),
                        allowBlank: false,
                        labelWidth:50,
                        width:250
                    },
                    {
                        xtype:'textfield',
                        id:'portField',
                        fieldLabel:'端口',
                        name:'port',
                        msgTarget:'none',
                        labelAlign:'left',
                        validator:MyDesktop.Utils.validatPort,
                        value: sel[0].data.port,
                        labelWidth:50,
                        width:250
                    },
                    {
                        xtype:'textarea',
                        fieldLabel:'备注',
                        name:'comment',
                        msgTarget:'qtip',
                        labelAlign:'left',
                        value: sel[0].data.comment,
                        labelWidth:50,
                        width:250
                    }
                ]
            });

            var updateProxyWindow = Ext.create('Ext.window.Window', {
                title: '修改代理服务器',
                modal : true,
                resizable: false,
                closable: true,
                closeAction: 'destroy',
                width: 350,
                height: 250,
                padding:'10 40 15 40',
                layout: {
                    type: 'fit',
                },
                items: [updateProxyForm]
            });
            updateProxyWindow.show();
        };

        var addProxyHandler = function(obj, e){

            var submitBtn = Ext.create('Ext.button.Button',{
                margin:'0 0 0 75',
                text:'提交',
                handler:function(obj, e){
                    var formPanel = obj.up('form');
                    var form = formPanel.getForm();
                    addProxyWin = formPanel.up('window');
                    if(form.isValid()){
                        form.submit({
                            method : 'post',
                            success : function(f, a){
                                if(a.result.errorCode == 0){
                                    dataStore.load();
                                    addProxyWin.destroy();
                                    return;
                                }
                                submitError(f, a);
                            },
                            failure : function(f, a){
                                submitError(f, a);
                            }
                        });
                    }
                }
            });

            var cancelBtn = Ext.create('Ext.button.Button',{
                margin:'0 0 0 50',
                text:'取消',
                handler:function(obj, e){
                    obj.up('window').destroy();
                }
            });

            var addProxyForm = Ext.create('Ext.form.Panel', {
                url: ActionURL.add, 
                bbar:[submitBtn,cancelBtn],
                items:[
                    {
                        xtype:'textfield',
                        fieldLabel:'ip地址',
                        id:'ipField',
                        name:'ip',
                        msgTarget:'none',
                        labelAlign:'left',
                        validator:MyDesktop.Utils.validatIp,
                        allowBlank: false,
                        labelWidth:50,
                        width:250
                    },
                    {
                        xtype:'textfield',
                        id:'portField',
                        fieldLabel:'端口',
                        name:'port',
                        msgTarget:'none',
                        labelAlign:'left',
                        validator:MyDesktop.Utils.validatPort,
                        value:80,
                        labelWidth:50,
                        width:250
                    },
                    {
                        xtype:'textarea',
                        fieldLabel:'备注',
                        name:'comment',
                        msgTarget:'qtip',
                        labelAlign:'left',
                        labelWidth:50,
                        width:250
                    }
                ]
            });

            var addProxyWindow = Ext.create('Ext.window.Window', {
                title: '添加代理服务器',
                modal : true,
                resizable: false,
                closable: true,
                closeAction: 'destroy',
                width: 350,
                height: 250,
                padding:'10 40 15 40',
                layout: {
                    type: 'fit',
                },
                items: [addProxyForm]
            });
            addProxyWindow.show();
        };

        var proxyListGrid = Ext.create('Ext.grid.Panel',{
            border: false,
            xtype: 'grid',
            selType: "checkboxmodel",
            selModel: {
                checkOnly: false,
                mode: "SINGLE",
            },
            store: dataStore,
            columns: [
                {text: "IP地址", width:140,sortable: true, dataIndex: 'ip', renderer: MyDesktop.Utils.ip2str},
                {text: "端口号", width: 70, sortable: true, dataIndex: 'port'},
                {text: "备注", width: 300, sortable: true, dataIndex: 'comment'}
            ]
        });
        if (!win) {
            dataStore.load();
            win = desktop.createWindow({
                id:'proxy-win',
                title: '代理管理',
                width: 600,
                height: 400,
                iconCls: 'icon-grid',
                animCollapse: false,
                constrainHeader: true,
                layout: 'fit',
                bbar: Ext.create('Ext.PagingToolbar', {
                    store: dataStore,
                    displayInfo: true,
                    displayMsg: 'Displaying items {0} - {1} of {2}',
                    emptyMsg: "没有相关记录",
                }),
                items: [proxyListGrid],
                tbar: [{
                    text: '添加',
                    iconCls: 'add',
                    handler:addProxyHandler
                }, '-', {
                    text: '修改',
                    iconCls: 'option',
                    handler: updateProxyHandler
                }, '-', {
                    text: '删除',
                    iconCls: 'remove',
                    handler: delProxyHandler
                }]
            });
        }
        return win;
    }
});