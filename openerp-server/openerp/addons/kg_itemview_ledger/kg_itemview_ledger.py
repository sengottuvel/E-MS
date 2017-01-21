from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime
import re
import math
import one2many_sorted
dt_time = time.strftime('%m/%d/%Y %H:%M:%S')
today = time.strftime('%Y-%m-%d')

class kg_itemview_ledger(osv.osv):

	_name = "kg.itemview.ledger"
	_description = "Item Ledger"
	_order = "crt_date desc"
	_columns = {
		'name': fields.text('Name', select=True),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'location_id': fields.many2one('stock.location', 'Location Name', domain="[('location_type','=','main'),('active','=',True),('dummy_state','=','approved')]"),
		'from_date':fields.date('From Date'),
		'to_date':fields.date('To Date'),
		'crt_date': fields.datetime('Created Date',readonly=True),
		'user_id': fields.many2one('res.users', 'Created By', readonly=True),	
		'state': fields.selection([('load','Load'),('draft', 'Draft'),('confirm','Waiting For Approval'),('approved','Approved'),('cancel','Cancel')], 'Status', track_visibility='onchange',states={'draft':[('readonly',False)]}),	
		'product_id': fields.many2one('product.product', 'Product Name', domain="[('state','=','approved')]"),
		'line_ids' : one2many_sorted.one2many_sorted(
			'ch.itemview.ledger.line',
			'header_id',
			'Detail view',
			order='sno desc',
		),
		'uom_id': fields.many2one('product.uom', 'UOM', readonly=True),
		
	}
	
	_defaults = {
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.itemledger', context=c),
		'user_id': lambda obj, cr, uid, context: uid,
		'crt_date':lambda * a: time.strftime('%Y-%m-%d'),
		'state':'load',	
		'name':'/',	
		
	}
	
	def onchange_entry_load(self,cr,uid,ids,location_id,product_id,from_date,to_date,crt_date,context=None):
		if from_date:
			frm_dt = from_date
		else:
			date_str = '2016-03-31'
			formatter_string = "%Y-%m-%d" 
			frm_dt = datetime.strptime('2016-03-31', "%Y-%m-%d" ).date()		
		if to_date:
			to_dt = to_date
		else:
			to_dt = crt_date
		if not product_id:
			raise osv.except_osv(_('Warning!'), _('Please Choose Product!'))
		if location_id:
			cr.execute("""select COALESCE(sum(count),0.00)  as count from (
							select count from 
							(select count(*) from stock_move where location_dest_id = %s and product_id = %s and date::date between '%s'::date and '%s'::date
							union all
							select count(*) from stock_move where location_id = %s and move_type!='cons' and product_id = %s and date::date between '%s'::date and '%s'::date) as sample
							) as sam"""%(location_id,product_id,frm_dt,to_dt,location_id,product_id,frm_dt,to_dt))
			res_data = cr.fetchall();
			if res_data[0][0] <= 0:
				if ids:
					cr.execute('delete from ch_itemview_ledger_line where header_id = %s'%(ids[0]))
					cr.execute('delete from ch_itemview_ledger_details where header_id in (select id from ch_itemview_ledger_line where header_id = %s) '%(ids[0]))
				else:
					line_ids = []
			else:
				pass
		return {'value':{'line_ids':[]}}
		

	def entry_load(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		sql = """delete from ch_itemview_ledger_line where header_id= %s"""%(ids[0])
		cr.execute(sql)		
		if rec.from_date:
			frm_dt = rec.from_date
		else:
			frm_dt = datetime.strptime('2016-03-31', "%Y-%m-%d" ).date()		
		if rec.to_date:
			to_dt = rec.to_date
		else:
			to_dt = rec.crt_date
		if rec.location_id.id:
			cr.execute("""select COALESCE(sum(count),0.00)  as count from (
							select count from 
							(select count(*) from stock_move where location_dest_id = %s and product_id = %s and date::date between '%s'::date and '%s'::date
							union all
							select count(*) from stock_move where location_id = %s and move_type!='cons' and product_id = %s and date::date between '%s'::date and '%s'::date) as sample
							) as sam"""%(rec.location_id.id,rec.product_id.id,frm_dt,to_dt,rec.location_id.id,rec.product_id.id,frm_dt,to_dt))
			res_data = cr.fetchall();
			if res_data[0][0] <= 0:
				raise osv.except_osv(_('Warning'),_('No Record Found'))
			stock_rec = self.pool.get('stock.location').browse(cr,uid,rec.location_id.id)
			if stock_rec:
				if rec.product_id.id and stock_rec.location_type == 'counter' :
					print "FDFDFDFD",ids[0],rec.product_id.id,rec.location_id.id,frm_dt,to_dt
					cr.execute("""select fn_itemview_ledger_counter(%s,%s,%s,'%s'::date,'%s'::date)"""%(ids[0],rec.product_id.id,rec.location_id.id,frm_dt,to_dt))
					data = cr.fetchall();
				if rec.product_id.id and stock_rec.location_type == 'main' :
					cr.execute("""select fn_itemview_ledger_main_store(%s,%s,%s,'%s'::date,'%s'::date)"""%(ids[0],rec.product_id.id,rec.location_id.id,frm_dt,to_dt))
					data = cr.fetchall();
		return True
		
	def onchange_product_id(self,cr,uid,ids,product_id,uom_id,context=None):
		value = {'uom_id':'','location_id':''}
		if product_id:
			pro_rec = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			value = {'uom_id': pro_rec.uom_id.id,'location_id': ''}
		else:
			value = {'uom_id': '','location_id': ''}
		return {'value': value}

	def _check_date(self, cr, uid, ids, context=None):
		for so in self.browse(cr,uid,ids):
			cr.execute("""SELECT CURRENT_DATE;""")
			data = cr.fetchall();
			if not (so.from_date <= data[0][0] and so.to_date <= data[0][0]):
				raise osv.except_osv(_('Warning'),_('From/To Date should be less than or equal to current date!'))
				return False
			if so.from_date > so.to_date:
				raise osv.except_osv(_('Warning'),_('From Date should be less than or equal to To Date!'))
				return False
		return True	

	_constraints = [
	
		(_check_date,'From/To Date Validation !',['order_line']),
	]


kg_itemview_ledger()

class ch_itemview_ledger_line(osv.osv):

	_name = "ch.itemview.ledger.line"
	_description = "Counter Product Lines"
	_order = "sno desc"
	_columns = {
	'header_id': fields.many2one('kg.itemview.ledger', 'Parent'),
	'line_ids' : one2many_sorted.one2many_sorted(
		'ch.itemview.ledger.details',
		'header_id',
		'Detail view',
		order='sno asc',
	),	
	'stock_date': fields.date('Date'),
	'product_id':fields.many2one('product.product','Item Name',required=False),
	'uom': fields.many2one('product.uom', 'UOM', required=False),
	'product_name': fields.char('Product Name', size=128,select=True),
	'trans_type': fields.text('T.Type'),
	'ref_type': fields.text('Ref Type'),
	'dc_no': fields.text('Doc No'),
	'from_to': fields.char('To', size=60,select=True),
	'sno':fields.integer('Sno'),
	'qty':fields.float('Qty',digits=(16,3)),
	'price_unit':fields.float('Price'),	
	'amount':fields.float('Amount'),	
	'cl_stock':fields.float('Closing Stock',digits=(16,3)),	
	'stock_rate':fields.float('Stock Rate'),	
	'stock_value':fields.float('Stock Value'),
	}

ch_itemview_ledger_line()

class ch_itemview_ledger_details(osv.osv):

	_name = "ch.itemview.ledger.details"
	_description = "Counter Product Details"
	_order = "sno desc"
	_columns = {
	'header_id': fields.many2one('ch.itemview.ledger.line', 'Parent'),
	'stock_date': fields.datetime('Date'),
	'product_id':fields.many2one('product.product','Item Name',required=False),
	'pay_mode': fields.char('Payment Mode', size=60,select=True),
	'bill_no': fields.char('Bill No', size=60,select=True),
	'sale_date': fields.char('Bill Date&Time', size=120,select=True),
	'location_id': fields.many2one('product.product','Location Name',required=False),
	'sno':fields.integer('Sno'),
	'qty':fields.float('Qty',digits=(16,3)),
	'price_unit':fields.float('Price'),	
	'amount':fields.float('Amount'),	
	}

ch_itemview_ledger_details()

