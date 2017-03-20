
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
	
class kg_purchase_invoice_reg_wiz(osv.osv_memory):
		
	_name = 'kg.purchase.invoice.reg.wiz'
	_columns = {
		
		'product_id':fields.many2many('product.product','kg_po_stm_pro','order_id','product_id','Product Name'),
		'supplier':fields.many2many('res.partner','kg_po_stm_sup','order_id','supplier_id','Supplier'),
		
		'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date')], "Filter by", required=True),
		'date_from': fields.date("Start Date"),
		'date_to': fields.date("End Date"),
		'print_date': fields.datetime('Creation Date', readonly=True),
		'printed_by': fields.many2one('res.users','Printed By',readonly=True),
		'status': fields.selection([('approved', 'Approved'),('cancelled','Cancelled')], "Status"),
		'company_id': fields.many2one('res.company', 'Company Name'),
		'invoice_id':fields.many2many('kg.purchase.invoice','kg_inv_temp','order_id','inv_id','Invoice No',domain="[('state','=','approved'),'&',('approved_date','>=',date_from),'&',('approved_date','<=',date_to)]"),
		'invoice_id1':fields.many2many('kg.purchase.invoice','kg_inv_temp1','order_id','inv_id','Invoice No',domain="[('state','=','approved'),'&',('approved_date','>=',date_from),'&',('approved_date','<=',date_to),'&',('payment_type','=',payment_type)]"),
		'voucher_id':fields.many2many('kg.cash.voucher','kg_voucher_temp','order_id','inv_id','Vooucher No',domain="[('state','=','approved'),'&',('approved_date','>=',date_from),'&',('approved_date','<=',date_to)]"),
		#~ 'direct_id':fields.many2many('direct.entry.expense','kg_direct_expense_temp','order_id','inv_id','Direct Expense No',domain="[('state','=','approved'),'&',('approve_date','>=',date_from),'&',('approve_date','<=',date_to)]"),
		#~ 'direct_id1':fields.many2many('direct.entry.expense','kg_direct_expense_temp1','order_id','inv_id','Direct Expense No',domain="[('state','=','approved'),'&',('approve_date','>=',date_from),'&',('approve_date','<=',date_to),'&',('payment_type','=',payment_type)]"),
		'payment_type': fields.selection([('cash', 'Cash'), ('credit', 'Credit')], 'Payment Type',required=False),
	}
	
	_defaults = {
		
		'filter': 'filter_date', 
		'date_from': time.strftime('%Y-%m-%d'),
		'date_to': time.strftime('%Y-%m-%d'),
		'print_date': fields.datetime.now,
		'printed_by': lambda obj, cr, uid, context: uid,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.pi.detail.wizard', context=c),
	}



	def _date_validation_check(self, cr, uid, ids, context=None):
		for val_date in self.browse(cr, uid, ids, context=context):
			
			if val_date.date_from <= val_date.date_to:
				return True
		return False
 
	_constraints = [
		(_date_validation_check, 'You must select an correct Start Date and End Date !!', ['Valid_date']),
	  ]
	  
	  
	def _build_contexts(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		result = {}
		result['date_from'] = 'date_from' in data['form'] and data['form']['date_from'] or False
		result['date_to'] = 'date_to' in data['form'] and data['form']['date_to'] or False
		if data['form']['filter'] == 'filter_date':
			result['date_from'] = data['form']['date_from']
			result['date_to'] = data['form']['date_to']
		return result
		
	def date_indian_format(self,date_pyformat):
		date_contents = date_pyformat.split("-")
		date_indian = date_contents[2]+"/"+date_contents[1]+"/"+date_contents[0]
		return date_indian
	  
	def check_report(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		data = {}
		data['ids'] = context.get('active_ids', [])
		data['model'] = context.get('active_model', 'ir.ui.menu')
		data['form'] = self.read(cr, uid, ids, [])[0]
		used_context = self._build_contexts(cr, uid, ids, data, context=context)
		data['form']['used_context'] = used_context
		return self._print_report(cr, uid, ids, data, context=context)
		
	def pre_print_report(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		data['form'].update(self.read(cr, uid, ids, [], context=context)[0])
		return data
		
	def _print_report(self, cr, uid, ids, data, context=None):
		rec = self.browse(cr,uid,ids[0])
		if context is None:
			context = {}
		data = self.pre_print_report(cr, uid, ids, data, context=context)
		data['form'].update(self.read(cr, uid, ids[0]))
		if data['form']:
			date_from = str(data['form']['date_from'])
			date_to = str(data['form']['date_to'])
			data['form']['date_from_ind'] = self.date_indian_format(date_from)		  
			data['form']['date_to_ind'] = self.date_indian_format(date_to)
			
			company_id = data['form']['company_id'][0]
			com_rec = self.pool.get('res.company').browse(cr,uid, company_id)		   
			if com_rec.name == ' KGiSL IIM Hostel':
				data['form']['company'] = 'KGISL IIM Hostel - Stationery Store'
			else:   
				data['form']['company'] = com_rec.name
			data['form']['company_logo'] = com_rec.logo
			data['form']['printed_by'] = rec.printed_by.name
			
			if data['form']['status'] == 'approved':
				data['form']['status_name'] = 'Approved'
			
			elif data['form']['status'] == 'cancelled':
				data['form']['status_name'] = 'Cancelled'
			else:
				data['form']['status_name'] = ''
			
			if data['form']['payment_type'] == 'cash':
				data['form']['payment'] = 'CASH'
			
			elif data['form']['payment_type'] == 'credit':
				data['form']['payment'] = 'CREDIT'
			else:
				data['form']['payment'] = 'ALL' 
				
			cr_date = datetime.strptime(rec.print_date, '%Y-%m-%d %H:%M:%S')
			date = cr_date.strftime('%d/%m/%Y %H:%M:%S')	
			data['form']['print_date'] = date   
			return {'type': 'ir.actions.report.xml', 'report_name': 'kg.purchase.invoice.register', 'datas': data,  'name': 'Purchase Invoice Register'}
	
	
		

kg_purchase_invoice_reg_wiz()

