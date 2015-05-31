/*!
 * Ext JS Library 4.0
 * Copyright(c) 2006-2011 Sencha Inc.
 * licensing@sencha.com
 * http://www.sencha.com/license
 */


Ext.define('MyDesktop.ClientWindow', {
    extend: 'Ext.ux.desktop.Module',

    requires: [
        'Ext.data.ArrayStore',
        'Ext.util.Format',
        'Ext.grid.Panel',
        'Ext.grid.RowNumberer',
        'MyDesktop.Utils'
    ],

    id: 'client-win',


    init: function () {
        this.launcher = {
            text: '客户端管理',
            iconCls: 'icon-grid'
        };
    },
    createWindow: function () {
        var desktop = this.app.getDesktop();
        var win = desktop.getWindow('client-win');
        var ActionURL = {list:'/proxy/clients/list',
            add:'/proxy/clients/add',
            update:'/proxy/clients/edit',
            del:'/proxy/clients/del'
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
            fields:["ip", "name", "mask", "comment"]
        });
        
        var submitError =function(form, action){
            Ext.MessageBox.alert('Error', '数据提交失败');
        };

        var delClientHandler = function(obj, e){
            var gd = obj.up("panel").child("grid");
            var sel = gd.selModel.getSelection();
            if(sel.length != 1){
                return;
            }
            var delClient = function(id){
                Ext.Ajax.request({
                    url: ActionURL.del,
                    method: 'POST',
                    params: {id: id},
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
            Ext.MessageBox.confirm('请确认', '删除所选客户端', function(option){
                if(option == 'yes'){
                    delClient(sel[0].data.id);
                }
            });
        };

        var updateClientHandler = function(obj, e){
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
                    updateClientWin = formPanel.up('window');
                    if(form.isValid()){
                        form.submit({
                            method : 'post',
                            success : function(f, a){
                                if(a.result.errorCode == 0){
                                    dataStore.load();
                                    updateClientWin.destroy();
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

            var updateClientForm = Ext.create('Ext.form.Panel', {
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
                        labelWidth:60,
                        width:250
                    },
                    {
                        xtype:'textfield',
                        fieldLabel:'网段名称',
                        id:'nameField',
                        name:'name',
                        msgTarget:'none',
                        labelAlign:'left',
                        value:sel[0].data.name,
                        allowBlank: false,
                        labelWidth:60,
                        width:250
                    },
                    {
                        xtype:'textfield',
                        id:'maskField',
                        fieldLabel:'子网掩码',
                        name:'mask',
                        msgTarget:'none',
                        labelAlign:'left',
                        validator:MyDesktop.Utils.validatMask,
                        value: sel[0].data.mask,
                        labelWidth:60,
                        width:250
                    },
                    {
                        xtype:'textarea',
                        fieldLabel:'备注',
                        name:'comment',
                        msgTarget:'qtip',
                        labelAlign:'left',
                        value: sel[0].data.comment,
                        labelWidth:60,
                        width:250
                    }
                ]
            });

            var updateClientWindow = Ext.create('Ext.window.Window', {
                title: '修改源ip',
                modal : true,
                resizable: false,
                closable: true,
                closeAction: 'destroy',
                width: 350,
                height: 260,
                padding:'10 40 15 40',
                layout: {
                    type: 'fit',
                },
                items: [updateClientForm]
            });
            updateClientWindow.show();
        };

        var addClientHandler = function(obj, e){

            var submitBtn = Ext.create('Ext.button.Button',{
                margin:'0 0 0 75',
                text:'提交',
                handler:function(obj, e){
                    var formPanel = obj.up('form');
                    var form = formPanel.getForm();
                    addClientWin = formPanel.up('window');
                    if(form.isValid()){
                        form.submit({
                            method : 'post',
                            success : function(f, a){
                                if(a.result.errorCode == 0){
                                    dataStore.load();
                                    addClientWin.destroy();
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

            var addClientForm = Ext.create('Ext.form.Panel', {
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
                        labelWidth:60,
                        width:250
                    },
                    {
                        xtype:'textfield',
                        fieldLabel:'网段名称',
                        id:'nameField',
                        name:'name',
                        msgTarget:'none',
                        labelAlign:'left',
                        allowBlank: false,
                        labelWidth:60,
                        width:250
                    },
                    {
                        xtype:'textfield',
                        id:'maskField',
                        fieldLabel:'子网掩码',
                        name:'mask',
                        msgTarget:'none',
                        labelAlign:'left',
                        validator:MyDesktop.Utils.validatMask,
                        labelWidth:60,
                        width:250
                    },
                    {
                        xtype:'textarea',
                        fieldLabel:'备注',
                        name:'comment',
                        msgTarget:'qtip',
                        labelAlign:'left',
                        labelWidth:60,
                        width:250
                    }
                ]
            });

            var addClientWindow = Ext.create('Ext.window.Window', {
                title: '添加源ip',
                modal : true,
                resizable: false,
                closable: true,
                closeAction: 'destroy',
                width: 350,
                height: 260,
                padding:'10 40 15 40',
                layout: {
                    type: 'fit',
                },
                items: [addClientForm]
            });
            addClientWindow.show();
        };

        var clientListGrid = Ext.create('Ext.grid.Panel',{
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
                {text: "网段名称", width: 70, sortable: true, dataIndex: 'name'},
                {text: "子网掩码", width: 70, sortable: true, dataIndex: 'mask'},
                {text: "备注", width: 300, sortable: true, dataIndex: 'comment'}
            ]
        });
        if (!win) {
            dataStore.load();
            win = desktop.createWindow({
                id:'client-win',
                title: '源ip管理',
                width: 650,
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
                items: [clientListGrid],
                tbar: [{
                    text: '添加',
                    iconCls: 'add',
                    handler:addClientHandler
                }, '-', {
                    text: '修改',
                    iconCls: 'option',
                    handler: updateClientHandler
                }, '-', {
                    text: '删除',
                    iconCls: 'remove',
                    handler: delClientHandler
                }]
            });
        }
        return win;
    }
});

