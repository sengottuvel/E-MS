##############################################################################
#
#   This is New Customized Pump Model Master
#
##############################################################################

{
    'name': 'Item Ledger View',
    'version': '0.1',
    'author': 'Ramya Kalaiselvan',
    'category': 'BASE',        
    'depends' : ['base','product','stock','kg_menus'],
    'data': [
			'kg_itemview_ledger_view.xml'
			],
    'css': ['static/src/css/state.css'], 
    'auto_install': False,
    'installable': True,
}

