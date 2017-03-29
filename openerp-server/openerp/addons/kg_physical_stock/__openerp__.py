##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).

##############################################################################

{
    'name': 'Physical Stock Entry',
    'version': '0.1',
    'author': 'Ramya V',
    'category': 'Warehouse',
   
    'website': 'http://www.openerp.com',
    'description': """
This module allows you to manage your Item Details.
===========================================================
""",
    'depends' : ['base', 'product'],
    'data': ['kg_physical_stock_view.xml',
			'physical_stock_report_view.xml'],
		
    'auto_install': False,
    'installable': True,
}

