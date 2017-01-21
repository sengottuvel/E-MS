{
    'name': 'Stock Movement',
    'version': '0.1',
    'author': 'Manjula',
    'category': 'Item Details',
   
    'website': 'http://www.openerp.com',
    'description': """
This module allows you to track the stock movement activity.
===========================================================
""",
    'depends' : ['base', 'product','stock'],
    'data': [
	     'kg_stock_movement_view.xml',
		
			],
			

	
    'auto_install': False,
    'installable': True,
}
