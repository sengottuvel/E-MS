import time
from osv import fields, osv
import netsvc
import pooler
from osv.orm import browse_record, browse_null
from tools.translate import _
import datetime as lastdate
from datetime import date
import calendar
from datetime import datetime
from datetime import timedelta
import datetime

	
class grn_register_report_wizard(osv.osv_memory):
	
	def _get_from_date(self, cr, uid, context=None):
		today = date.today()
		first = datetime.date(year=today.year,month=today.month,day=1,)
		res = first.strftime('%Y-%m-%d')
		return res		
		
	_name = 'grn.register.report.wizard'
	_columns = {
		
		'supplier':fields.many2many('res.partner','grn_register_supplier','grn_id','supplier_id','Supplier',domain="[('supplier','=',True),('sup_state','=','approved')]"),
		'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date')], "Filter by", required=True),
		'product_type': fields.selection([('consu', 'Consumable Items'),('cap','Capital Goods'),('service','Service Items')], 
					'Product Type'),
	    
	    #'product':fields.many2many('product.product','purchase_requisition_line','product_id','Product','Product'),
	    'product':fields.many2many('product.product','wizard_id','product_id','grn_product_map','Product',domain="[('state','=','approved')]"),				
		'date_from': fields.date("Start Date"),
		'date_to': fields.date("End Date"),
		'company_id': fields.many2one('res.company', 'Company Name'),
		'print_date': fields.datetime('Creation Date', readonly=True),
		'printed_by': fields.many2one('res.users','Printed By',readonly=True),
		'status': fields.selection([('done', 'Approved'),('inv', 'Invoiced'),('cancel','Cancelled')], "Status"),
		'inward_type': fields.many2one('kg.inwardmaster', 'Inward Type',domain="[('state','=','approved')]"),
		'inward_type1': fields.char('Inward Type'),

	}
	
	_defaults = {
		
		'filter': 'filter_date', 
		'date_from': _get_from_date,
		'date_to': time.strftime('%Y-%m-%d'),
		'print_date': fields.datetime.now,
		'printed_by': lambda obj, cr, uid, context: uid,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'grn.register.report.wizard', context=c),
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
		print "_build_contexts data ^^^^^^^^^^^^^^^^^^^^^^^^", data
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
		print "data..................,,,,,,,,,,,,,,", data
		data['form'].update(self.read(cr, uid, ids[0]))
		if data['form']:
			date_from = str(data['form']['date_from'])
			date_to = str(data['form']['date_to'])
			data['form']['date_from_ind'] = self.date_indian_format(date_from)			
			data['form']['date_to_ind'] = self.date_indian_format(date_to)
			
			company_id = data['form']['company_id'][0]
			
			com_rec = self.pool.get('res.company').browse(cr,uid, company_id)			
				
			data['form']['company'] = com_rec.name
			data['form']['printed_by'] = rec.printed_by.name
			
			
			if data['form']['supplier']:
						
				data['form']['supplier_id'] = 'Limited'
			else:
				data['form']['supplier_id'] = 'All'	
			
			
			if data['form']['inward_type']:
				inward_type = data['form']['inward_type'][0]
				inw_rec = self.pool.get('kg.inwardmaster').browse(cr,uid, inward_type)		
				data['form']['inward_type1'] = inw_rec.name
			else:
				data['form']['inward_type1'] = 'All'	
			
			if data['form']['status'] == 'approved':
				data['form']['status_name'] = 'Approved'
			
			elif data['form']['status'] == 'cancelled':
				data['form']['status_name'] = 'Cancelled'
				
			elif data['form']['status'] == 'inv':
				data['form']['status_name'] = 'Invoiced'
			else:
				data['form']['status_name'] = ''
		
			cr_date = datetime.datetime.strptime(rec.print_date, '%Y-%m-%d %H:%M:%S')
			date = cr_date.strftime('%d/%m/%Y %H:%M:%S')	
			data['form']['print_date'] = date	
			return {'type': 'ir.actions.report.xml', 'report_name': 'grn.register.report', 'datas': data,  'name': 'GRN Register'}	
		

grn_register_report_wizard()

