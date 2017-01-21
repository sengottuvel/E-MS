{
    'name': 'kg_production_order',
    'version': '0.1',
    'author': 'Dinesh kumar',
    'category': 'kg_production_order',
    'website': 'http://www.openerp.com',
    'description': """
This module allows you to manage your Production requirements based on Bill Of Materials master
""",
    'depends' : ['base','product','mrp'],
    'data': ['kg_production_order_view.xml'],
    'auto_install': False,
    'installable': True,
}

