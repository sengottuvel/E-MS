import math
import re
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
import openerp.addons.decimal_precision as dp
import netsvc
import datetime
import calendar
from datetime import date
import re
import urllib
import urllib2
import logging
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import calendar
today = datetime.now()
a = datetime.now()
dt_time = a.strftime('%m/%d/%Y %H:%M:%S')

class kg_stock_movement(osv.osv):
	
	_name = 'kg.stock.movement'
	_description = "This form is to track the Stock movement"
	_order = "date desc"
	
	_columns = {
	
		'name':fields.char('No'),
		'date':fields.date('Entry Date'),
		'state': fields.selection([('draft','Draft'),('confirm','WFA'),('approved','Approved'),('reject','Rejected')],'Status', readonly=True),
		'process_type': fields.selection([('excess_sub2main','Excess Return'),('damage_fromsub','Damage Return From SS'),('damage_frommain','Damage Return From MS'),('purchase_frommain','Purchase Return From MS'),('purchase_fromsub','Purchase Return From SS'),('stock_transfer','Stock Transfer'),('gp_frommain','Gate Pass From MS'),('gp_fromsub','Gate Pass From SS')],'Process Type',readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'sub_location':fields.many2one('stock.location','From Sub Store',domain = [('location_type','=','sub'),('state','=','approved')],readonly=True),
		'main_location':fields.many2one('stock.location','Main Store',domain = [('location_type','=','main'),('state','=','approved')],readonly=True),
		'sub_location1':fields.many2one('stock.location','To Sub Store',domain = [('location_type','=','sub'),('state','=','approved')],readonly=True),
		'scrap_location':fields.many2one('stock.location','Scrap Store',domain = [('usage','=','scrap'),('state','=','approved')],readonly=True),
		'supplier_location':fields.many2one('stock.location','Supplier Store',domain = [('usage','=','supplier'),('state','=','approved')],readonly=True),
		'from_location':fields.many2one('stock.location','From Location'),
		'to_location':fields.many2one('stock.location','To Location'),
		'line_ids':fields.one2many('ch.stock.movement','header_id','Stock Activity'),   
		'remark':fields.text('Remarks'),
		
			### Entry Info ###
		'crt_date': fields.datetime('Created Date',readonly=True),
		'user_id': fields.many2one('res.users', 'Created By', readonly=True),
		'confirm_date': fields.datetime('Confirmed Date', readonly=True),
		'confirm_user_id': fields.many2one('res.users', 'Confirmed By', readonly=True),
		'approve_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Approved By', readonly=True),  
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),	
		'active':fields.boolean('Active'),	
		'notes': fields.text('Notes'),
		'cancel_remark': fields.text('Rejection Remarks'),
		'update_date': fields.datetime('Last Updated Date', readonly=True),
		'update_user_id': fields.many2one('res.users', 'Last Updated By', readonly=True),
		
	}
	
	_defaults = {
	
		'active': True,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg_stock_movement', context=c),			
		
		'state': 'draft',
		'date': lambda * a: time.strftime('%Y-%m-%d'),
		'user_id': lambda obj, cr, uid, context: uid,
		'crt_date':lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
	}
	
	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(kg_stock_movement, self).write(cr, uid, ids, vals, context)	
	
	def onchange_location(self, cr, uid, ids, process_type,sub_location,main_location,scrap_location,sub_location1,supplier_location):
		value = {'from_location':False,'to_location':False}
		if process_type == 'excess_sub2main':
			from_location = sub_location 
			to_location = main_location		
			
		elif process_type == 'damage_fromsub':
			from_location = sub_location 
			to_location = scrap_location 
					
		elif process_type == 'damage_frommain':
			from_location = main_location 
			to_location = scrap_location
				
		elif process_type == 'purchase_frommain':
			from_location = main_location 
			to_location = supplier_location 
						
		elif process_type == 'purchase_fromsub':
			from_location = sub_location
			to_location = supplier_location 
						
		elif process_type == 'stock_transfer':
			from_location = sub_location
			to_location = sub_location1			
			
		elif process_type == 'gp_frommain':
			from_location = main_location
			to_location = supplier_location
								
		elif process_type == 'gp_fromsub':
			from_location = sub_location
			to_location = supplier_location
		value = {'from_location':from_location,'to_location':to_location}	
		
		return {'value': value}
		
		
	def load_item(self,cr,uid,ids,context=None):
		rec = self.browse(cr, uid, ids[0])
		lot_obj = self.pool.get('stock.production.lot')
		
		from_location = rec.from_location.id
		to_location = rec.to_location.id
		
		
		## checking stock based on location
		
		for item in rec.line_ids:
			received_qty = 0.00
			pending_qty = 0.00
			product_id = item.product_id.id
			
			out_sql = """ select 
						Sum(case when type = 'in'
						then qty else 0 end) as in_qty,
						Sum(case when type = 'out'
						then qty else 0 end) as out_qty
						from (
						(select sum(product_qty) as qty,'in' as type from stock_move where product_id=%s and state='done' and location_dest_id =%s)
						union
						(select sum(product_qty) as qty ,'out' as type from stock_move where product_id=%s and state='done' and location_id =%s)) as main"""%(product_id,from_location,product_id,from_location)
			cr.execute(out_sql)		 
			out_data = cr.dictfetchall()
			
			if  not out_data:
				diff = 0
				received = 0
			else:
				in_qty = out_data[0]['in_qty'] or 0
				out_qty = out_data[0]['out_qty'] or 0
				diff = in_qty - out_qty
				received = in_qty
			
			received_qty =  received
			pending_qty =   diff
			
				
			if  pending_qty <= 0:
				raise osv.except_osv(
						_('Stock not available for product'),
						_('%s')%(item.product_id.name))   
			if  pending_qty < item.return_qty :
				raise osv.except_osv(
						_('Return qty should not be greater than Available Qty for product'),
						_('%s')%(item.product_id.name))
						
			if 	rec.process_type in ('damage_frommain','purchase_frommain','gp_frommain'):			
				sql = """ select lot_id from m2m_item_return_details where movement_line_id=%s""" %(item.id)
				cr.execute(sql)
				data = cr.dictfetchall()
				if not data:
					raise osv.except_osv(
					_('No GRN Entry !!'),
					_('There is no GRN reference for this transaction. You must associate GRN entries for Product %s.' %(item.product_id.name_template)))
				else:
					val = [d['lot_id'] for d in data if 'lot_id' in d]
					tot = 0.0
					for i in val:
						lot_rec = lot_obj.browse(cr, uid, i)
						tot += lot_rec.pending_qty
					if tot < item.return_qty:
						raise osv.except_osv(
						_('Stock not available !!'),
						_('Associated GRN have less Qty compare to Return Qty for Product %s.' %(item.product_id.name_template)))
					else:
						pass
								
		##  stock checking ends here	
						   	
		self.write(cr, uid, ids, {'state': 'draft','from_location': from_location,'to_location': to_location})
		
		return True
	
	
	def entry_draft(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'draft'})
		return True

	def entry_confirm(self,cr,uid,ids,context=None):
		rec = self.browse(cr, uid, ids[0])
		self.load_item(cr, uid, ids,context=None)
		process_type = rec.process_type
		seq_name = ''
		if not rec.name:
			if process_type == 'excess_sub2main':
				seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.stock.movement')])
				seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
				cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,rec.date))
				
			elif process_type == 'damage_fromsub':
				seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.stock.movement.damage.fromsub')])
				seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
				cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,rec.date))
				
			elif process_type == 'damage_frommain':
				seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.stock.movement.damage.fm')])
				seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
				cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,rec.date))
				
				
			elif process_type == 'purchase_frommain':
				seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.stock.movement.po.frommain')])
				seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
				cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,rec.date))
				
				
			elif process_type == 'purchase_fromsub':
				seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.stock.movement.po.fromsub')])
				seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
				cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,rec.date))
				
			elif process_type == 'stock_transfer':
				seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.stock.movement.stock.transfer')])
				seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
				cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,rec.date))
				
			elif process_type == 'gp_frommain':
				seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.stock.movement.gp.frommain')])
				seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
				cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,rec.date))
				
			elif process_type == 'gp_fromsub':
				seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.stock.movement.gp.fromsub')])
				seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
				cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,rec.date))
			
			seq_name = cr.fetchone();
		
		self.write(cr, uid, ids, {'state': 'confirm','confirm_user_id': uid, 'confirm_date': dt_time,'name':seq_name[0]})
		return True

	def entry_approve(self,cr,uid,ids,context=None):
		rec = self.browse(cr, uid, ids[0])
		self.load_item(cr, uid, ids,context=None)
		lot_obj = self.pool.get('stock.production.lot')
		
		from_location = rec.from_location.id
		to_location = rec.to_location.id
		process_type = rec.process_type
		
		for line in rec.line_ids:
			
			move_type = ''
			lot_updation = ''
			
			if process_type == 'excess_sub2main':
				move_type = 'in'
				lot_updation = 'not_applicable'
				
			elif process_type == 'damage_fromsub':
				move_type = 'out'
				lot_updation = 'not_applicable'
				
			elif process_type == 'damage_frommain':
				move_type = 'out'
				lot_updation = 'applicable'
				
				
			elif process_type == 'purchase_frommain':
				move_type = 'out'
				lot_updation = 'applicable'
				
				
			elif process_type == 'purchase_fromsub':
				move_type = 'out'
				lot_updation = 'not_applicable'
				
			elif process_type == 'stock_transfer':
				move_type = 'out'
				lot_updation = 'not_applicable'
				
			elif process_type == 'gp_frommain':
				move_type = 'out'
				lot_updation = 'applicable'
				
			elif process_type == 'gp_fromsub':
				move_type = 'out'
				lot_updation = 'not_applicable'
				
			## move creation	
				
			form_vals = {
					'date':rec.date,
					'stock_move_id':rec.id,
					'product_id':line.product_id.id,
					'product_uom':line.uom.id,
					'product_uos':line.uom.id,
					'product_qty':line.return_qty,
					'product_uos_qty':line.return_qty,
					'name':line.product_id.name,
					'location_id':from_location,
					'location_dest_id':to_location,
					'state':'done',
					'move_type':move_type,
					'return_id':rec.id,
					'return_line_id':line.id,
					'stock_rate':line.price_unit,
					'price_unit':line.price_unit,
					'stock_uom':line.uom.id,
					'po_to_stock_qty':line.return_qty,
				}
			if form_vals:
				self.pool.get('stock.move').create(cr,uid,form_vals,context=None)
				
			## lot creation		
				
			if move_type == 'in':
				lot_vals = {
					'product_id':line.product_id.id,
					'product_uom':line.uom.id,
					'po_uom':line.uom.id,
					'price_unit':line.price_unit,
					'price_unit':line.price_unit,
					'product_qty':line.return_qty,
					'pending_qty':line.return_qty,
					'issue_qty':line.return_qty,
					'grn_type':'material',
					'lot_type':'in',
					'name':'Return',
					'date':rec.date,
					'grn_no':'Return',
					'batch_no':'Return',
					
				}
				if lot_vals:
					self.pool.get('stock.production.lot').create(cr,uid,lot_vals,context=None)  
			
			## lot updation			
					
			if lot_updation == 'applicable':		
				sql = """ select lot_id from m2m_item_return_details where movement_line_id=%s""" %(line.id)
				cr.execute(sql)
				data = cr.dictfetchall()
				if not data:
					raise osv.except_osv(
					_('No GRN Entry !!'),
					_('There is no GRN reference for this transaction. You must associate GRN entries for Product %s.' %(line.product_id.name_template)))
				else:
					val = [d['lot_id'] for d in data if 'lot_id' in d]
					tot = 0.0
					for i in val:
						lot_rec = lot_obj.browse(cr, uid, i)
						tot += lot_rec.pending_qty
					if tot < line.return_qty:
						raise osv.except_osv(
						_('Stock not available !!'),
						_('Associated GRN have less Qty compare to Return Qty for Product %s.' %(line.product_id.name_template)))
					else:
						pass
					
				
				if data:
					val = [d['lot_id'] for d in data if 'lot_id' in d]
					issue_qty = line.return_qty
					for i in val:
						lot_rec = lot_obj.browse(cr,uid,i)
						move_qty = issue_qty
						if move_qty > 0 and move_qty <= lot_rec.pending_qty:
							lot_pending_qty = lot_rec.pending_qty - move_qty
							lot_rec.write({'pending_qty': lot_pending_qty,'issue_qty': 0.0})
							
							break
						else:
							if move_qty > 0:								
								lot_pending_qty = lot_rec.pending_qty
								remain_qty =  move_qty - lot_pending_qty
								lot_rec.write({'pending_qty': 0.0})
								
							else:
								pass
						
				else:
					pass	
		self.write(cr, uid, ids, {'state': 'approved','app_user_id': uid, 'approve_date': dt_time})
		return True

	def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.cancel_remark:
			self.write(cr, uid, ids, {'state': 'reject','rej_user_id': uid, 'reject_date': dt_time})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter the remarks in rejection remark field !!'))
		return True
		
		
		
	def _check_date(self,cr,uid,ids,context=None):
		read_date = self.read(cr,uid,ids,['crt_date','date'],context=context)
		for t in read_date:
			bk_date = date.today() - timedelta(days=(10))
			back_date = bk_date.strftime('%Y-%m-%d')
			if t['date'] < back_date:
				raise osv.except_osv(
					_('Warning'),
					_('Past date not allowed. Check & change the entry date !!'))
					
			if t['crt_date']<t['date']:
				return False
			else:
				return True
		return True	
		
		
	
	
		
	def _check_lineitem(self, cr, uid, ids, context=None):
		
		indent = self.browse(cr,uid,ids[0])
		if indent.line_ids:
			for line in indent.line_ids:
				
				if line.return_qty <= 0:
					raise osv.except_osv(
					_('Warning'),
					_('Return Qty should be greater than zero for product %s')%(line.product_id.name_template))
		if not indent.line_ids:
			return False
												
		return True
		
	def unlink(self,cr,uid,ids,context=None):
		if context is None:
			context={}
		indent = self.read(cr, uid, ids, ['state'], context=context)
		unlink_ids = []
		for t in indent:
			if t['state'] in ('draft'):
				unlink_ids.append(t['id'])
			else:
				raise osv.except_osv(('Invalid action !'),('System not allow to delete a UN-DRAFT state !!'))
		osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		return True
	
	_constraints = [(_check_date,'Entry date should not be greater than Current date',['']),
					(_check_lineitem,'Please enter the Item Details',['']),
					]
	
	

