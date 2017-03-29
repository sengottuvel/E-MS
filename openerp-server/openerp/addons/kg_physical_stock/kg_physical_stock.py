import math
import re
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import openerp.addons.decimal_precision as dp

dt_time = time.strftime('%m/%d/%Y %H:%M:%S')

class kg_physical_stock(osv.osv):
	
	_name = "kg.physical.stock"
	_description = "Physical Stock"
	_order = "date desc"
	
	_columns = {
		
		## Basic Info
		
		'name': fields.char('Issue Return No', size=64, readonly=True),
		'date': fields.date('Issue Return Date',readonly=True,states={'draft':[('readonly',False)]}),
		'remark': fields.text('Remarks',readonly=False,states={'cancel':[('readonly',True)]}),
		'state': fields.selection([('load','Load'),('draft', 'Draft'),('confirm','WFA'),('approved','Approved'),('cancel','Cancel')], 'Status', track_visibility='onchange',states={'draft':[('readonly',False)]}),
		
		## Module Requirement Info
		
		'load': fields.boolean('Load'),
		'stock_type': fields.selection([('main','Main'),('sale', 'Sale')], 'Stock Type',readonly=True),
		'categ_id': fields.many2many('product.category','m2m_ps_pc','header_id','category_id', 'Category',readonly=True,states={'load':[('readonly',False)]}),
		'product_type': fields.selection([('raw','Foundry Raw Materials'),('ms','MS Item'),('bot','BOT'),('consu', 'Consumables'),('capital','Capitals and Asset'),('service','Service Items'),('coupling','Coupling'),('mechanical_seal','Mechanical Seal')], 'Product Type',readonly=True,states={'load':[('readonly',False)]}),
		
		## Child Tables Declaration
		
		'stock_line': fields.one2many('kg.physical.stock.line', 'stock_pid',
					'Physical Stock Lines',readonly=True,states={'draft':[('readonly',False)]}),
		
		# Entry Info
		
		'active': fields.boolean('Active'),
		'company_id':fields.many2one('res.company','Company',readonly=True),
		'user_id' : fields.many2one('res.users', 'Created By', readonly=True),
		'creation_date':fields.datetime('Created Date',readonly=True),
		'confirmed_by' : fields.many2one('res.users', 'Confirmed By', readonly=True,select=True),
		'confirmed_date': fields.datetime('Confirmed Date', readonly=True),
		'approved_by' : fields.many2one('res.users', 'Approved By', readonly=True,select=True),
		'approved_date': fields.datetime('Approved Date', readonly=True),
		'update_date': fields.datetime('Last Updated Date', readonly=True),
		'update_user_id': fields.many2one('res.users', 'Last Updated By', readonly=True),
		
	}
	
	_sql_constraints = [('code_uniq','unique(name)', 'Indent number must be unique!')]
	
	_defaults = {
		
		'state' : 'load',
		'active' : 'True',
		'load' : True,
		'date' : lambda * a: time.strftime('%Y-%m-%d'),
		'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
		'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'company_id' : lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.physical.stock', context=c),
		'stock_type': 'main',
		
	}
	
	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'update_date':dt_time,'update_user_id':uid})
		return super(kg_physical_stock, self).write(cr, uid, ids, vals, context)
	
	def load_stock(self, cr, uid, ids,context=None):
		rec  = self.browse(cr,uid,ids[0])
		if rec.state == 'load':
			cr.execute('''delete from kg_physical_stock_line where stock_pid = %s '''%(rec.id))
					
			"""
			draft_amends=self.search(cr,uid,[('date','=',rec.date)])
			if len(draft_amends) > 1:
				raise osv.except_osv(_('Physical stock has been already done'),
					_('for this Date')) 
			"""
			product_type = []
			categ_id = []
			
			print"if rec.product_type:if rec.product_type:",rec.product_type
			
			if rec.product_type:
				product_type.append("pp.product_type = '%s' "%rec.product_type)
			
			if rec.categ_id:
				for item in rec.categ_id:
					categ_id.append("pt.categ_id = %s"%(item.id))
			
			if product_type:
				product_type = ' and '+' or '.join(product_type)
			else:
				product_type = ''
			
			if categ_id:
				categ_id = 'and ('+' or '.join(categ_id)
				categ_id =  categ_id+')'
			else:
				categ_id = ''
			
			cr.execute('''	SELECT 
					distinct spl.product_id as in_pro_id,
					brand.name as brand,
					spl.product_uom as uom,
					pp.type as purpose,
					pp.name_template as product,
					sum(pending_qty) as in_qty
					
					FROM stock_production_lot spl
					
					left JOIN product_product pp ON (pp.id=spl.product_id)
					JOIN product_template pt ON (pt.id=pp.product_tmpl_id)
					left JOIN kg_brand_master brand ON (brand.id=spl.brand_id)
					
					where spl.pending_qty > 0 and spl.lot_type = 'in' 
					
					''' + product_type + categ_id + '''
					
					group by spl.product_id,brand.name,spl.product_uom,pp.type,pp.name_template ''',)
			data = cr.dictfetchall()
			data.sort(key=lambda data: data['product'])
			
			self.write(cr, uid, ids, {'state':'draft','stock_type':'main'})
			
			for item in data:
				
				line_vals = {
				'product_id':item['in_pro_id'],
				'brand':item['brand'] or '',
				'uom':item['uom'],
				'qty':item['in_qty'],
				'physical_stock':item['in_qty'],
				'stock_pid':rec.id,
				
				}
				if line_vals:
					common_line = self.pool.get('kg.physical.stock.line').create(cr,uid,line_vals,context=None)
		
		return True
	
	def load_sale_stock(self, cr, uid, ids,context=None):
		#rec  = self.browse(cr,uid,ids[0])
		sql = """delete from kg_physical_stock where state='load'"""
		cr.execute(sql)		
		
		"""
		draft_amends=self.search(cr,uid,[('date','=',rec.date)])
		if len(draft_amends) > 1:
			raise osv.except_osv(_('Physical stock has been already done'),
				_('for this Date')) 
		"""		
		
		vals={
			'stock_type':'sale',
			'state':'draft',
			
			}
		
		stock = self.pool.get('kg.physical.stock').create(cr,uid,vals,context=None)	
		
		sql="""select a_product_id,
				
				pp.name_template as product,
				uom.id as uom,
				bm.name as brand,
				CASE WHEN (a_prod_qty - b_prod_qty) is NULL THEN (round(a_prod_qty::numeric, 2)) ELSE (round((a_prod_qty - b_prod_qty)::numeric, 2)) END as close_qty
				
				from

				(select a.product_id as a_product_id,a.product_uom as a_uom,sum(a.product_qty) as a_prod_qty,a.location_dest_id as a_location,
				a.brand_id as a_brand 
				from stock_move a where a.move_type='out' and a.state='done'
				group by a.product_id,a.location_dest_id,a.product_uom,a.brand_id) as query1
				left outer join
				(select b_product_id,b_prod_qty from
				(select b.product_id as b_product_id,sum(b.product_qty) as b_prod_qty
				from stock_move b where b.move_type='cons' and b.state='done'
				group by b.product_id ) as query2) as query2 on query2.b_product_id = query1.a_product_id
				left join stock_location loc on (loc.id = query1.a_location)
				left join product_product pp on (pp.id = query1.a_product_id)
				left join kg_brand_master bm on (bm.id = query1.a_brand)
				left join product_uom uom on (uom.id = query1.a_uom)
				where loc.name = 'Sales location'"""
		cr.execute(sql)
		data = cr.dictfetchall()		
		data.sort(key=lambda data: data['product'])
		
		for item in data:
			
			line_vals = {
			'product_id':item['a_product_id'],
			'brand':item['brand'] or '',
			'uom':item['uom'],
			'qty':item['close_qty'],
			'physical_stock':item['close_qty'],
			'stock_pid':stock,
			
			}
			if line_vals:
				common_line = self.pool.get('kg.physical.stock.line').create(cr,uid,line_vals,context=None)
				
		#self.write(cr,uid,ids[0],{'state':'draft'})		
		return True	
	
	def confirm_stock(self, cr, uid, ids,context=None):
		rec  = self.browse(cr,uid,ids[0])
		if rec.state == 'draft':
			if not rec.stock_line:
				raise osv.except_osv(_('Warning'),
					_('Line item cannot be empty'))
			self.write(cr,uid,ids,{'state':'confirm',
								   'confirmed_by':uid,
								   'confirmed_date':dt_time,
				})	
		return True
	
	def approve_stock(self, cr, uid, ids,context=None):
		rec  = self.browse(cr,uid,ids[0])
		if rec.state == 'confirm':
			self.write(cr,uid,ids,{'state':'approved','approved_by':uid,'approved_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		return True
	
	def cancel_stock(self, cr, uid, ids, context=None):
		rec  = self.browse(cr,uid,ids[0])
		if rec.state == 'approved':
			if not rec.remark:
				raise osv.except_osv(_('Invalid action !'), _('Enter remarks to cancel!!'))
			self.write(cr, uid,ids,{'state':'cancel'})
		return True
	
	#~ def unlink(self, cr, uid, ids, context=None):
		#~ if context is None:
			#~ context = {}
		#~ indent = self.read(cr, uid, ids, ['state'], context=context)
		#~ unlink_ids = []
		#~ for t in indent:
			#~ if t['state'] in ('draft'):
				#~ unlink_ids.append(t['id'])
			#~ else:
				#~ raise osv.except_osv(_('Invalid action !'), _('System not allow to delete a UN-DRAFT state Department Indent!!'))
		#~ indent_lines_to_del = self.pool.get('kg.physical.stock.line').search(cr, uid, [('stock_line','in',unlink_ids)])
		#~ self.pool.get('kg.physical.stock.line').unlink(cr, uid, indent_lines_to_del)
		#~ osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		#~ return True
	
	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []		
		for rec in self.browse(cr,uid,ids):	
			if rec.state != 'draft':			
				raise osv.except_osv(_('Warning!'),
					_('You can not delete this entry !!'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		
	def _check_lineitem(self, cr, uid, ids, context=None):
		for si in self.browse(cr,uid,ids):
			if si.issue_return_line==[] or si.issue_return_line:
				tot = 0.0
				for line in si.issue_return_line:
					tot += line.qty
				if tot <= 0.0:			
					return False
			return True
	
	#_constraints = [
		
		#(_check_lineitem, 'You can not save this Service Indent with out Line and Zero Qty  !!',['qty']),
		
		#]	
	
kg_physical_stock()

class kg_physical_stock_line(osv.osv):
	
	_name = "kg.physical.stock.line"
	_description = "Issue Return Line"
	
	def onchange_product_id(self, cr, uid, ids, product_id, uom,context=None):
		value = {'uom': ''}
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			value = {'uom': prod.uom_id.id}
		return {'value': value}
	
	_columns = {
		
		## Basic Info
		
		'stock_pid': fields.many2one('kg.physical.stock', 'Stock No', required=True, ondelete='cascade'),
		
		## Module Requirement Fields
		
		'product_id': fields.many2one('product.product', 'Product', required=False),
		'uom': fields.many2one('product.uom', 'UOM', required=False),
		#'brand_id': fields.many2one('kg.brand.master', 'Brand', required=True),
		'brand': fields.char('Brand'),
		'qty': fields.float('Current Stock', required=True),
		'physical_stock':fields.float('Physical Stock Qty'),
		'diff_qty':fields.float('Diff Qty'),
		'note': fields.text('Remarks'),	
		'line_state': fields.selection([('process','Processing'),('noprocess','NoProcess'),('pi_done','PI-Done'),('done','Done')], 'Status'),
		'line_date': fields.date('Indent Date'),
		'price_unit':fields.float('Unit Price'),
		
	}
	
	_defaults = {
		
		'line_date' : lambda * a: time.strftime('%Y-%m-%d'),
		
	}

kg_physical_stock_line()	
