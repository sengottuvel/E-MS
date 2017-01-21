
{
    'name': 'KG PO GRN',
    'version': '0.1',
    'author': 'Sangeetha',
    'category': 'GRN Details',
   
    'website': 'http://www.openerp.com',
    'description': """
This module allows you to manage your Item Details.
===========================================================
""",
    'depends' : ['base', 'product','stock','kg_depmaster','kg_service_order','kg_inwardmaster'],
    'data': ['kg_po_grn_view.xml',
			 'kg_po_invoice_wizard.xml',
			 'po_grn_report_view.xml'

            
		
			],
		
    'auto_install': False,
    'installable': True,
}

