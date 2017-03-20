##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).

##############################################################################
{
    'name': 'KG_Reports',
    'version': '0.1',
    'author': ' ',
    'website': 'http://www.openerp.com',
    'description': """
The module contains all Reports of the project
""",
    'depends' : ['base', 'product', 'purchase','purchase_requisition','kg_purchase_invoice'],
    'data': [
		'warehouse/wizard/grn_register_report_wizard.xml',
		'warehouse/wizard/dep_issue_register_wizard_istl.xml',
		'warehouse/wizard/main_closing_stock_wizard.xml',
		'warehouse/wizard/gate_pass_register_wizard.xml',
		'purchase/wizard/kg_po_register_wiz.xml',
		'purchase/wizard/kg_so_register_wiz.xml',
		'purchase/wizard/kg_purchase_invoice_reg_wiz.xml',

			],
    'auto_install': False,
    'installable': True,
}

