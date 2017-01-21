import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from datetime import datetime 

class grn_print(report_sxw.rml_parse):
	
	def __init__(self, cr, uid, name, context):
		
		super(grn_print, self).__init__(cr, uid , name, context=context)
		self.localcontext.update(
				{
				'time': time,
				'get_date_ddmmyyyy': self.get_date_ddmmyyyy, 
		})
	
	def get_date_ddmmyyyy(self, datec):
		return datetime.strptime(datec, "%Y-%m-%d").strftime("%d/%m/%Y") 
	

	
report_sxw.report_sxw('report.grn.print','kg.po.grn','addons/kg_po_grn/report/grn_print.rml',parser=grn_print,header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

