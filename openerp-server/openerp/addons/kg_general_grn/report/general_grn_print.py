import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from datetime import datetime 

class general_grn_print(report_sxw.rml_parse):
	
	def __init__(self, cr, uid, name, context):
		
		super(general_grn_print, self).__init__(cr, uid , name, context=context)
		self.localcontext.update(
				{
				'time': time,
				'get_date_ddmmyyyy': self.get_date_ddmmyyyy, 
		})
	
	def get_date_ddmmyyyy(self, datec):
		return datetime.strptime(datec, "%Y-%m-%d").strftime("%d/%m/%Y") 
	

	
report_sxw.report_sxw('report.general.grn.print','kg.general.grn','addons/kg_general_grn/report/general_grn_print.rml',parser=general_grn_print,header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

