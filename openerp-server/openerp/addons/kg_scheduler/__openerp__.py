##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).

##############################################################################
{
    'name': 'KG_scheduler',
    'version': '0.1',
    'author': 'Dinesh',
    'category': 'scheduler',
    'images': [''],
    'website': 'http://www.openerp.com',
    'description': """
This Module is for running all schedulers
""",
    'depends' : ['base'],
    'data': ['kg_scheduler_view.xml'],
    'auto_install': False,
    'installable': True,
}

