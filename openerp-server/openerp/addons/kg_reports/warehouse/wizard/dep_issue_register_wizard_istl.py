import time
from osv import fields, osv
import netsvc
import pooler
from datetime import datetime
from datetime import date
from osv.orm import browse_record, browse_null
from tools.translate import _
import datetime

class dep_issue_register_wizard_istl(osv.osv_memory):
	
	def _get_from_date(self, cr, uid, context=None):
		today = datetime.date.today()
		first = datetime.date(year=today.year,month=today.month,day=1,)
		res = first.strftime('%Y-%m-%d')
		return res		
	
	_name = "dep.issue.register.wizard.istl"
	_description = "Issue Register Wiz"
	
	_columns = {
	
				'fis_year': fields.many2one('account.fiscalyear','Fiscal year',readonly=True),
			#	'account_id': fields.many2one('account.account','Account Name',domain=[('type', '=', 'view')],required=True),
				'user_id': fields.many2one('res.users', 'User ID'),
				'company_id': fields.many2one('res.company', 'Company Name',required=True),
				'from_date': fields.date('From Date'),
				'to_date': fields.date('To Date'),
				'dep_id':fields.many2many('kg.depmaster','dep_issue_register1','wiz_id','dep_id','Department Name'),
				'product':fields.many2many('product.product','dep_issue_product1','product_wiz_id','product_dep_id','Product'),
				'issue_status': fields.selection([('approved', 'Approved'),('cancelled','Cancelled')], "Status"),
				'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date')], "Filter by")
				
			}
	

	
	def _get_fis(self, cr, uid, context=None):
		today = date.today()
		fis_obj = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start','<=',today),('date_stop','>=',today)])
		fis_id = self.pool.get('account.fiscalyear').browse(cr,uid,fis_obj[0])
		fisyear_id = fis_id.id
		return fisyear_id
						
	_defaults = {
	
				'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id,
				'company_id':1,
				'from_date': _get_from_date,
				'to_date': fields.date.context_today,
				'fis_year': _get_fis,
				'filter': 'filter_date',
				
				}
		
	def create_report(self, cr, uid, ids, context={}):
		data = self.read(cr,uid,ids,)[-1]
		print data,' create_report('
		return {
			'type'		 : 'ir.actions.report.xml',
			'report_name'   : 'jasper_kg_dep_issue_report',
			'datas': {
					'model':'dep.issue.register.wizard.istl',
					'id': context.get('active_ids') and context.get('active_ids')[0] or False,
					'ids': context.get('active_ids') and context.get('active_ids') or [],
					'report_type':'pdf',
					'form':data
				},
			'nodestroy': False
			}
	
dep_issue_register_wizard_istl()

