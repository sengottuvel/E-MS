##############################################################################
#
#   This is New Customized Module
#
##############################################################################

{
    'name': 'Department Indent Manual Closing',
    'version': '0.1',
    'author': 'sengottuvelu',
    'category': 'BASE',    
    'depends' : ['base','product','account','purchase','kg_po_manual_closing','kg_depindent',],
    'data': ['kg_depindent_manual_closing.xml'],    
    'auto_install': False,
    'installable': True,
}

