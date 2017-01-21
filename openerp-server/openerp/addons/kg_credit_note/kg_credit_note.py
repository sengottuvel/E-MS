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

class kg_credit_note(osv.osv):
	
	
	def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		for order in self.browse(cr, uid, ids, context=context):
			res[order.id] = {
				'amount_total': 0.0,
			}
			val = 0.0
			for line in order.line_ids:
				val += line.price_subtotal
			res[order.id]['amount_total']= val
		return res
		
		
	_name = 'kg.credit.note'
	_description = "This form is to enter the credit note details"
	_order = "date desc"
	
	_columns = {
	
		'name':fields.char('Credit Note No',required=True),
		'date':fields.date('Credit Note Date'),
		'state': fields.selection([('draft','Draft'),('confirm','WFA'),('approved','Approved'),('reject','Rejected'),('cancel','Canceled')],'Status', readonly=True),
		'supplier_id':fields.many2one('res.partner','Supplier',domain = [('supplier','=',True),('sup_state','=','approved')],readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'supplier_invoice_no':fields.char('Supplier Invoice No',readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'supplier_invoice_date':fields.date('Supplier Invoice Date',readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'line_ids':fields.one2many('ch.credit.note','header_id','Credit Note',readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),   
		'remark':fields.text('Approve/Reject',readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total Amount',
			 multi="sums", store=True, track_visibility='always'),		
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
		'cancel_remark':fields.text('Cancel Remarks'),	
		'notes': fields.text('Notes'),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'updated_date': fields.datetime('Last Updated Date',readonly=True),
		'updated_by': fields.many2one('res.users','Last Updated By',readonly=True),		
		
	}
	
	_defaults = {
	
		'active': True,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg_credit_note', context=c),			
		'state': 'draft',
		'date': lambda * a: time.strftime('%Y-%m-%d'),
		'user_id': lambda obj, cr, uid, context: uid,
		'crt_date':lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
	}
	
	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(kg_credit_note, self).write(cr, uid, ids, vals, context)		
	
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

	def entry_confirm(self,cr,uid,ids,context=None):
		rec = self.browse(cr, uid, ids[0])		
		self.write(cr, uid, ids, {'state': 'confirm','confirm_user_id': uid, 'confirm_date': dt_time})
		return True

	def entry_approve(self,cr,uid,ids,context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.confirm_user_id.id == uid:
			raise osv.except_osv(
					_('Warning'),
					_('Approve cannot be done by Confirmed user'))
		self.write(cr, uid, ids, {'state': 'approved','app_user_id': uid, 'approve_date': dt_time})
		return True

	def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.remark:
			self.write(cr, uid, ids, {'state': 'reject','rej_user_id': uid, 'reject_date': dt_time})
		else:
			raise osv.except_osv(_('Kindly enter the reason for rejecton in remark field'),
				_(''))
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
				
				if line.price_unit <= 0:
					raise osv.except_osv(
					_('Warning'),
					_('Unit Price should be greater than zero for product %s')%(line.product_id.name_template))
				if line.qty <= 0:
					raise osv.except_osv(
					_('Warning'),
					_('Quantity should be greater than zero for product %s')%(line.product_id.name_template))	
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
	
	

kg_credit_note()



class ch_credit_note(osv.osv):
	
	def _amount_line(self, cr, uid, ids, prop, arg, context=None):
		res = {}
		for line in self.browse(cr, uid, ids, context=context):
			total = (line.qty * line.price_unit )
			res[line.id] = total
		return res
	
	_name='ch.credit.note'
	_description='This is used to track the product against this credit note'
	
	
	_columns={
	
		'header_id':fields.many2one('kg.credit.note','Credit Note No'),
		'product_id':fields.many2one('product.product','Item Name',domain = [('state','=','approved')]),
		'uom': fields.many2one('product.uom', 'UOM', required=True),
		'qty': fields.float('Quantity', required=True),
		'price_unit':fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
		'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account'),store=True),
		'remark':fields.text('Remarks'),
	
	}   
	
	_defaults = {   
	
	}
	

	
	
	
	def onchange_product_id(self, cr, uid, ids, product_id,context=None):
		value = {'uom': ''}
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			value = {'uom': prod.uom_id.id}
		return {'value': value}
	
	
		
ch_credit_note()
