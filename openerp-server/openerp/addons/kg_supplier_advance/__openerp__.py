##############################################################################
#
#   Standard Transaction Module
#
##############################################################################

{

    'name': 'Supplier Advance',
    'version': '0.1',
    'author': 'Karthikeyan.S',    
    'depends' : ['base','purchase','kg_service_order'],
    'data': [
    
			'kg_supplier_advance_view.xml',
			'sequence_data.xml',
			'onscreen_report_data.xml',
			
			],
			
    'css': ['static/src/css/state.css'], 
    'auto_install': False,
    'installable': True,
    
}

