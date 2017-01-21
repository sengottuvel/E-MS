from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
import openerp.addons.decimal_precision as dp
import netsvc
import time
import openerp.exceptions
import datetime
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re
from operator import itemgetter
from itertools import groupby
from datetime import datetime
a = datetime.now()
dt_time = a.strftime('%m/%d/%Y %H:%M:%S')
from openerp import netsvc
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import logging

class kg_bom(osv.osv):
	
	_name = 'mrp.bom'	
	_inherit = 'mrp.bom'
	
	def _get_modify(self, cr, uid, ids, field_name, arg,  context=None):
		res={}
		if field_name == 'modify':
			for h in self.browse(cr, uid, ids, context=None):
				res[h.id] = 'no'
				if h.state == 'approved':
					sql_chk = """ SELECT tc.table_schema, tc.constraint_name, tc.table_name, kcu.column_name, ccu.table_name
					AS foreign_table_name, ccu.column_name AS foreign_column_name
					FROM information_schema.table_constraints tc
					JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
					JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
					WHERE constraint_type = 'FOREIGN KEY'
					AND ccu.table_name='mrp_bom' and tc.table_name not in ('mrp_bom_line')  """
					cr.execute(sql_chk)
					data = cr.dictfetchall()	
					if data:
						for var in data:
							data = var
							chk_sql = 'Select COALESCE(count(*),0) as cnt from '+str(data['table_name'])+' where '+data['column_name']+' = '+str(ids[0]) 
							cr.execute(chk_sql)			
							out_data = cr.dictfetchone()
							if out_data:
								if out_data['cnt'] > 0:
									res[h.id] = 'no'
									return res
								else:
									res[h.id] = 'yes'
				else:
					res[h.id] = 'no'
		return res		
	
	_columns = {
		
		'product_id': fields.many2one('product.product', 'Product', required=True, domain="[('purchase_ok','=',True),('state','=','approved'),('categ_id','in',('Finishedgoods'))]"),
		'mrp_bom_line':fields.one2many('mrp.bom.line','bom_id','BOM Line'),
		'expiry_date':fields.date('Expiry Date'),
		'creation_date':fields.datetime('Created Date',readonly=True),
		'active':fields.boolean('Active'),
		#newly added
		'user_id': fields.many2one('res.users', 'Created By', readonly=True),
		'approve_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Approved By', readonly=True),
		'confirm_date': fields.datetime('Confirmed Date', readonly=True),
		'conf_user_id': fields.many2one('res.users', 'Confirmed By', readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),

		#notes
		'notes': fields.text('Notes'),
		'remarks': fields.text('Approve/Reject',readonly=False),
		'modify': fields.function(_get_modify, string='Modify', method=True, type='char', size=3),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'updated_date': fields.datetime('Last Updated Date',readonly=True),
		'updated_by': fields.many2one('res.users','Last Updated By',readonly=True),		
	}
	
	_defaults = {
	  
	  'state':'draft',
	  'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
	  'active': True,
	  'modify': 'no',
	  'user_id': lambda obj, cr, uid, context: uid,
	  'copy_flag' : False, 
	  
	}
	
	def copy_bom(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])		
		mrp_bom_line_obj = self.pool.get('mrp.bom.line')
		cr.execute(""" delete from mrp_bom_line where bom_id  = %s """ %(ids[0]))
		for bom_line_item in rec.source_bom.mrp_bom_line:	
			vals = {
				'bom_id' : ids[0]
				}			
			copy_rec = mrp_bom_line_obj.copy(cr, uid, bom_line_item.id,vals, context) 		
		return True
	
	
#unlink
	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []		
		for rec in self.browse(cr,uid,ids):	
			if rec.state != 'draft':			
				raise osv.except_osv(_('Warning!'),
						_('You can not delete this entry !!'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		
	#write
	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_by':uid})
		return super(kg_bom, self).write(cr, uid, ids, vals, context)
			
	#entry cancel
	def entry_cancel(self,cr,uid,ids,context=None):
		a = datetime.now()
		dt_time = a.strftime('%m/%d/%Y %H:%M:%S')			
		rec = self.browse(cr,uid,ids[0])
		if rec.cancel_remark:
			self.write(cr, uid, ids, {'state': 'cancel','cancel_user_id': uid, 'cancel_date': dt_time})
		else:
			raise osv.except_osv(_('Cancel remark is must !!'),
				_('Enter the remarks in Cancel remarks field !!'))
		return True
		
		#entry draft
	def entry_draft(self,cr,uid,ids,context=None):
		a = datetime.now()
		dt_time = a.strftime('%m/%d/%Y %H:%M:%S')		
		self.write(cr, uid, ids, {'state': 'draft','updated_by':uid,'updated_date': dt_time})
		return True	
			
	#ENTRY CONFIRM
	def entry_confirm(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.mrp_bom_line:
			b = datetime.now()		
			d_time = b.strftime('%m/%d/%Y %H:%M:%S')				
			self.write(cr, uid, ids, {'state': 'confirm','conf_user_id': uid, 'confirm_date': d_time})
		else:
			raise osv.except_osv(_('Warning!!'),
				_('Please add the line items !!'))
		return True
		
	#ENTRY APPROVE
	def entry_approve(self,cr,uid,ids,context=None):
		b = datetime.now()		
		d_time = b.strftime('%m/%d/%Y %H:%M:%S')				
		self.write(cr, uid, ids, {'state': 'approved','app_user_id': uid, 'approve_date': d_time})
		return True
		
	#ENTRY REJECT
	def entry_reject(self,cr,uid,ids,context=None):
		b = datetime.now()		
		d_time = b.strftime('%m/%d/%Y %H:%M:%S')				
		rec = self.browse(cr,uid,ids[0])
		if rec.remarks:
			self.write(cr, uid, ids, {'state': 'reject','rej_user_id': uid, 'reject_date': d_time})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
		return True

	
kg_bom()



class kg_bom_line(osv.osv):
	
	_name = 'mrp.bom.line'
	
	_columns = {
		
		'bom_id':fields.many2one('mrp.bom','BOM Entry'),
		'product_id': fields.many2one('product.product', 'Product', required=True, domain="[('purchase_ok','=',True),('state','=','approved'),('categ_id','not in',('Finishedgoods'))]"),
		'product_qty': fields.float('Product Quantity', required=True, digits_compute=dp.get_precision('Product Unit of Measure')),
		'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control"),
		'department_id':fields.many2one('kg.depmaster','Department Name',required=True,domain=[('state','=','approved')]),
		'state':fields.selection([('draft','Draft'),('approve','Approved')],'Status'),
	}
	
	
	_defaults = {
	
	'state':'draft',
	  
	}
	
	def onchange_uom_id(self, cr, uid, ids, product_id, context=None):
		value = {'product_uom': ''}
		if product_id:
			pro_rec = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			value = {'product_uom': pro_rec.uom_id.id}
		return {'value': value}	

	
kg_bom_line()









