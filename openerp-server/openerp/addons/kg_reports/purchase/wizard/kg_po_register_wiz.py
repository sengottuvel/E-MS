import time
from lxml import etree
from osv import fields, osv
from tools.translate import _
import pooler
import logging
import netsvc
logger = logging.getLogger('server')
from datetime import datetime
from datetime import date
import datetime
	
class kg_po_register_wiz(osv.osv_memory):
		
	_name = 'kg.po.register.wiz'
	_columns = {
		'fis_year': fields.many2one('account.fiscalyear','Fiscal year',readonly=True),
		'product_id':fields.many2many('product.product','kg_po_stm_pro','order_id','product_id','Product Name'),
		'supplier':fields.many2many('res.partner','kg_po_stm_sup','order_id','supplier_id','Supplier'),
		'po_no':fields.many2many('purchase.order','kg_po_stm_pono','order_id','po_no_id','PO No'),
		'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date')], "Filter by", required=True),
		'date_from': fields.date("Start Date"),
		'date_to': fields.date("End Date"),
		'print_date': fields.datetime('Creation Date', readonly=True),
		'printed_by': fields.many2one('res.users','Printed By',readonly=True),
		'status': fields.selection([('approved', 'Approved'),('cancelled','Cancelled'),('pending','Pending')], "Status"),
		'company_id': fields.many2one('res.company', 'Company Name'),
		'user_id': fields.many2one('res.users', 'User ID'),
		
	}
	
	_defaults = {
		
		'filter': 'filter_date', 
		'date_from': time.strftime('%Y-%m-%d'),
		'date_to': time.strftime('%Y-%m-%d'),
		'print_date': fields.datetime.now,
		'printed_by': lambda obj, cr, uid, context: uid,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.pi.detail.wizard', context=c),
	}

	def _get_from_date(self, cr, uid, context=None):
		today = datetime.date.today()
		first = datetime.date(year=today.year,month=today.month,day=1,)
		res = first.strftime('%Y-%m-%d')
		return res
	
	def _get_fis(self, cr, uid, context=None):
		today = date.today()
		fis_obj = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start','<=',today),('date_stop','>=',today)])
		fis_id = self.pool.get('account.fiscalyear').browse(cr,uid,fis_obj[0])
		fisyear_id = fis_id.id
		return fisyear_id
						
	_defaults = {
	
				'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id,
				'company_id':1,
				'date_from': _get_from_date,
				'date_to': fields.date.context_today,
				'fis_year': _get_fis,
				'filter': 'filter_date',
				
				}
		
	def create_report(self, cr, uid, ids, context={}):
		data = self.read(cr,uid,ids,)[-1]
		print data,' create_report('
		return {
			'type'		 : 'ir.actions.report.xml',
			'report_name'   : 'jasper_kg_po_register_report',
			'datas': {
					'model':'kg.po.register.wiz',
					'id': context.get('active_ids') and context.get('active_ids')[0] or False,
					'ids': context.get('active_ids') and context.get('active_ids') or [],
					'report_type':'pdf',
					'form':data
				},
			'nodestroy': False
			}
	
	
		

kg_po_register_wiz()

