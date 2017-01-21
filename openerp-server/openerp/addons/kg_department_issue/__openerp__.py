
{
    'name': 'KG Department Issue',
    'version': '0.1',
    'author': 'Sangeetha',
    'category': 'Department Issue',
   
    'website': 'http://www.openerp.com',
    'description': """
This module allows you to manage your Item Details.
===========================================================
""",
    'depends' : ['base', 'product','stock','kg_depmaster','kg_outwardmaster','kg_depindent'],
    'data': ['kg_department_issue_view.xml',
			  'dep_issue_report.xml',
            
		
			],
		
    'auto_install': False,
    'installable': True,
}