kg_stock_movement()



class ch_stock_movement(osv.osv):
	_name='ch.stock.movement'
	_description='This is used to track Stock movement'
	
	
	_columns={
	
		'header_id':fields.many2one('kg.stock.movement','Stock Movement No'),
		'product_id':fields.many2one('product.product','Product',domain = [('state','=','approved')]),
		'uom': fields.many2one('product.uom', 'UOM', required=True),
		'qty': fields.float('Received Qty', required=True),
		'pending_qty':fields.float('Available Qty'),
		'return_qty':fields.float('Return Qty'),
		'price_unit':fields.float('Unit Price'),
		'process_type': fields.selection([('excess_sub2main','Excess Return From SS To MS'),('damage_fromsub','Damage Return From SS'),('damage_frommain','Damage Return From MS'),('purchase_frommain','Purchase Return From MS'),('purchase_fromsub','Purchase Return From SS'),('stock_transfer','Stock Transfer'),('gp_frommain','Gate Pass From MS'),('gp_fromsub','Gate Pass From SS')],'Process Type'),
		'from_location':fields.many2one('stock.location','From Location'),
		'to_location':fields.many2one('stock.location','To Location'),
		'kg_grn_moves': fields.many2many('stock.production.lot','m2m_item_return_details','movement_line_id','lot_id', 'GRN Entry',
					domain="[('product_id','=',product_id),'&', ('pending_qty','>',0), '&', ('lot_type','!=','out')]",
					),
		'remark':fields.text('Remarks'),
	
	}   
	
	_defaults = {   
	
	}
	

	
	def default_get(self, cr, uid, fields, context=None):
		return context
	
	def onchange_product_id(self, cr, uid, ids, product_id, uom,process_type,from_location,to_location,context=None):
			
		value = {'uom': '','qty':'','pending_qty':'','price_unit':''}
		
		
		received_qty = 0
		pending_qty = 0
			
		if not from_location or not to_location:
				raise osv.except_osv(
						_('Kindly enter the store details'),
						_(''))		
		else:   	
			out_sql = """ select 
						Sum(case when type = 'in'
						then qty else 0 end) as in_qty,
						Sum(case when type = 'out'
						then qty else 0 end) as out_qty
						from (
						(select sum(product_qty) as qty,'in' as type from stock_move where product_id=%s and state='done' and location_dest_id =%s)
						union
						(select sum(product_qty) as qty ,'out' as type from stock_move where product_id=%s and state='done' and location_id =%s)) as main"""%(product_id,from_location,product_id,from_location)
			cr.execute(out_sql)		 
			out_data = cr.dictfetchall()
		
			if  not out_data:
				diff = 0
				received = 0
			else:
				in_qty = out_data[0]['in_qty'] or 0
				out_qty = out_data[0]['out_qty'] or 0
				diff = in_qty - out_qty
				received = in_qty
				
			
			
			received_qty =  received
			pending_qty =   diff
			
		if  pending_qty <= 0:
			raise osv.except_osv(
					_('Stock not available '),
					_(''))
		
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			price_sql = """ select price_unit as price from stock_move where product_id=%s order by id desc limit 1"""%(product_id)
			cr.execute(price_sql)		   
			price_data = cr.dictfetchall()
			if price_data:
				price = price_data[0]['price'] or 0.00
			else:
				price = 0.00	
			value = {'uom': prod.uom_id.id,'from_location':from_location,'to_location':to_location,'qty':received_qty,'pending_qty':pending_qty,'price_unit':price}
		return {'value': value}
	
	def onchange_qty(self,cr,uid,ids,pending_qty,return_qty,context=None):
		
		if  pending_qty < return_qty :
				raise osv.except_osv(
						_('Return qty should not be greater than Available Qty'),
						_(''))		   	

		return True
		
ch_stock_movement()
