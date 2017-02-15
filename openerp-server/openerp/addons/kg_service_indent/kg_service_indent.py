from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import re
from operator import itemgetter
from itertools import groupby
from datetime import datetime
a = datetime.now()
dt_time = a.strftime('%m/%d/%Y %H:%M:%S')
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
import logging


class kg_service_indent(osv.osv):

	_name = "kg.service.indent"
	_description = "KG Service Indent"
	_order = "date desc"

	
	_columns = {
	
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'name': fields.char('Indent No', size=64, readonly=True),
		'dep_name': fields.many2one('kg.depmaster','Department', translate=True,required=True, select=True,readonly=True, states={'draft':[('readonly',False)],'confirm':[('readonly',False)]},domain="[('state','=','approved')]"),
		'date': fields.date('Indent Date',required=True,readonly=True, states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'service_indent_line': fields.one2many('kg.service.indent.line', 'service_id',
					'Indent Lines',readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'active': fields.boolean('Active'),
		'user_id' : fields.many2one('res.users', 'Created By', readonly=True),
		'state': fields.selection([('draft', 'Draft'),('confirm','WFA'),('approved','Approved'),('done','Done'),('cancel','Cancel'),('reject','Rejected')], 'Status', track_visibility='onchange', required=True),
		'gate_pass': fields.boolean('Gate Pass', readonly=True, states={'draft':[('readonly', False)],'confirm':[('readonly',False)]}),
		'creation_date':fields.datetime('Created Date',required=True,readonly=True),
		'origin': fields.char('Source Location', size=264,readonly=True, states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'remark': fields.text('Remarks'),
		'confirmed_by' : fields.many2one('res.users', 'Confirmed By', readonly=True),
		'approved_by' : fields.many2one('res.users', 'Approved By', readonly=True),
		'approved_date' : fields.datetime('Approved Date',readonly=True),

#added by dinesh
		'cancel_remark': fields.text('Cancel Remarks'),
		'confirm_date': fields.datetime('Confirmed Date', readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'update_date': fields.datetime('Last Updated Date', readonly=True),
		'update_user_id': fields.many2one('res.users', 'Last Updated By', readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'notes': fields.text('Notes'),

	}
	
	_sql_constraints = [('code_uniq','unique(name)', 'Indent number must be unique!')]

	_defaults = {
		
		'state' : 'draft',
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.depindent', context=c),
		'active' : 'True',
		'date' : fields.date.context_today,
		'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
		'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),

	}
	
	
	def cancel_indent(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		"""
		Cancel Indent
		"""
		pending_qty = 0
		for indent in self.browse(cr,uid,ids):
			if indent.service_indent_line[0].qty != indent.service_indent_line[0].pending_qty or indent.service_indent_line[0].qty != indent.service_indent_line[0].issue_pending_qty:
				raise osv.except_osv(
						_('Indent UnderProcessing'),
						_('You can not cancel this Indent because this indent is under processing !!!'))
			elif rec.cancel_remark:
				self.write(cr, uid,ids,{'state' : 'cancel',
								'cancel_user_id': uid,
								'cancel_date': time.strftime('%Y-%m-%d %H:%M:%S'),
								})
			else:
				raise osv.except_osv(_('Cancel remark is must !!'),
				_('Enter the remarks in Cancel remarks field !!'))
			
		return True	
	
	def reject_indent(self, cr, uid, ids,context=None):
		rec = self.browse(cr, uid,ids[0])
		if rec.remark:
			self.write(cr,uid,ids,{'state': 'reject',
								'rej_user_id': uid,
								'reject_date': time.strftime('%Y-%m-%d %H:%M:%S'),
							})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))	
	
	def email_ids(self,cr,uid,ids,context = None):
		email_from = []
		email_to = []
		email_cc = []
		val = {'email_from':'','email_to':'','email_cc':''}
		ir_model = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		mail_form_ids = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		for ids in mail_form_ids:
			mail_form_rec = self.pool.get('kg.mail.settings').browse(cr,uid,ids)
			if mail_form_rec.doc_name.model == 'kg.service.indent':
				email_from.append(mail_form_rec.name)
				mail_line_id = self.pool.get('kg.mail.settings.line').search(cr,uid,[('line_entry','=',ids)])
				for mail_id in mail_line_id:
					mail_line_rec = self.pool.get('kg.mail.settings.line').browse(cr,uid,mail_id)
					if mail_line_rec.to_address:
						email_to.append(mail_line_rec.mail_id)
					if mail_line_rec.cc_address:
						email_cc.append(mail_line_rec.mail_id)
			else:
				pass		
		val['email_from'] = email_from
		val['email_to'] = email_to
		val['email_cc'] = email_cc
		return val
	
	def draft_indent(self, cr, uid, ids,context=None):
		self.write(cr,uid,ids,{'state':'draft'})
		return True
		
		
	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(kg_service_indent, self).write(cr, uid, ids, vals, context)		
		
	def confirm_indent(self, cr, uid, ids,context=None):
		obj = self.browse(cr,uid,ids[0])
		indent_name = ''		
		if not obj.name:
			indent_no = self.pool.get('ir.sequence').get(cr, uid, 'kg.service.indent') or ''
			indent_no_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.service.indent')])
			rec = self.pool.get('ir.sequence').browse(cr,uid,indent_no_id[0])
			cr.execute("""select generatesequenceno(%s,'%s','%s') """%(indent_no_id[0],rec.code,obj.date))
			indent_name = cr.fetchone();
			self.write(cr,uid,ids,{'name':str(indent_name[0])})
			self.write(cr, uid, ids, {'state': 'confirm','confirmed_by': uid, 'confirm_date': time.strftime('%Y-%m-%d %H:%M:%S')})			
		return True
			
	def approve_indent(self, cr, uid, ids,context=None):
		obj = self.browse(cr,uid,ids[0])
		self.write(cr, uid, ids, {'state': 'approved','approved_by': uid, 'approved_date': time.strftime('%Y-%m-%d %H:%M:%S')})		
		line_obj = self.pool.get('kg.service.indent.line')

		for line in obj.service_indent_line:
			line_obj.write(cr,uid,line.id,{'pending_qty' : line.qty, 'issue_pending_qty' : line.qty,'gate_pending_qty':line.qty})
		self.write(cr,uid,ids,{'state':'approved','approved_by':uid,'approved_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		return True
	
	def entry_cancel(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.cancel_remark:
			self.write(cr, uid, ids, {'state': 'cancel','cancel_user_id': uid, 'cancel_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		else:
			raise osv.except_osv(_('Cancel remark is must !!'),
				_('Enter the remarks in Cancel remarks field !!'))
		return True
		
	def entry_draft(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'draft'})
		return True		

	def unlink(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		indent = self.read(cr, uid, ids, ['state'], context=context)
		unlink_ids = []
		for t in indent:
			if t['state'] in ('draft'):
				unlink_ids.append(t['id'])
			else:
				raise osv.except_osv(_('Invalid action !'), _('System not allow to delete a UN-DRAFT state Department Indent!!'))
		indent_lines_to_del = self.pool.get('kg.service.indent.line').search(cr, uid, [('service_id','in',unlink_ids)])
		self.pool.get('kg.service.indent.line').unlink(cr, uid, indent_lines_to_del)
		osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		return True
		
	def _check_lineitem(self, cr, uid, ids, context=None):
		for si in self.browse(cr,uid,ids):
			if si.service_indent_line==[] or si.service_indent_line:
					tot = 0.0
					for line in si.service_indent_line:
						tot += line.qty
					if tot <= 0.0:			
						return False
						
			return True
	
	_constraints = [
	
		(_check_lineitem, 'You can not save this Service Indent with out Line and Zero Qty  !!',['qty']),

		]	

kg_service_indent()

class kg_service_indent_line(osv.osv):
	
	_name = "kg.service.indent.line"
	_description = "Service Indent"

	def onchange_product_id(self, cr, uid, ids, product_id, uom,context=None):
			
		value = {'uom': ''}
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			value = {'uom': prod.uom_id.id}

		return {'value': value}
		
	def onchange_qty(self,cr,uid,ids,qty,pending_qty,issue_pending_qty,context=None):
		value = {'pending_qty': '', 'issue_pending_qty':'','gate_pending_qty':'',}
		if qty:
			pending_qty = qty
			value = {'pending_qty' : pending_qty, 'issue_pending_qty' : pending_qty,'gate_pending_qty':pending_qty}
		return {'value': value}
	
	
	_columns = {

	'service_id': fields.many2one('kg.service.indent', 'Indent No', required=True, ondelete='cascade'),
	'product_id': fields.many2one('product.product', 'Product', required=True,domain = [('state','=','approved'),('categ_id','not in',('Finishedgoods'))]),
	'uom': fields.many2one('product.uom', 'UOM', required=True,domain="[('dummy_state','=','approved')]"),
	'qty': fields.float('Quantity', required=True),
	'pending_qty':fields.float('Pending Qty'),
	'issue_pending_qty':fields.float('Issue Pending Qty'),
	'gate_pending_qty':fields.float('Gate Pass Pending Qty'),
	'note': fields.text('Remarks'),	
	'line_state': fields.selection([('process','Processing'),('noprocess','NoProcess'),('pi_done','PI-Done'),('done','Done')], 'Status'),
	'line_date': fields.date('Indent Date'),
	'brand_id':fields.many2one('kg.brand.master','Brand',domain="[('state','=','approved')]"),
	'ser_no':fields.char('Old Serial No', size=128,required=True),
	'serial_no':fields.many2one('stock.production.lot','Serial No',domain="[('product_id','=',product_id)]"),
	'return_qty':fields.float('Return Qty'),
	}

	_defaults = {

		'line_date' : fields.date.context_today,

	}
	
	
	
		
	
	
kg_service_indent_line()	
