## KG Purchase Indent Module ##

import math
import re
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from datetime import datetime
from itertools import groupby
import openerp.addons.decimal_precision as dp
import logging
logger = logging.getLogger('server')

class kg_purchase_indent(osv.osv):
	
	_name = "purchase.requisition"
	_inherit = "purchase.requisition"
	_order = "date_start desc"	
	
	_columns = {
	
		'name': fields.char('Indent No', size=64, readonly=True, states={'draft': [('readonly', False)],'in_progress':[('readonly',False)]}),
		'kg_store': fields.selection([('sub','Sub Store'), ('main','Main Store')], 'Store', readonly=True, states={'draft': [('readonly', False)],'in_progress':[('readonly',False)]}),
		'dep_name' : fields.many2one('kg.depmaster', 'Dep.Name', readonly=True, states={'draft': [('readonly', False)],'in_progress':[('readonly',False)]}),
		'state': fields.selection([('draft','Draft'),('in_progress','WFA'),('done','Purchase Done'),('approved','Approved'),('cancel','Cancelled'),('reject','Rejected')],
						'Status', track_visibility='onchange', required=True, readonly=True, states={'draft': [('readonly', False)],'in_progress':[('readonly',False)]}),
		'date_start':fields.date('Indent Date', readonly=True, states={'draft': [('readonly', False)],'in_progress':[('readonly',False)]}),
		'line_ids' : fields.one2many('purchase.requisition.line','requisition_id','Products to Purchase', readonly=True, states={'draft': [('readonly', False)],'in_progress':[('readonly',False)]}),
		'pi_type': fields.selection([('direct','Direct'),('fromdep','From Dep Indent')], 'Type'),
		'pi_flag': fields.boolean('pi flag'),
		'kg_seq_id':fields.many2one('ir.sequence','Document Type',domain=[('code','=','kg.purchase.indent')],
						readonly=True, states={'draft': [('readonly', False)],'in_progress':[('readonly',False)]}),			
		'expected_date':fields.date('Expected Date',required=True,readonly=True,states={'draft': [('readonly', False)],'in_progress':[('readonly',False)]}),
		'active': fields.boolean('Active'),
		'entry_mode': fields.selection([('auto','Auto'),('manual','Manual')],'Entry Mode',required=True,readonly=True),
		
		# Entry Info
		
		'created_by' : fields.many2one('res.users', 'Created By', readonly=True,select=True),
		'creation_date':fields.datetime('Created Date',readonly=True),
		'confirmed_by' : fields.many2one('res.users', 'Confirmed By', readonly=True,select=True),
		'confirmed_date': fields.datetime('Confirmed Date',readonly=True),
		'approved_by' : fields.many2one('res.users', 'Approved By', readonly=True,select=True),
		'approved_date' : fields.datetime('Apporved Date',readonly=True),
		'update_date' : fields.datetime('Last Updated Date',readonly=True),
		'update_user_id' : fields.many2one('res.users','Last Updated By',readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'notes': fields.text('Notes'),
		
		
		}
	
	_defaults = {
	
		'exclusive': 'exclusive',
		'kg_store': 'main',
		'name':'',
		'creation_date':lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'created_by': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id,
		'active': True,
		'entry_mode': 'manual',
		'indent_type': 'direct',
			
			}
			
	def set_to_draft(self, cr, uid, ids,context=None):
		rec = self.browse(cr, uid,ids[0])
		self.write(cr,uid,ids,{'state': 'draft'})			
	
	def _past_date_check(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		today = time.strftime("%Y-%m-%d")
		expected_date = str(rec.expected_date)
		if expected_date < today:
			return False
		return True
	
	def onchange_entry_mode(self, cr, uid, ids, entry_mode, pi_flag, context=None):
		value = {'pi_flag': ''}
		if entry_mode == 'manual':
			value = {'pi_flag': True}
		else:
			value = {'pi_flag': False}
		return {'value': value}
		
	def onchange_indent_type(self, cr, uid, ids, indent_type, pi_flag, context=None):
		value = {'pi_flag': ''}
		if indent_type == 'direct':
			value = {'pi_flag': True}
		else:
			value = {'pi_flag': False}
		return {'value': value}
		
	def email_ids(self,cr,uid,ids,context = None):
		email_from = []
		email_to = []
		email_cc = []
		val = {'email_from':'','email_to':'','email_cc':''}
		ir_model = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		mail_form_ids = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		for ids in mail_form_ids:
			mail_form_rec = self.pool.get('kg.mail.settings').browse(cr,uid,ids)
			if mail_form_rec.doc_name.model == 'kg.purchase.indent':
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
	

	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []		
		for rec in self.browse(cr,uid,ids):	
			if rec.state != 'draft':			
				raise osv.except_osv(_('Warning!'),
						_('You can not delete this entry !!'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		
	def tender_in_progress(self, cr, uid, ids, context=None):
		
		obj = self.browse(cr,uid,ids[0])
		seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','purchase.order.requisition')])
		seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
		cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,obj.date_start))
		seq_name = cr.fetchone();
		
		self.write(cr,uid,ids,{'name':seq_name[0]})
		self.write(cr,uid,ids,{'state':'in_progress','confirmed_by':uid,'confirmed_date':time.strftime("%Y-%m-%d")})
		return True
		   
	def tender_for_approve(self, cr, uid, ids,kg_seq_id, context=None):
		product_obj = self.pool.get('product.product')
		pi_line_obj = self.pool.get('purchase.requisition.line')
		obj = self.browse(cr,uid,ids[0])
		count ,count_line , value = 0 , 0 , []
		if obj.indent_type == 'fromdi':
			for i in obj.line_ids:
				if i.depindent_line_id.id:
					pass
				else:
					raise osv.except_osv(
							_('Warning'),
							_('You can not allowed to create a Manual Line Entry'))
		for t in self.browse(cr,uid,ids):
			indent_line_obj = self.pool.get('kg.depindent.line')
			if not t.line_ids:
				raise osv.except_osv(
						_('Empty Purchase Indent'),
						_('You can not confirm an empty Purchase Indent'))
			for line in t.line_ids:
				pi_line_obj.write(cr,uid,line.id, {'line_state' : 'process'})
				pi_line_obj.write(cr,uid,line.id, {'indent_state' : True})
				if line.product_qty==0:
					raise osv.except_osv(
						_('Error'),
						_('Purchase Indent quantity can not be zero'))
				else:
					print "Line have enough Qty"
					
			self.write(cr,uid,ids,{'state':'approved','approved_by':uid,'approved_date':time.strftime('%Y-%m-%d %H:%M:%S')})
			cr.execute(""" select depindent_line_id from kg_depindent_pi_line where pi_id = %s """ %(str(ids[0])))
			data = cr.dictfetchall()
			val = [d['depindent_line_id'] for d in data if 'depindent_line_id' in d] # Get a values form list of dict if the dict have with empty values
			pi_lines = obj.line_ids
			for i in range(len(pi_lines)):
				product_id = pi_lines[i].product_id.id
				product_record = product_obj.browse(cr, uid, product_id)
				product = pi_lines[i].product_id.name
				pi_used_qty = pi_lines[i].product_qty
					
				if pi_lines[i].line_ids:
					total = sum(wo.qty for wo in pi_lines[i].line_ids)
					if total <= pi_used_qty:
						pass
					else:
						raise osv.except_osv(
							_('Warning!'),
							_('Please Check WO Qty'))
				if pi_lines[i].depindent_line_id and pi_lines[i].group_flag == False:
					depindent_line_id=pi_lines[i].depindent_line_id
					orig_depindent_qty = pi_lines[i].dep_indent_qty
					
					po_uom_qty = pi_lines[i].po_uom_qty
					pending_stock_depindent_qty = pi_lines[i].dep_indent_qty -  pi_lines[i].po_uom_qty
					pending_po_depindent_qty = pi_lines[i].po_uom_qty - pi_lines[i].po_uom_qty
					tmp_qty = pi_used_qty * product_record.po_uom_coeff
					if pi_lines[i].product_uom_id.id != pi_lines[i].default_uom_id.id:
						if tmp_qty > orig_depindent_qty or pi_used_qty > po_uom_qty :
							pending_stock_depindent_qty = 0.0
							pending_po_depindent_qty = po_uom_qty - pi_used_qty
							sql = """ update kg_depindent_line set po_qty=%s, =%s where id = %s"""%(pending_po_depindent_qty,
										pending_stock_depindent_qty,pi_lines[i].depindent_line_id.id)
							cr.execute(sql)
							if pending_po_depindent_qty == 0:
								indent_line_obj.write(cr,uid,depindent_line_id.id, {'line_state' : 'process'})
							elif pending_po_depindent_qty > 0:
								indent_line_obj.write(cr,uid,depindent_line_id.id, {'line_state' : 'noprocess'})
						else:
							pending_stock_depindent_qty = orig_depindent_qty - tmp_qty
							pending_po_depindent_qty = po_uom_qty - pi_used_qty
							if pi_used_qty > po_uom_qty:
								pending_stock_depindent_qty = 0.0
								pending_po_depindent_qty = 0.0
								sql = """ update kg_depindent_line set po_qty=%s, pending_qty=%s where id = %s """%(pending_po_depindent_qty,
												pending_stock_depindent_qty,pi_lines[i].depindent_line_id.id)
								cr.execute(sql)
								if pending_po_depindent_qty == 0:
									indent_line_obj.write(cr,uid,depindent_line_id.id, {'line_state' : 'process'})
								elif pending_po_depindent_qty > 0:
									indent_line_obj.write(cr,uid,depindent_line_id.id, {'line_state' : 'noprocess'})
							else:
								sql = """ update kg_depindent_line set po_qty=%s, pending_qty=%s where id = %s """%(pending_po_depindent_qty,
													pending_stock_depindent_qty,pi_lines[i].depindent_line_id.id)
								cr.execute(sql)
								if pending_po_depindent_qty == 0:
									indent_line_obj.write(cr,uid,depindent_line_id.id, {'line_state' : 'process'})
								elif pending_po_depindent_qty > 0:
									indent_line_obj.write(cr,uid,depindent_line_id.id, {'line_state' : 'noprocess'})
					else:
						if pi_used_qty > po_uom_qty:
							pending_stock_depindent_qty = 0.0
							pending_po_depindent_qty = 0.0
							sql1 = """ update kg_depindent_line set po_qty=%s, pending_qty=%s where id = %s """%(pending_po_depindent_qty,
										pending_stock_depindent_qty,pi_lines[i].depindent_line_id.id)
							cr.execute(sql1)
							if pending_po_depindent_qty == 0:
								indent_line_obj.write(cr,uid,depindent_line_id.id, {'line_state' : 'process'})
							elif pending_po_depindent_qty > 0:
								indent_line_obj.write(cr,uid,depindent_line_id.id, {'line_state' : 'noprocess'})
						else:
							pending_stock_depindent_qty = orig_depindent_qty - pi_used_qty
							pending_po_depindent_qty = po_uom_qty - pi_used_qty
							sql1 = """ update kg_depindent_line set po_qty=%s, pending_qty=%s where id = %s """%(pending_po_depindent_qty,
										pending_stock_depindent_qty,pi_lines[i].depindent_line_id.id)
							cr.execute(sql1)
							if pending_po_depindent_qty == 0:
								indent_line_obj.write(cr,uid,depindent_line_id.id, {'line_state' : 'process'})
							elif pending_po_depindent_qty > 0:
								indent_line_obj.write(cr,uid,depindent_line_id.id, {'line_state' : 'noprocess'})
								
				else:
					if not pi_lines[i].depindent_line_id:
						pass
					if pi_lines[i].group_flag == True:
						self.update_product_group(cr,uid,ids,line=pi_lines[i])
					else:
						print "All are correct Values"
			
	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(kg_purchase_indent, self).write(cr, uid, ids, vals, context)
		
	def tender_cancel(self, cr, uid, ids, context=None):
		purchase_order_obj = self.pool.get('purchase.order')
		pi_line_obj = self.pool.get('purchase.requisition.line')
		piindent = self.browse(cr, uid, ids[0], context=context)
		if not piindent.cancel_remark:
			raise osv.except_osv(
				_('Remarks Needed !!'),
				_('Enter Remark in Remarks Tab....'))
				
		if piindent.indent_type == 'fromdi':
			if piindent.state == 'approved':	
				for line in piindent.line_ids:
					pi_line_obj.write(cr,uid,line.id, {'line_state' : 'noprocess'})
					if line.product_qty != line.pending_qty:
						raise osv.except_osv(
							_('Unable to cancel this Purchase Indent.'),
							_('First cancel all PO related to this Purchase Indent.'))
					else:
							if line.depindent_line_id and line.group_flag == False:
								orig_pending_qty = line.depindent_line_id.pending_qty
								pi_qty = line.product_qty
								orig_pending_qty += pi_qty
								line.depindent_line_id.write({'pending_qty':orig_pending_qty })
								line.depindent_line_id.write({'line_state':'noprocess' })
							else:
								pass
							# Need to do cancel process if a PI line is product Grouping
			else:			
				for line in piindent.line_ids:
					line.depindent_line_id.write({'line_state' : 'noprocess'})			
		else:
			pass
		return self.write(cr, uid, ids, {'state': 'cancel','cancel_date':time.strftime('%Y-%m-%d %H:%M:%S'),'cancel_user_id':uid})
		
		
	def tender_reject(self, cr, uid, ids, context=None):
		purchase_order_obj = self.pool.get('purchase.order')
		pi_line_obj = self.pool.get('purchase.requisition.line')
		piindent = self.browse(cr, uid, ids[0], context=context)
		
		if not piindent.remark:
			raise osv.except_osv(
				_('Remarks Needed !!'),
				_('Enter Remark in Remarks Tab....'))
			
		if piindent.indent_type == 'di':
			for line in piindent.line_ids:
				line.depindent_line_id.write({'line_state' : 'noprocess'})			
		else:
			pass
			
		return self.write(cr, uid, ids, {'state': 'reject','reject_date':time.strftime('%Y-%m-%d %H:%M:%S'),'rej_user_id':uid})
		
		
	def pi_approval(self, cr, uid, ids, context=None):
		
		self.write(cr, uid, ids, {'state': 'approved'})
		return True	
			

	def _check_line(self, cr, uid, ids, context=None):
		logger.info('[KG ERP] Class: kg_purchase_indent, Method: _check_line called...')
		for pi in self.browse(cr,uid,ids):
			if pi.kg_depindent_lines==[]:
				tot = 0.0
				for line in pi.line_ids:
					tot += line.product_qty
				if tot <= 0.0:			
					return False
			
			return True
			
	_constraints = [
	
		(_past_date_check, 'System not allow to save with past date. !!',['Expected Date']),
	]   	   	
		
kg_purchase_indent()

class kg_purchase_indent_line(osv.osv):
	
	_name = "purchase.requisition.line"
	_inherit = "purchase.requisition.line"
	_rec_name = 'name'
	
	_columns = {
	
	'rate': fields.float('Last Purchase Rate',readonly=True, state={'draft': [('readonly', False)]}),
	'line_date':fields.datetime('Indent Date'),
	'line_state': fields.selection([('process', 'Approved'),('noprocess', 'Confirmed'),
					('cancel', 'Cancel')], 'Status'),
	'current_qty':fields.float('Current Stock Quantity'),
	'dep_indent_qty': fields.float('Dep.Indent Qty'),
	'name': fields.char('Name', size=64),
	'depindent_line_id':fields.many2one('kg.depindent.line', 'Dep.Indent Line'),
	'default_uom_id': fields.many2one('product.uom', 'PO UOM'),
	'po_uom_qty': fields.float('PO.Qty'),
	'group_flag':fields.boolean('Group By'),
	'dep_id':fields.many2one('kg.depmaster', 'Department'),
	'user_id': fields.many2one('res.users', 'Users'),
	'cancel_remark': fields.text('Cancel Remarks'),
	'draft_flag':fields.boolean('Draft Flag'),
	'entry_mode': fields.selection([('auto','Auto'),('manual','Manual')],'Entry Mode'),
	'src_type': fields.selection([('direct', 'Direct'),('frompi', 'From PI'),('fromquote', 'From Quotation')], 'Soruce Type'),
	
	}
	
	_defaults = {
	
	'line_state' : 'noprocess',
	'name': 'PILINE',
	'line_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
	'draft_flag': False,
	'src_type': 'frompi',
	
	}		
	

		
	def onchange_product_id(self, cr, uid, ids, product_id, product_uom_id, context=None):
		value = {'product_uom_id': '','stock_qty':''}
		uom = ''
		stock_qty = 0.00
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			uom = prod.uom_po_id.id
		else:
			uom = ''	
		stock_sql = """ select sum(pending_qty) from stock_production_lot where product_id = %s group by product_id """%(product_id)
		cr.execute(stock_sql)		
		stock_data = cr.dictfetchall()
		if stock_data:
			stock_qty = stock_data[0]
			stock_qty = stock_qty.values()[0]
		else:
			stock_qty = 0.00
		value = {'product_uom_id': uom,'stock_qty': stock_qty}	
		return {'value': value}
			
	def onchange_qty(self, cr, uid, ids, product_qty, pending_qty, context=None):
		
		value = {'pending_qty': ''}
		if product_qty:
			value = {'pending_qty': product_qty}
		return {'value': value}
		

	def unlink(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for rec in self.browse(cr, uid, ids, context=context):
			parent_rec = rec.requisition_id
			if parent_rec.state not in ['draft','in_progress']:
				raise osv.except_osv(_('Invalid Action!'), _('Cannot delete a purchase indent line which is in state \'%s\'.') %(parent_rec.state,))
			else:
					pi_id = parent_rec.id
					dep_line_rec = rec.depindent_line_id			
					if dep_line_rec:	
						dep_line_id = rec.depindent_line_id.id
						dep_line_rec.write({'line_state' : 'noprocess'})
						del_sql = """ delete from kg_depindent_pi_line where pi_id=%s and depindent_line_id=%s """ %(pi_id,dep_line_id)
						cr.execute(del_sql)		
					return super(kg_purchase_indent_line, self).unlink(cr, uid, ids, context=context)
				
	def line_cancel(self, cr, uid, ids, context=None):
		line = self.browse(cr, uid, ids[0])
		if not line.cancel_remark:
			raise osv.except_osv(_('Remarks is must !!'), _('Enter cancel remarks !!!'))
		else:							
			line.write({'line_state' : 'cancel'})
			line.depindent_line_id.write({'pi_cancel' : True})
		return True

kg_purchase_indent_line()


