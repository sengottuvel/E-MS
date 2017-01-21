from datetime import *
from datetime import datetime
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta
import time
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
today = datetime.now()


class kg_production_order(osv.osv):
	
	_name = "kg.production.order"
	_columns = {
	
		'order_lines': fields.one2many('ch.production.order.line', 'header_id', 'Order Lines', readonly=True,required=True),
		'name': fields.char('No'),
		'date':fields.date('Date',readonly=True),
		'creation_date':fields.datetime('Created Date',readonly=True),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'user_id': fields.many2one('res.users', 'Created By', readonly=True),
		'approve_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Approved By', readonly=True),
		'confirm_date': fields.datetime('Confirmed Date', readonly=True),
		'conf_user_id': fields.many2one('res.users', 'Confirmed By', readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'state': fields.selection([('draft','Draft'),('confirm','WFA'),('approved','Approved'),
				('reject','Rejected')],'Status', readonly=True),
		'notes': fields.text('Notes'),
		'remark': fields.text('Approve/Reject',readonly=False),
		'updated_date': fields.datetime('Last Updated Date',readonly=True),
		'updated_by': fields.many2one('res.users','Last Updated By',readonly=True),		
		'active': fields.boolean('Active'),


	}
	
	_defaults = {
	
		'state' : 'draft',
		'active' : True,
		'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'date': fields.date.context_today,
		'user_id': lambda obj, cr, uid, context: uid,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.segment', context=c),
		
	}
	
	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_by':uid})
		return super(kg_production_order, self).write(cr, uid, ids, vals, context)	
	
	def entry_confirm(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		lis = []
		if rec.order_lines:
			for i in rec.order_lines:
				lis.append(i.product_id.id)
			for j in lis:
				po_sql = """ select * from mrp_bom_line where bom_id = (select id from mrp_bom where product_id = %d and state = 'approved') """%(j)
				cr.execute(po_sql)		
				po_data = cr.dictfetchall()
				if po_data:
					pass
				else:
					raise osv.except_osv(_('Invalid Action !!'),
					_('The product name must have a Bill of Materials !!'))				
		if rec.order_lines:
			pass
		else:
			raise osv.except_osv(_('Invalid Action !!'),
				_('Please add the line details !!'))
		seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.production.order')])
		seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
		cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,rec.date))
		seq_name = cr.fetchone();
		self.write(cr, uid, ids, {'state': 'confirm','name': seq_name[0],'conf_user_id': uid, 'confirm_date': time.strftime('%Y-%m-%d %H:%M:%S')})   
		return True

	def entry_approve(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		lis = []
		if rec.order_lines:
			for i in rec.order_lines:
				lis.append(i.product_id.id)
			for j in lis:
				po_sql = """ select * from mrp_bom_line where bom_id = (select id from mrp_bom where product_id = %d and state = 'approved') """%(j)
				cr.execute(po_sql)		
				po_data = cr.dictfetchall()
				if po_data:
					for k in po_data:
						po_qty = """ select qty from ch_production_order_line where header_id = %d and product_id = %d """%(rec.id,j)
						cr.execute(po_qty)		
						po_data_qty = cr.dictfetchall()	
						for l in po_data_qty:
							kg_depindent_id=self.pool.get('kg.depindent')
							kg_depindent_line=self.pool.get('kg.depindent.line')
							indent_ids = kg_depindent_id.create(cr,uid,{'dep_name':72,'indent_type':'production','state':'draft','dest_location_id': 277,'src_location_id': 47})
							kg_depindent_line.create(cr,uid,
							{
							'indent_id':indent_ids,
							'product_id':k['product_id'],
							'uom':k['product_uom'],
							'po_uom':k['product_uom'],
							'qty':k['product_qty'] * int(l['qty']),
							'issue_pending_qty':k['product_qty'] * int(l['qty']),
							'pending_qty':k['product_qty'] * int(l['qty']),
							'po_qty':k['product_qty'] * int(l['qty']),
							})	
				else:
					raise osv.except_osv(_('Invalid Action !!'),
					_('The product name must have a Bill of Materials !!'))		
		self.write(cr, uid, ids, {'state': 'approved','app_user_id': uid, 'approve_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		return True
		
	def entry_draft(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'draft'})
		return True
		
	def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.remark:
			self.write(cr, uid, ids, {'state': 'reject','rej_user_id': uid, 'reject_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
		return True

	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []		
		for rec in self.browse(cr,uid,ids):	
			if rec.state != 'draft':			
				raise osv.except_osv(_('Warning!'),
						_('You can not delete this entry !!'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
	
kg_production_order()


class ch_production_order_line(osv.osv):
	
	_name = "ch.production.order.line"
	_description = "Ch Production Order Line"
	
	_columns = {

	'header_id': fields.many2one('kg.production.order', 'Production Order Line',ondelete='cascade', required=True),
	'product_id': fields.many2one('product.product', 'Product', required=True,domain="[('state','=','approved'),('categ_id','in',('Finishedgoods'))]"),
	'uom': fields.many2one('product.uom', 'UOM', required=True,domain="[('dummy_state','=','approved')]"),
	'qty': fields.float('Order Qty', required=True),
	'remarks': fields.text('Remarks'),
	
	}
	
	
	def onchange_product_id(self, cr, uid, ids, product_id, uom, context=None):
		value = {'uom': ''}
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			value = {'uom': prod.uom_id.id}
		return {'value': value}
		
		
	def _check_qty(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.qty <= 0.00:
			return False					
		return True
		
	_constraints = [
		(_check_qty,'You cannot save with zero qty !',['WO Qty']),
		
		]		
		
				
	
ch_production_order_line()	




	

