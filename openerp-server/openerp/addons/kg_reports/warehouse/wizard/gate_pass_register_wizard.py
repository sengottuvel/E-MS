
import time
from lxml import etree
from osv import fields, osv
from tools.translate import _
import pooler
import logging
import netsvc
logger = logging.getLogger('server')
import datetime
from datetime import datetime
	
class gate_pass_register_wizard(osv.osv_memory):
		
	_name = 'gate.pass.register.wizard'
	_columns = {
		
		'dep_id':fields.many2one('kg.depmaster','Department Name'),
	
			
		'date_from': fields.date("Start Date"),
		'date_to': fields.date("End Date"),
		'supplier':fields.many2one('res.partner','Supplier',domain="[('supplier','=',True)]"),
		'product':fields.many2one('product.product','Product'),
		
		'status': fields.selection([('done', 'Delivered'),('cancel','Cancelled'),('close','Closed'),('open','Open'),('confirmed','Confirmed'),('pending', 'Pending')], "Status"),
		'out_type': fields.selection([('g-return', 'G-Return'),('service', 'Service'), ('replacement', 'Replacement'), ('rejection', 'Rejection'), ('transfer', 'Transfer')],'Gate Pass Type'),

	}
	
	_defaults = {
		

		'date_from': time.strftime('%Y-%m-%d'),
		'date_to': time.strftime('%Y-%m-%d'),

	}

	def _get_from_date(self, cr, uid, context=None):
		today = date.today()
		fis_obj = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start','<=',today),('date_stop','>=',today)])
		fis_id = self.pool.get('account.fiscalyear').browse(cr,uid,fis_obj[0])
		from_date = fis_id.date_start
		d2 = datetime.strptime(from_date,'%Y-%m-%d')
		res = d2.strftime('%Y-%m-%d')
		
		return res
	
	def _get_fis(self, cr, uid, context=None):
		today = date.today()
		fis_obj = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start','<=',today),('date_stop','>=',today)])
		fis_id = self.pool.get('account.fiscalyear').browse(cr,uid,fis_obj[0])
		fisyear_id = fis_id.id
		return fisyear_id
						
	
		
	def create_report(self, cr, uid, ids, context={}):
		data = self.read(cr,uid,ids,)[-1]
	
		return {
			'type'		 : 'ir.actions.report.xml',
			'report_name'   : 'jasper_kg_gatepass_register',
			'datas': {
					'model':'gate.pass.register.wizard',
					'id': context.get('active_ids') and context.get('active_ids')[0] or False,
					'ids': context.get('active_ids') and context.get('active_ids') or [],
					'report_type':'pdf',
					'form':data
				},
			'nodestroy': False
			}
	

gate_pass_register_wizard()

