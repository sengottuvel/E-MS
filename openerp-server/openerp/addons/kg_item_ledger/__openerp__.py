
{
    'name': 'KG Item Ledger View',
    'version': '0.1',
    'author': 'sengottuvel',
    'category': 'Item Details',
   
    'website': 'http://www.openerp.com',
    'description': """
This module allows you to manage your Item Details.
===========================================================
""",
    'depends' : ['base', 'product','stock'],
    'data': ['kg_item_ledger_view.xml',
		
			],
    'auto_install': False,
    'installable': True,
}

