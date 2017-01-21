##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).

##############################################################################
{
    'name': 'KG_QUOTATION',
    'version': '0.1',
    'author': 'Ramya Kalaiselvan',
    'category': 'Kg_Quotation',
    'website': 'http://www.openerp.com',
    'depends' : ['base', 'product', 'purchase','purchase_requisition','kg_purchase_indent'],
    'data': ['kg_quotation_view.xml',
			],
	#'css': ['static/src/css/state.css'],
    'auto_install': False,
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

