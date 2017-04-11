from datetime import *
import time
from osv import fields, osv
from tools.translate import _
import netsvc
import decimal_precision as dp
from itertools import groupby
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta
import smtplib
import socket
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
import logging
import netsvc
import pooler
import math
from tools import number_to_text_convert_india
logger = logging.getLogger('server')
today = datetime.now()


class kg_depindent(osv.osv):

	_name = "kg.depindent"
	_description = "Department Indent"
	_rec_name = "name"
	_order = "name desc"
	
	_columns = {
		
		'name': fields.char('No', size=64, readonly=True,select=True),
		'dep_name': fields.many2one('kg.depmaster','Department', required=True,translate=True, select=True,readonly=True,
					domain="[('item_request','=',True),('state','=','approved')]", states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'date': fields.datetime('Created Date',readonly=True),
		'ind_date': fields.date('Indent Date'),
		'entry_date': fields.date('Entry Date',readonly=True),
		'type': fields.selection([('direct','Direct'), ('from_bom','From BoM')], 'Entry Mode',readonly=True, states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'dep_indent_line': fields.one2many('kg.depindent.line', 'indent_id', 'Indent Lines', readonly=True, states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'active': fields.boolean('Active'),
		'user_id' : fields.many2one('res.users', 'Created By', readonly=True,select=True),
		'src_location_id': fields.many2one('stock.location', 'MainStock Location'),
		'dest_location_id': fields.many2one('stock.location', 'DepStock Location'),
		'state': fields.selection([('draft', 'Draft'),('confirm','WFA'),('approved','Approved'),('rejected','Rejected'),('cancel','Cancelled')], 'Status', track_visibility='onchange', required=True),
		'main_store': fields.boolean('For Main Store',readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'remarks': fields.text('Approve/Reject',readonly=True,states={'confirm':[('readonly',False)]}),
		'cancel_remark': fields.text('Cancel Remarks',readonly=True,states={'approved':[('readonly',False)]}),
		'project':fields.char('Project',size=100,readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'confirmed_by' : fields.many2one('res.users', 'Confirmed By', readonly=True,select=True),
		'confirmed_date': fields.datetime('Confirmed Date',readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'approved_by' : fields.many2one('res.users', 'Approved By', readonly=True,select=True),
		'approved_date' : fields.datetime('Approved Date',readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'update_date' : fields.datetime('Last Updated Date',readonly=True),
		'update_user_id' : fields.many2one('res.users','Last Updated By',readonly=True),
		'ticket_no':fields.char('Ticket No',size=200,readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'ticket_date':fields.date('Ticket Date',readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'entry_mode': fields.selection([('auto','Auto'),('manual','Manual')],'Entry Mode',required=True,readonly=True),
		'indent_type': fields.selection([('production','For Production'),('own_use','For Own Use')],'Indent Type',required=True,readonly=True,states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
		#added by dinesh
		'notes': fields.text('Notes'),
		
	}
	

	_defaults = {
		
		'type' : 'direct',
		'state' : 'draft',
		'active' : True,
		'date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
		'ind_date': fields.date.context_today,
		'entry_date': fields.date.context_today,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.depindent', context=c),
		'entry_mode': 'manual',
		
			}
	

	
	
	def onchange_ticket_date(self, cr, uid, ids, ticket_date):
		today_date = today.strftime('%Y-%m-%d')
		bk_date = date.today() - timedelta(days=2)
		back_date = bk_date.strftime('%Y-%m-%d')
		holiday_obj = self.pool.get('kg.holiday.master.line')
		holiday_ids = holiday_obj.search(cr, uid, [('leave_date','=',back_date)])
		if ticket_date > today_date:
			raise osv.except_osv(
					_('Warning'),
					_('Ticket Date should be less than or equal to current date!'))	
		if holiday_ids:
			hol_bk_date = date.today() - timedelta(days=3)
			hol_back_date = hol_bk_date.strftime('%Y-%m-%d')
			if ticket_date <= hol_back_date:
				raise osv.except_osv(
					_('Warning'),
					_('Department Indent Entry is not allowed for this ticket date!'))
		else:
			if ticket_date <= back_date:
				raise osv.except_osv(
					_('Warning'),
					_('Department Indent Entry is not allowed for this ticket date!'))
		return True

	def _check_uomline(self, cr, uid, ids, context=None):
		indent = self.browse(cr,uid,ids[0])
		pro_obj = self.pool.get('product.product')
		if indent.dep_indent_line:			
			for line in indent.dep_indent_line:				
				pro_id = line.product_id.id
				pro_rec = pro_obj.browse(cr,uid,pro_id)
				po_uom = pro_rec.uom_po_id.id
				st_uom = pro_rec.uom_id.id
				uom = line.uom.id
				if uom != po_uom:
					if uom != st_uom:
						return False
				else:
					if uom != st_uom:
						if uom != po_uom:
							return False	
			return True
			
	def _check_product_duplicate(self, cr, uid, ids, context=None):
		indent = self.browse(cr,uid,ids[0])
		pro_obj = self.pool.get('product.product')
		if indent.dep_indent_line:			
			for line in indent.dep_indent_line:				
				pro_id = line.product_id
	
	def email_ids(self,cr,uid,ids,context = None):
		email_from = []
		email_to = []
		email_cc = []
		val = {'email_from':'','email_to':'','email_cc':''}
		ir_model = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		mail_form_ids = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		for ids in mail_form_ids:
			mail_form_rec = self.pool.get('kg.mail.settings').browse(cr,uid,ids)
			if mail_form_rec.doc_name.model == 'kg.depindent':
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
		
	def confirm_indent(self, cr, uid, ids,context=None):
		product_obj = self.pool.get('product.product')
		indent_obj = self.browse(cr, uid,ids[0])
		total = 0
		indent_lines = indent_obj.dep_indent_line
		for i in range(len(indent_lines)):
			indent_qty=indent_lines[i].qty
			if indent_lines[i].line_id:
				total = sum(wo.qty for wo in indent_lines[i].line_id)
				if total <= indent_qty:
					pass
				else:
					raise osv.except_osv(
						_('Warning!'),
						_('Please Check WO Qty'))
				wo_sql = """ select count(wo_id) as wo_tot,wo_id as wo_name from ch_depindent_wo where header_id = %s group by wo_id"""%(indent_lines[i].id)
				cr.execute(wo_sql)		
				wo_data = cr.dictfetchall()
				for wo in wo_data:
					if wo['wo_tot'] > 1:
						raise osv.except_osv(
						_('Warning!'),
						_('%s This WO No. repeated'%(wo['wo_name'])))
					else:
						pass
		
		location = self.pool.get('kg.depmaster').browse(cr, uid, indent_obj.dep_name.id, context=context)
		self.write(cr,uid,ids,{'src_location_id' : location.main_location.id,'dest_location_id':location.stock_location.id})
		for t in self.browse(cr,uid,ids):
			if not t.dep_indent_line:
				raise osv.except_osv(
						_('Empty Department Indent'),
						_('You can not confirm an empty Department Indent'))
			depindent_line = t.dep_indent_line[0]
			depindent_line_id = depindent_line.id

			if t.dep_indent_line[0].qty==0:
				raise osv.except_osv(
						_('Error'),
						_('Department Indent quantity can not be zero'))
			for line in t.dep_indent_line:
				product_record = product_obj.browse(cr,uid,line.product_id.id)
				cr.execute("""update kg_depindent_line set uom = %s where id = %s"""%(line.product_id.uom_id.id,line.id))
				if line.uom.id != product_record.uom_po_id.id:
					new_po_qty = line.qty / product_record.po_uom_coeff
			seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.depindent')])
			seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
			cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,indent_obj.ind_date))
			seq_name = cr.fetchone();
			self.write(cr,uid,ids,{'state':'confirm',
						'confirmed_by': uid,
						'confirmed_date': datetime.now(),
						'name': seq_name[0]
						})
			return True
	
	def reject_indent(self, cr, uid, ids,context=None):
		rec = self.browse(cr, uid,ids[0])
		if rec.remarks:
			self.write(cr,uid,ids,{'state': 'rejected',
								'rej_user_id': uid,
								'reject_date': time.strftime("%Y-%m-%d"),
							})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
				
	def set_to_draft(self, cr, uid, ids,context=None):
		rec = self.browse(cr, uid,ids[0])
		self.write(cr,uid,ids,{'state': 'draft'})
		
	def approve_indent(self, cr, uid, ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		total = 0
		indent_lines = rec.dep_indent_line
		for i in range(len(indent_lines)):
			indent_qty=indent_lines[i].qty
			if indent_lines[i].line_id:
				total = sum(wo.qty for wo in indent_lines[i].line_id)
				if total <= indent_qty:
					pass
				else:
					raise osv.except_osv(
						_('Warning!'),
						_('Please Check WO Qty'))
				wo_sql = """ select count(wo_id) as wo_tot,wo_id as wo_name from ch_depindent_wo where header_id = %s group by wo_id"""%(indent_lines[i].id)
				cr.execute(wo_sql)		
				wo_data = cr.dictfetchall()
				for wo in wo_data:
					if wo['wo_tot'] > 1:
						raise osv.except_osv(
						_('Warning!'),
						_('%s This WO No. repeated'%(wo['wo_name'])))
					else:
						pass
						
		for t in self.browse(cr,uid,ids):
			if not t.dep_indent_line:
				raise osv.except_osv(
						_('Empty Department Indent'),
						_('You can not approve an empty Department Indent'))
			depindent_line = t.dep_indent_line[0]
			depindent_line_id = depindent_line.id
			if t.dep_indent_line[0].qty==0:
				raise osv.except_osv(
						_('Error'),
						_('Department Indent quantity can not be zero'))
		if rec.dep_indent_line:
			for line in rec.dep_indent_line:
				indent_qty = line.qty
				if line.line_id:
					total = sum(wo.qty for wo in line.line_id)
					if total <= indent_qty:
						pass
					else:
						raise osv.except_osv(
							_('Warning!'),
							_('Please Check WO Qty'))
		self.write(cr,uid,ids,{'state':'approved','approved_by':uid,'approved_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		
		
	def done_indent(self, cr, uid, ids,context=None):
		self.write(cr,uid,ids,{'state':'done'})
		return True
		
	def cancel_indent(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		pending_qty = 0
		for indent in self.browse(cr,uid,ids):
			if indent.dep_indent_line[0].qty != indent.dep_indent_line[0].pending_qty or indent.dep_indent_line[0].qty != indent.dep_indent_line[0].issue_pending_qty:
				raise osv.except_osv(
						_('Indent UnderProcessing'),
						_('You can not cancel this Indent because this indent is under processing !!!'))
			elif rec.cancel_remark:
				self.write(cr, uid,ids,{'state' : 'cancel',
								'cancel_user_id': uid,
								'cancel_date': time.strftime("%Y-%m-%d"),
								})
			else:
				raise osv.except_osv(_('Cancel remark is must !!'),
				_('Enter the remarks in Cancel remarks field !!'))
			
		
		return True

	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(kg_depindent, self).write(cr, uid, ids, vals, context)
		
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
		indent_lines_to_del = self.pool.get('kg.depindent.line').search(cr, uid, [('indent_id','in',unlink_ids)])
		self.pool.get('kg.depindent.line').unlink(cr, uid, indent_lines_to_del)
		osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		return True
		
	def onchange_user_id(self, cr, uid, ids, user_id, context=None):
		value = {'dep_name': ''}
		if user_id:
			user = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
			value = {'dep_name': user.dep_name.id}
		return {'value': value}
	
	def onchange_depname(self, cr, uid, ids, dep_name, src_location_id,dest_location_id,context=None):
		value = {'src_location_id' : '','dest_location_id':''}
		if dep_name:
			location = self.pool.get('kg.depmaster').browse(cr, uid, dep_name, context=context)
			value = {'src_location_id' : location.main_location.id,'dest_location_id':location.stock_location.id}
		return {'value' : value}
		
	def print_indent(self, cr, uid, ids, context=None):		
		assert len(ids) == 1, 'This option should only be used for a single id at a time'
		wf_service = netsvc.LocalService("workflow")
		wf_service.trg_validate(uid, 'kg.depindent', ids[0], 'send_rfq', cr)
		datas = {
				 'model': 'kg.depindent',
				 'ids': ids,
				 'form': self.read(cr, uid, ids[0], context=context),
		}
		return {'type': 'ir.actions.report.xml', 'report_name': 'indent.on.screen.report', 'datas': datas, 'nodestroy': True}
	

kg_depindent()

class kg_depindent_line(osv.osv):
	
	_name = "kg.depindent.line"
	_description = "Department Indent Line"
	_rec_name = 'indent_id'
	
	def onchange_product_id(self, cr, uid, ids, product_id, uom, po_uom, context=None):
		value = {'uom': '', 'po_uom': ''}
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			value = {'uom': prod.uom_id.id, 'po_uom' : prod.uom_po_id.id}
		return {'value': value}
		
	def onchange_product_uom(self, cr, uid, ids, product_id, uom, po_uom,qty, context=None):
		value = {'qty': 0.0}
		if qty:			
			value = {'qty': 0.0}
		prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)

		if uom != prod.uom_id.id:
			if uom != prod.uom_po_id.id:				 			
				raise osv.except_osv(
					_('UOM Mismatching Error !'),
					_('You choosed wrong UOM and you can choose either %s or %s for %s !!!') % (prod.uom_id.name,prod.uom_po_id.name,prod.name))
		else:
			if uom != prod.uom_po_id.id:
				if uom != prod.uom_id.id:
								
					raise osv.except_osv(
						_('UOM Mismatching Error !'),
						_('You choosed wrong UOM and you can choose either %s or %s for %s !!!') % (prod.uom_id.name,prod.uom_po_id.name,prod.name))

		return {'value': value}
	
	def onchange_qty(self, cr, uid, ids, uom,product_id, qty, pending_qty, issue_pending_qty,po_qty, context=None):
		value = {'pending_qty': '', 'issue_pending_qty':'', 'po_qty':''}
		prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)

		if product_id and qty:
			if uom != prod.uom_po_id.id:
				dep_po_qty_test = qty / prod.po_uom_coeff
				dep_po_qty = (math.ceil(dep_po_qty_test))
				value = {'pending_qty': qty, 'issue_pending_qty' : qty, 'po_qty' : dep_po_qty }
			else:
				value = {'pending_qty': qty, 'issue_pending_qty' : qty, 'po_qty' : qty}
		return {'value': value}
		

	def _main_store_qty(self,cr,uid,ids,product_id,context=None):		
		sql_in = """ select sum(product_qty)
					from stock_move as st_move
					join stock_picking as picking on(picking.id = st_move.picking_id)
					where st_move.state = %s and st_move.product_id = %s and picking.type = %s
					('done',product_id.id,'in')"""
		sql_out = """ select sum(product_qty)
					from stock_move as st_move
					join stock_picking as picking on(picking.id = st_move.picking_id)
					where st_move.state = %s and st_move.product_id = %s and picking.type = %s 
					('done',product_id.id,'out') """
		data_in = cr.execute(sql_in)
		data_out = cr.execute(sql_out)
		
	def _get_product_available_func(states, what):
		def _product_available(self, cr, uid, ids, name, arg, context=None):
			return {}.fromkeys(ids, 0.0)
		return _product_available

	_stock_qty = _get_product_available_func(('done',), ('in', 'out'))
	
	_columns = {

	'indent_id': fields.many2one('kg.depindent', 'Indent.NO', required=True, ondelete='cascade'),
	'line_date': fields.date('Indent Date', required=True, readonly=True),
	'product_id': fields.many2one('product.product', 'Product', required=True,domain="[('state','=','approved'),('categ_id','not in',('Finishedgoods'))]"),
	'uom': fields.many2one('product.uom', 'UOM', required=True,domain="[('dummy_state','=','approved')]"),
	'po_uom': fields.many2one('product.uom', 'PO UOM'),
	'qty': fields.float('Indent Qty', required=True),
	'po_qty': fields.float('PO Qty',),
	'pending_qty': fields.float('Pending Qty'),
	'issue_pending_qty': fields.float('Issue.Pending Qty'),
	'main_store_qty': fields.function(_stock_qty, type='float', string='Quantity On Hand'),
	'dep_id': fields.many2one('kg.depmaster', 'Dep.Name'),
	'line_state': fields.selection([('process','Processing'),('noprocess','NoProcess'),('pi_done','PI-Done'),('done','Done')], 'Status'),
	'note': fields.text('Remarks'),
	'name': fields.char('Name', size=128),
	'state':fields.related('indent_id','state',type='selection',string="State",store=True),
	'dep_id': fields.many2one('kg.depmaster','Department Name'),
	'pi_cancel': fields.boolean('Cancel'),
	'required_date': fields.date('Required Date'),
	'brand_id': fields.many2one('kg.brand.master', 'Brand Name',domain="[('state','=','approved')]"),
	'return_qty':fields.float('Return Qty'),
	'line_id': fields.one2many('ch.depindent.wo','header_id','Ch Line Id'),
	
	}
	
	_defaults = {
	
	'line_state' : 'noprocess',
	'name': 'Dep.Indent.Line',
	'line_date' : fields.date.context_today,
	
	}
		

		
kg_depindent_line()	



class ch_depindent_wo(osv.osv):
	
	_name = "ch.depindent.wo"
	_description = "Ch Depindent WO"
	
	_columns = {

	'header_id': fields.many2one('kg.depindent.line', 'Dept Indent Line', required=True, ondelete='cascade'),
	'wo_id': fields.char('WO', required=True),
	'qty': fields.float('Indent Qty', required=True),
	
	}
	
	def _check_qty(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.qty <= 0.00:
			return False					
		return True
		
	_constraints = [
		(_check_qty,'You cannot save with zero qty !',['WO Qty']),
		
		]
				
	
ch_depindent_wo()	


