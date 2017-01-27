## KG Quotation ##

from datetime import *
import time
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _

import decimal_precision as dp
from itertools import groupby
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta
import smtplib
import socket
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from collections import OrderedDict
import logging


from tools import number_to_text_convert_india
logger = logging.getLogger('server')
today = datetime.now()

import urllib
import urllib2
import logging
import base64

class kg_rfq_vendor_selection(osv.osv):
	_name = "kg.rfq.vendor.selection"
	_description = "RFQ Vendor Selection"
	_order = 'name desc'
	
	_columns = {
		'name': fields.char('RFQ No', size=32, ),
		'rfq_name': fields.char('Alias Name', size=64, ),
		'quotation_date': fields.date('RFQ Date'),
		'state': fields.selection([('draft', 'Draft'),('approved', 'RFQ Generated'),('rfq_approved', 'RFQ Approved'),('comparison_confirmed', 'Compared'),('comparison_approved', 'QCA'),], 'Status'),
		'quote_submission_date': fields.date('Due Date'),
		'user_id': fields.many2one('res.users', 'Requested By'),
		'requisition_line_ids': fields.many2many('purchase.requisition.line', 'kg_rfq_pi_lines','quote_id','requisition_id','Purchase Indent Lines',domain="[('pending_qty','>','0'), '&',('line_state','=','process'), '&',('draft_flag','=', False)]"),
		'line_id': fields.one2many('kg.rfq.vendor.selection.line', 'header_id', 'Entries', ),
		'vendor_ids': fields.one2many('kg.rfq.vendor.list', 'header_id', 'Vendors' ),
		'visible_quote': fields.boolean('Quote Visible'),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'crt_date': fields.datetime('Created Date',readonly=True),
		'created_by': fields.many2one('res.users','Created By',readonly=True),
		'update_date' : fields.datetime('Last Updated Date',readonly=True),
		'update_user_id' : fields.many2one('res.users','Last Updated By',readonly=True),
		
	}
	
	_defaults = {
		'name': '/',
		'visible_quote':False,
		'state': 'draft',
		'quotation_date': lambda *a: time.strftime('%Y-%m-%d'),
		'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
		'created_by': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
		'crt_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.rfq.vendor.selection', context=c),
	}
	
			
	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []		
		for rec in self.browse(cr,uid,ids):	
			if rec.state not in ('draft'):				
				raise osv.except_osv(_('Warning!'),
						_('You can not delete this entry !!'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
			

	def _line_entry_check(self,cr,uid,ids,context = None):
		entry = self.browse(cr,uid,ids[0])
		if not entry.requisition_line_ids:
			return False
		return True
	def _entry_date_check(self,cr,uid,ids,context = None):
		entry = self.browse(cr,uid,ids[0])
		if entry.quote_submission_date < entry.quotation_date :
			return False
		return True
	
	_constraints = [
		(_line_entry_check, 'You cannot Confirm the record without line entry!', ['id']),
		(_entry_date_check, 'Due date should be greater than the RFQ date!!!', ['Due Date']),
	]
		
	def proceed(self, cr, uid, ids, context=None):
		pi_line_obj = self.pool.get('purchase.requisition.line')
		line_obj = self.pool.get('kg.rfq.vendor.selection.line')
		vendor_obj = self.pool.get('kg.rfq.vendor.list')
		rec = self.browse(cr,uid,ids[0])
		
		for quote in self.browse(cr, uid, ids, context=context):
			tmp_ids = []
			del_sql = """ delete from kg_rfq_vendor_selection_line where header_id=%s """ %(ids[0])
			cr.execute(del_sql)
			ven_sql = """ delete from kg_rfq_vendor_list where header_id=%s """ %(ids[0])
			cr.execute(ven_sql)
			cr.execute("""select requisition_id from kg_rfq_pi_lines where quote_id = %s"""%(quote.id))
			data = cr.dictfetchall()
			for pi_lines in data:
				line_ids = pi_lines['requisition_id']
				tree = pi_line_obj.browse(cr, uid, line_ids, context)
				
				for item in tree.product_id.pro_seller_ids:
					vendor_line_ids = self.pool.get('kg.rfq.vendor.list').search(cr,uid,[('header_id','=',rec.id),('partner_id','=',item.name.id)])
					print"vendor_line_ids",vendor_line_ids
				
					tot_add = (item.name.street or '')+ ' ' + (item.name.street2 or '') + '\n'+(item.name.city_id.name or '')+ ',' +(item.name.state_id.name or '') + '-' +(item.name.zip or '') + '\nPh:' + (item.name.phone or '')+ '\n' +(item.name.mobile or '')		
					if vendor_line_ids:
						pass
					else:						
						vendor_ids = vendor_obj.create(cr,uid,{'partner_id':item.name.id,'header_id':rec.id,'partner_address':tot_add})
				
				pi_line_obj.write(cr, uid, pi_lines['requisition_id'], {'src_type':'fromquote'})
				name = 'name'
				cr.execute(''' insert into kg_rfq_vendor_selection_line (create_date,create_uid,name,state,purchase_requisition_id,header_id,quotation_qty,product_uom_id,purchase_requisition_line_id,product_id,requested_qty,product_name,due_date)
				values(now(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',[uid,name, 'draft',tree.requisition_id.id,quote.id,tree.pending_qty,tree.product_uom_id.id,tree.id,tree.product_id.id,tree.product_qty,tree.product_id.name_template,rec.quote_submission_date])
		return True

	def approve_rfq(self, cr, uid, ids, context=None):
		vendor = []
		rec = self.browse(cr,uid,ids[0])
		rfq_pi_obj = self.pool.get('kg.rfq.vendor.selection.line')
		quote_pi_obj = self.pool.get('kg.quote.pi.line')
		quote_ven_obj = self.pool.get('kg.rfq.vendor.list')
		quote_header_obj = self.pool.get('kg.quotation.requisition.header')
		quote_line_obj = self.pool.get('kg.quotation.requisition.line')
		pi_line_obj = self.pool.get('purchase.requisition.line')
		for line in rec.line_id:
			if line.purchase_requisition_line_id.pending_qty < line.quotation_qty:
				raise osv.except_osv(_('RFQ Qty'), _('Indent Qty should not be greater than pending qty!!'))
			
			product_qty = line.purchase_requisition_line_id.pending_qty - line.quotation_qty
			pi_line_obj.write(cr,uid,line.purchase_requisition_line_id.id, {'pending_qty':product_qty})
		
		
		for custom in self.browse(cr, uid, ids, context=context):
			print"length",len(custom.vendor_ids)
			if len(custom.vendor_ids) > 5:
				raise osv.except_osv(_('Vendor List'), _('Please Check Vendor selection only Five Vendors To Generate RFQ'))				
			if not custom.line_id:
				raise osv.except_osv(_('Invalid action !'), _('Please Add Purchase Indent Lines To Generate RFQ'))
			if not custom.vendor_ids:
				raise osv.except_osv(_('Invalid action !'), _('Please Add Vendor list '))
			if custom.name == '/':
				name = self.pool.get('ir.sequence').get(cr, uid, 'kg.rfq.vendor.selection')
			else:
				name = custom.name
			duplicate_ids = quote_header_obj.search(cr, uid, [('rfq_no_id','=',custom.id)])
			if duplicate_ids == []:
				header_vals = {
					'quotation_date': custom.quotation_date,
					'user_id': custom.user_id.id,
					'state': 'draft',
					'rfq_no_id': custom.id,
				}
				quote_header_id = quote_header_obj.create(cr, uid, header_vals)
				if quote_header_id:
					ven_list = []
					vendor_line_ids = quote_ven_obj.search(cr, uid, [('header_id','=',custom.id)])
					if len(vendor_line_ids)>5:
						raise osv.except_osv(_(''), _('Please Select Only Five Vendors for Comparision!!!'))
					for lines in vendor_line_ids:
						ven_rec = quote_ven_obj.browse(cr, uid, lines, context)
						ven_list.append(ven_rec.partner_id.id)
					tmp_list = list(set(ven_list))
					if len(tmp_list) != len(vendor_line_ids):
						raise osv.except_osv(_(''), _('Vendor shoud be unique!!!'))
					for line in vendor_line_ids:
						vendor_rec = quote_ven_obj.browse(cr, uid, line, context)
						quote_ven_obj.write(cr, uid, [vendor_rec.id], {'state':'approved'})
						name_ref = self.pool.get('ir.sequence').get(cr, uid, 'kg.quotation.requisition.line')
						line_vals = {
							'header_id': quote_header_id,
							'user_id': custom.user_id.id,
							'partner_id': vendor_rec.partner_id.id,
							'user_ref_id': vendor_rec.partner_id.user_ref_id.id,
							'partner_address': vendor_rec.partner_address,
							'name': name_ref,
							'rfq_ven_id': custom.id,
							'due_date': custom.quote_submission_date,
							'state': 'draft',
							'rfq_date': custom.quotation_date,
						}
						quote_line_id = quote_line_obj.create(cr, uid, line_vals)
						rfq_pi_id = rfq_pi_obj.search(cr, uid, [('header_id','=',custom.id)])
						for prod in rfq_pi_id:
							rfq_pi_rec = rfq_pi_obj.browse(cr, uid, prod, context)
							rfq_pi_obj.write(cr, uid, [rfq_pi_rec.id], {'state':'approved'})
							pro_price = """ select price from ch_supplier_details where supplier_id=%s and partner_id = %s""" %(rfq_pi_rec.product_id.id,vendor_rec.partner_id.id)
							cr.execute(pro_price)
							data = cr.dictfetchall()
							if data:
								price_val = data[0]['price']
							else:
								price_val = 0
							merge_vals = {
								'name': 'name',
								'rfq_no_id': custom.id ,
								'header_id': quote_line_id,
								'user_id': custom.user_id.id,
								'product_id': rfq_pi_rec.product_id.id,
								'product_name': rfq_pi_rec.product_name,
								'product_uom_id': rfq_pi_rec.product_uom_id.id,
								'requested_qty': rfq_pi_rec.requested_qty,
								'quotation_qty': rfq_pi_rec.quotation_qty,
								'state': 'draft',
								'rfq_date': custom.quotation_date,
								'partner_id':vendor_rec.partner_id.id,
								'partner_address': vendor_rec.partner_address,
								'partner_name': vendor_rec.partner_name,	
								'vendors_price': price_val,
																
							}
							quote_pi_id = quote_pi_obj.create(cr, uid, merge_vals)							
			self.write(cr, uid, ids, {'state':'approved', 'name':name})
		return True
	
	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(kg_rfq_vendor_selection, self).write(cr, uid, ids, vals, context)
		
kg_rfq_vendor_selection() 

class kg_rfq_vendor_list(osv.osv):
	
	_name = "kg.rfq.vendor.list"
	_order = 'partner_name asc'
	
	_columns = {
		'header_id': fields.many2one('kg.rfq.vendor.selection' , 'Header Id', required=True, ondelete='cascade'),
		'partner_id': fields.many2one('res.partner', 'Vendor', domain="[('supplier','=',1),('sup_state','=','approved')]", required=True),
		'state': fields.selection([('draft','Draft'),('approved','Approved')], 'Status'),
		'partner_address': fields.char('Vendor Address',size=200, ),
		'partner_name': fields.related('partner_id','name',type='char', string="Vendor Name", size=200, store=True),
		'active': fields.boolean('Active'),
	}
	
	_defaults = {
		'active':True,
		'state':'draft',
	}
	
	def onchange_partner_id(self, cr, uid, ids, partner_id):
		partner = self.pool.get('res.partner')
		if partner_id:
			supplier_address = partner.address_get(cr, uid, [partner_id], ['default'])
			supplier = partner.browse(cr, uid, partner_id)
			tot_add = (supplier.street or '')+ ' ' + (supplier.street2 or '') + '\n'+(supplier.city_id.name or '')+ ',' +(supplier.state_id.name or '') + '-' +(supplier.zip or '') + '\nPh:' + (supplier.phone or '')+ '\n' +(supplier.mobile or '')		
			return {'value': {
				'partner_address' : tot_add or False
				}}
	
kg_rfq_vendor_list()

class kg_rfq_vendor_selection_line(osv.osv): 
	_name = 'kg.rfq.vendor.selection.line'
	
	_columns = {
		'name': fields.char('Name',size=128),
		'product_id': fields.many2one('product.product', 'Product'),
		'product_name': fields.related('product_id', 'name', type='char', string='Product Name', store=True, size=300),
		'product_uom_id': fields.related('product_id','uom_id', type='many2one', relation='product.uom', string='Product UOM', store=True),
		'state': fields.selection([('draft','Draft'),('approved','Approved')], 'Status'),
		'requested_qty': fields.float('Purchase Indent Approved Qty', digits=(16,3)),
		'quotation_qty': fields.float('RFQ Qty', digits=(16,3), ),
		'header_id': fields.many2one('kg.rfq.vendor.selection', 'Header', ondelete="cascade", ),
		'purchase_requisition_id': fields.many2one('purchase.requisition', 'Material Requisition No.', ),
		'purchase_requisition_line_id': fields.many2one('purchase.requisition.line', 'Material Requisition No.'),
		'vendor_ids': fields.one2many('kg.rfq.vendor.list', 'header_id', 'Vendors' ),
		'due_date': fields.date('Due Date'),
		'remarks': fields.text('Remarks'),
		'brand_id': fields.many2one('kg.brand.master','Brand'),
		
	}
	
	_defaults = {
		'name': '/',
		'state': 'draft',
	}	
	
	def create(self, cr, uid, vals, context=None):
		return super(kg_rfq_vendor_selection_line, self).create(cr, uid, vals, context=context)
		
kg_rfq_vendor_selection_line()

class kg_quotation_requisition_header(osv.osv):
	_name = 'kg.quotation.requisition.header'
	
	_columns = {
		'name': fields.char('Quotation Reference', size=32, readonly=True),
		'revision': fields.integer('Revision'),
		'quotation_date': fields.date('RFQ Date', readonly=True),
		'user_id': fields.many2one('res.users', 'Requested By'),
		'state': fields.selection([('draft', 'Draft'),('approved', 'Approved'),('reject', 'Reject'),('revised', 'Revised'),], 'State'),
		'rfq_no_id': fields.many2one('kg.rfq.vendor.selection', 'Comparison No.', required=True,),
		'line_ids': fields.one2many('kg.quotation.requisition.line', 'header_id', 'RFQ Lines', readonly=False, ),
	  
	}
	_defaults = {
		'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
		'quotation_date': lambda *a: time.strftime('%Y-%m-%d'),
		'state': 'draft',
		'name': '/',
	}
	
	_order = 'id desc'
	
	def create_revision1(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		print "rec.id",rec.id
		print "rerererreere"
		count = 0
		self.write(cr, uid, ids[0], {'state': 'revised'})
		var = rec.revision+1
		count = count  + 1
		vals = {
				'state': 'draft',
				'revision': var,
				'revision_count': count,
				}
		new_rec = self.copy(cr, uid, ids[0], vals, context)
		return True	
			
	def app_quotation(self, cr, uid, ids, context=None):
		rfq_ven_obj = self.pool.get('kg.rfq.vendor.selection')
		rfq_ven_lin_obj = self.pool.get('kg.rfq.vendor.selection.line')
		line_obj = self.pool.get('kg.quotation.requisition.line')
		quo_lin_obj = self.pool.get('kg.quote.pi.line')
		for custom in self.browse(cr, uid, ids, context):
			for lines in custom.line_ids:
				for quotes in lines.pi_line_ids:
					quo_lin_obj.write(cr,uid,quotes.id,{'state':'approved'})
				line_obj.write(cr,uid,lines.id,{'state':'approved'})
			rfq_ven_rec = rfq_ven_obj.browse(cr, uid, custom.rfq_no_id.id)
			rfq_ven_obj.write(cr, uid, [custom.rfq_no_id.id], {'state':'rfq_approved'})
			self.write(cr, uid, ids, {'state':'approved'})
		
		return True
		
	def rej_quotation(self, cr, uid, ids, context=None):
		for custom in self.browse(cr, uid, ids, context):
			self.write(cr, uid, ids, {'state':'reject'})
		return True	
		
	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []		
		for rec in self.browse(cr,uid,ids):	
			if rec.state not in ('draft'):				
				raise osv.except_osv(_('Warning!'),
						_('You can not delete this entry !!'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
	
	def _lines_check(self,cr,uid,ids,context = None):
		quote_pi_obj = self.pool.get('kg.quote.pi.line')
		entry = self.browse(cr,uid,ids[0])
		if entry.state!='draft':
			if not entry.line_ids:
				return False
			else:
				for loop in entry.line_ids:
					if loop.cmp_flag == True:
						for items in loop.pi_line_ids:
							if items.vendors_price<=0:
								return False
		return True
			
	_constraints = [
			(_lines_check, 'Please enter Unit Price', ['']),
		]	
kg_quotation_requisition_header()

class kg_quotation_requisition_line(osv.osv):
	_name = 'kg.quotation.requisition.line'
	_order = 'id desc'
	
	_columns = {
		
		'header_id': fields.many2one('kg.quotation.requisition.header', 'Quotation Header'),
		'rfq_ven_id': fields.many2one('kg.rfq.vendor.selection', 'RFQ No.'),
		'name': fields.char('RFQ No', size=32, readonly=True),
		'rfq_date': fields.date('RFQ Date', readonly=True),
		'due_date': fields.date('Due Date', readonly=True),
		'user_id': fields.many2one('res.users', 'Requested By'),
		'user_ref_id': fields.many2one('res.users', 'Ref User'),
		'partner_id':fields.many2one('res.partner','Vendor',size=120,readonly=True,),
		'partner_address': fields.char('Partner Address',size=200, readonly=True, ),
		'email':fields.char('Email', size=128,readonly=True,),
		'mail_flag': fields.boolean('Vendor Mail'),
		'cmp_flag': fields.boolean('Allow Vendor For Comparison'),
		'state': fields.selection([('draft', 'Draft'),('approved', 'Approved'),('reject', 'Reject')], 'State',readonly=True),
		'freight_type':fields.selection([('Inclusive','Inclusive'),('Extra','Extra'),('To Pay','To Pay'),('Paid','Paid'),('Extra at our Cost','Extra at our Cost')], 'Freight'), 		
		'tax_type': fields.selection([('inclusive', 'Inclusive'),('exclusive', 'Exclusive'),], 'Tax'),
		'other_charges': fields.selection([('applicable', 'Applicable'),('notapplicable', 'Not Applicable'),], 'Other Charges'),
		'pi_line_ids': fields.one2many('kg.quote.pi.line', 'header_id', 'PI Lines', readonly=False, ),
		'line_state': fields.selection([('pending','Pending'),('submit','Submitted')],'Status',readonly=True),
		'remarks': fields.text('RFQ Remarks'),
		'reject_remark': fields.text('Reject Remarks'),
		'total_amt': fields.float('Total Amount'),
		
	}
	
	_defaults = {
	
		'line_state': 'pending',
		'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
		'rfq_date': lambda *a: time.strftime('%Y-%m-%d'),
		'state': 'draft',
		'cmp_flag': True,
		'name': '/',
		
		}

	def create_revision(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		quote_lines_ids = self.pool.get('kg.quote.pi.line').search(cr, uid, [('header_id','=',rec.id)], context=context)
		self.write(cr, uid, ids[0], {'state': 'revised'})
		var = rec.revision+1
		vals = {
				'state': 'draft',
				'revision': var,
				}
		new_rec = self.copy(cr, uid, ids[0], vals, context)
		return True	
	
	def entry_submit(self, cr, uid, ids, context=None):		
		rfq_ven_obj = self.pool.get('kg.rfq.vendor.selection')
		rfq_ven_lin_obj = self.pool.get('kg.rfq.vendor.selection.line')
		line_obj = self.pool.get('kg.quotation.requisition.line')
		quo_lin_obj = self.pool.get('kg.quote.pi.line')
		total = 0
		for custom in self.browse(cr, uid, ids, context):			
			for quotes in custom.pi_line_ids:
				total += quotes.vendors_value			
				quo_lin_obj.write(cr,uid,quotes.id,{'state':'approved'})
			line_obj.write(cr,uid,custom.id,{'state':'approved','total_amt':total})
			rfq_ven_rec = rfq_ven_obj.browse(cr, uid, quotes.rfq_no_id.id)
			
			self_rec = self.search(cr,uid,[('rfq_ven_id','=',custom.rfq_ven_id.id)])
			app_rec = self.search(cr,uid,[('rfq_ven_id','=',custom.rfq_ven_id.id),('state','!=','draft')])
			if len(self_rec) == len(app_rec):			
				rfq_ven_obj.write(cr, uid, [quotes.rfq_no_id.id], {'state':'rfq_approved'})
			else:
				pass
			self.write(cr, uid, ids, {'state':'approved'})			
		return True	
		
	def entry_reject(self, cr, uid, ids, context=None):		
		rfq_ven_obj = self.pool.get('kg.rfq.vendor.selection')
		rfq_ven_lin_obj = self.pool.get('kg.rfq.vendor.selection.line')
		line_obj = self.pool.get('kg.quotation.requisition.line')
		quo_lin_obj = self.pool.get('kg.quote.pi.line')
		total = 0
		for custom in self.browse(cr, uid, ids, context):
			if custom.reject_remark:						
				for quotes in custom.pi_line_ids:
					total += quotes.vendors_value			
					quo_lin_obj.write(cr,uid,quotes.id,{'state':'reject'})
				line_obj.write(cr,uid,custom.id,{'state':'reject','total_amt':total})
				rfq_ven_rec = rfq_ven_obj.browse(cr, uid, quotes.rfq_no_id.id)
				
				self_rec = self.search(cr,uid,[('rfq_ven_id','=',custom.rfq_ven_id.id)])
				app_rec = self.search(cr,uid,[('rfq_ven_id','=',custom.rfq_ven_id.id),('state','!=','draft')])
				print"self_rec",len(self_rec)
				print"len(app_rec)",len(app_rec)
				if len(self_rec) == len(app_rec):			
					rfq_ven_obj.write(cr, uid, [quotes.rfq_no_id.id], {'state':'rfq_approved'})
				else:
					pass
				self.write(cr, uid, ids, {'state':'reject'})	
			else:
				raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter the remarks in Reject remarks field !!'))		
		return True	
		
	def _entry_date_check(self,cr,uid,ids,context = None):
		entry = self.browse(cr,uid,ids[0])
		for item in entry.pi_line_ids:			
			if item.ven_del_date != False:			
				if item.ven_del_date < entry.rfq_date :
					return False				
			return True
	
	
	
kg_quotation_requisition_line()

class kg_quote_pi_line(osv.osv):
	_name = 'kg.quote.pi.line'
	_order = 'id desc'
	
	def _value_calculation(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		for entry in self.browse(cr, uid, ids, context=context):
			res[entry.id] = {
				'vendors_value': 0.0,
			}
			res[entry.id]['vendors_value']= (round((entry.quotation_qty * entry.vendors_price),0))
		return res
	
	_columns = {
		'header_id': fields.many2one('kg.quotation.requisition.line', 'Quotation Line'),
		'rfq_no_id': fields.many2one('kg.rfq.vendor.selection', 'rfq no'),
		'revision': fields.integer('Revision'),
		'name': fields.char('RFQ No', size=32, readonly=True),
		'state': fields.selection([('draft', 'Draft'),('approved', 'Approved'),('revised', 'Revised'),('reject', 'Reject')], 'State'),
		'product_id': fields.many2one('product.product', 'Product', readonly=True),
		'product_name': fields.related('product_id', 'name', type='char', string='Product Name', readonly=True, store=True, size=300),
		'product_uom_id': fields.related('product_id','uom_id', type='many2one', relation='product.uom', string='Product UOM', store=True,readonly=True),
		'requested_qty': fields.float('Purchase Indent Approved Qty', digits=(16,3),readonly=True),
		'quotation_qty': fields.float('RFQ Qty', digits=(16,3),readonly=True),
		'partner_id':fields.many2one('res.partner','Vendor',size=120,readonly=True,),
		'partner_address': fields.char('Partner Address',size=200, readonly=True, ),
		'partner_name': fields.related('partner_id','name',type='char', string="Vendor Name", size=200, store=True),
		'vendors_price':fields.float('Unit Price',required=True),
		'brand_id': fields.many2one('kg.brand.master','Brand', readonly=True),
		'del_date': fields.date('Delivery Date', readonly=True),
		'ven_del_date': fields.date('Vendor Delivery Date'),
		'vendors_value': fields.function(_value_calculation,  string='Delivery Charges', multi="sums", help="The amount without tax", type='float',store=True,track_visibility='always'),
		
	}
	
	_defaults = {
		'state': 'draft',
		'name': '/',
	}
	
	def onchange_price(self, cr, uid, ids, quotation_qty,vendors_price,vendors_value):
		val = {'vendors_value':''}
		qty = quotation_qty
		price = vendors_price
		tot = qty*price
		val = {'vendors_value':tot}
		return {'val': val}	
	
	
kg_quote_pi_line()

class kg_quotation_entry_header(osv.osv):
	_name = 'kg.quotation.entry.header'
	_order = 'id desc'
	_columns = {
		'name': fields.char('Quotation No.', size=500,readonly=True),
		'rfq_name': fields.char('Alias Name', size=500),
		'comparision_date':fields.date('Comparison Date', readonly=True),
		'rfq_date':fields.date('RFQ Date'),
		'user_id': fields.many2one('res.users', 'Requested By'),
		'rfq_no_id':fields.many2one('kg.rfq.vendor.selection', 'RFQ No', domain="[('state','=','rfq_approved'), ('visible_quote','=',0)]",required=True, ), 
		'state': fields.selection([('draft', 'Draft'),('confirmed', 'WFA'),('approved', 'Approved'),('cancel', 'Cancel'),('po_generate', 'PO Generate'),], 'State'),
		'line_ids': fields.one2many('kg.quotation.entry.lines', 'header_id', string='quotes',readonly=True),
		'product_id': fields.related('line_ids','product_id', type='many2one', relation='product.product', string='Product', domain="[('defaultproduct','!=',1),('new_state','=','approved')]"),		
		'quote_list_flag': fields.boolean('Quote List Flag'),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'line_ids_vendor1': fields.one2many('kg.quotation.entry.lines', 'header_id', string='quotes',),
		'line_ids_vendor2': fields.one2many('kg.quotation.entry.lines', 'header_id', string='quotes',),
		'line_ids_vendor3': fields.one2many('kg.quotation.entry.lines', 'header_id', string='quotes',),
		'line_ids_vendor4': fields.one2many('kg.quotation.entry.lines', 'header_id', string='quotes',),
		'line_ids_vendor5': fields.one2many('kg.quotation.entry.lines', 'header_id', string='quotes',),
		'vendor_1_id': fields.many2one('res.partner', 'Vendor 1' , readonly=True),
		'vendor_2_id': fields.many2one('res.partner', 'Vendor 2' , readonly=True),
		'vendor_3_id': fields.many2one('res.partner', 'Vendor 3' , readonly=True),
		'vendor_4_id': fields.many2one('res.partner', 'Vendor 4' , readonly=True),
		'vendor_5_id': fields.many2one('res.partner', 'Vendor 5' , readonly=True),
		'vendor_1_name': fields.char('Vendor One Name', size=500, ),
		'vendor_2_name': fields.char('Vendor Two Name', size=500, ),
		'vendor_3_name': fields.char('Vendor Three Name', size=500, ),
		'vendor_4_name': fields.char('Vendor Four Name', size=500, ),
		'vendor_5_name': fields.char('Vendor Five Name', size=500, ),
		'vendor_1_flag': fields.boolean('Vendor Flag 1'),
		'vendor_2_flag': fields.boolean('Vendor Flag 2'),
		'vendor_3_flag': fields.boolean('Vendor Flag 3'),
		'vendor_4_flag': fields.boolean('Vendor Flag 4'),
		'vendor_5_flag': fields.boolean('Vendor Flag 5'),
		
		'generate_po_flag': fields.boolean('PO Flag'),
		
		'vendor_1_freight': fields.char('Vendor Freight Type.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_2_freight': fields.char('Vendor Freight Type.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_3_freight': fields.char('Vendor Freight Type.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_4_freight': fields.char('Vendor Freight Type.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_5_freight': fields.char('Vendor Freight Type.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		
		'vendor_1_tax': fields.char('Vendor Tax Type.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_2_tax': fields.char('Vendor Tax Type.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_3_tax': fields.char('Vendor Tax Type.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_4_tax': fields.char('Vendor Tax Type.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_5_tax': fields.char('Vendor Tax Type.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		
		'vendor_1_others': fields.char('Vendor Others.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_2_others': fields.char('Vendor Others.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_3_others': fields.char('Vendor Others.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_4_others': fields.char('Vendor Others.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_5_others': fields.char('Vendor Others.', size=30, readonly=True, states={'draft':[('readonly',True)]}),
		'vendor_reference_no_vendor_1': fields.char('Vendor Reference No.', size=30, readonly=True, states={'draft':[('readonly',False)]}),
		'vendor_reference_no_vendor_2': fields.char('Vendor Reference No.', size=30, readonly=True, states={'draft':[('readonly',False)]}),
		'vendor_reference_no_vendor_3': fields.char('Vendor Reference No.', size=30, readonly=True, states={'draft':[('readonly',False)]}),
		'vendor_reference_no_vendor_4': fields.char('Vendor Reference No.', size=30, readonly=True, states={'draft':[('readonly',False)]}),
		'vendor_reference_no_vendor_5': fields.char('Vendor Reference No.', size=30, readonly=True, states={'draft':[('readonly',False)]}),
		
		'vendor_reference_date_vendor_1': fields.date('Vendor Reference Date', readonly=True, states={'draft':[('readonly',False)]}),
		'vendor_reference_date_vendor_2': fields.date('Vendor Reference Date', readonly=True, states={'draft':[('readonly',False)]}),
		'vendor_reference_date_vendor_3': fields.date('Vendor Reference Date', readonly=True, states={'draft':[('readonly',False)]}),
		'vendor_reference_date_vendor_4': fields.date('Vendor Reference Date', readonly=True, states={'draft':[('readonly',False)]}),
		'vendor_reference_date_vendor_5': fields.date('Vendor Reference Date', readonly=True, states={'draft':[('readonly',False)]}),
		
		'quotation_validity_vendor_1': fields.integer('Quotation Validity', readonly=True, states={'draft':[('readonly',False)]}),
		'quotation_validity_vendor_2': fields.integer('Quotation Validity', readonly=True, states={'draft':[('readonly',False)]}),
		'quotation_validity_vendor_3': fields.integer('Quotation Validity', readonly=True, states={'draft':[('readonly',False)]}),
		'quotation_validity_vendor_4': fields.integer('Quotation Validity', readonly=True, states={'draft':[('readonly',False)]}),
		'quotation_validity_vendor_5': fields.integer('Quotation Validity', readonly=True, states={'draft':[('readonly',False)]}),
		
		'enquiry_type_vendor_1': fields.selection([('phone','Phone'),('email','Email'),('fax','Fax'),('others','Others')],'Enquiry Type', readonly=True, states={'draft':[('readonly',False)]}),
		'enquiry_type_vendor_2': fields.selection([('phone','Phone'),('email','Email'),('fax','Fax'),('others','Others')],'Enquiry Type', readonly=True, states={'draft':[('readonly',False)]}),
		'enquiry_type_vendor_3': fields.selection([('phone','Phone'),('email','Email'),('fax','Fax'),('others','Others')],'Enquiry Type', readonly=True, states={'draft':[('readonly',False)]}),
		'enquiry_type_vendor_4': fields.selection([('phone','Phone'),('email','Email'),('fax','Fax'),('others','Others')],'Enquiry Type', readonly=True, states={'draft':[('readonly',False)]}),
		'enquiry_type_vendor_5': fields.selection([('phone','Phone'),('email','Email'),('fax','Fax'),('others','Others')],'Enquiry Type', readonly=True, states={'draft':[('readonly',False)]}),
		'comparison_remarks': fields.text('Remarks'),
		'remarks': fields.text('Approve/Reject Remarks'),
	}
	
	_defaults = {
		'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
		'comparision_date': lambda *a: time.strftime('%Y-%m-%d'),
		'state': 'draft',
		'vendor_1_name': 'Vendor One',
		'vendor_2_name': 'Vendor Two',
		'vendor_3_name': 'Vendor Three',
		'vendor_4_name': 'Vendor Four',
		'vendor_5_name': 'Vendor Five',
		'quote_list_flag': False,
		'vendor_1_flag': True,
		'vendor_2_flag': False,
		'vendor_3_flag': False,
		'vendor_4_flag': False,
		'vendor_5_flag': False,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.quotation.entry.header', context=c),
	}
	
	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []		
		for rec in self.browse(cr,uid,ids):	
			if rec.state not in ('draft'):				
				raise osv.except_osv(_('Warning!'),
						_('You can not delete this entry !!'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
			
	def select_vendor_1(self, cr, uid, ids, context=None):
		for hdr in self.browse(cr, uid, ids, context):
			cr.execute('''update kg_quotation_entry_lines set 
			vendor_1_select=%s,vendor_2_select=%s,vendor_3_select=%s,vendor_4_select=%s,vendor_5_select=%s
			where header_id = %s''',(True,False,False,False,False,hdr.id))
		return True
	
	def select_vendor_2(self, cr, uid, ids, context=None):
		for hdr in self.browse(cr, uid, ids, context):
			cr.execute('''update kg_quotation_entry_lines set 
			vendor_1_select=%s,vendor_2_select=%s,vendor_3_select=%s,vendor_4_select=%s,vendor_5_select=%s
			where header_id = %s''',(False,True,False,False,False,hdr.id))
		return True
		
	def select_vendor_3(self, cr, uid, ids, context=None):
		for hdr in self.browse(cr, uid, ids, context):
			cr.execute('''update kg_quotation_entry_lines set 
			vendor_1_select=%s,vendor_2_select=%s,vendor_3_select=%s,vendor_4_select=%s,vendor_5_select=%s
			where header_id = %s''',(False,False,True,False,False,hdr.id))
		return True
	
	def select_vendor_4(self, cr, uid, ids, context=None):
		for hdr in self.browse(cr, uid, ids, context):
			cr.execute('''update kg_quotation_entry_lines set 
			vendor_1_select=%s,vendor_2_select=%s,vendor_3_select=%s,vendor_4_select=%s,vendor_5_select=%s
			where header_id = %s''',(False,False,False,True,False,hdr.id))
		return True
	
	def select_vendor_5(self, cr, uid, ids, context=None):
		for hdr in self.browse(cr, uid, ids, context):
			cr.execute('''update kg_quotation_entry_lines set 
			vendor_1_select=%s,vendor_2_select=%s,vendor_3_select=%s,vendor_4_select=%s,vendor_5_select=%s
			where header_id = %s''',(False,False,False,False,True,hdr.id))
		return True	
	
	def onchange_partner_id(self, cr, uid, ids, rfq_no_id):
		rfq_par_obj = self.pool.get('kg.rfq.vendor.selection')
		if rfq_no_id:
			rfq_par_rec = rfq_par_obj.browse(cr, uid, rfq_no_id)
			return {
					'value': 
					{
					'rfq_name' : rfq_par_rec.rfq_name,
					'rfq_date' : rfq_par_rec.quotation_date,
					}
					}
					

		
	def list_quotations(self, cr, uid, ids, context=None):
		rfq_ven_lin_obj = self.pool.get('kg.rfq.vendor.selection.line')
		rfq_ven_list_obj = self.pool.get('kg.rfq.vendor.list')
		line_obj = self.pool.get('kg.quotation.entry.lines') 
		quote_pi_line_obj = self.pool.get('kg.quote.pi.line') 
		qline_obj = self.pool.get('kg.quotation.requisition.line') 
		q_obj = self.pool.get('kg.quotation.requisition.header') 
		vendor_1_id = vendor_2_id = vendor_3_id = vendor_4_id = vendor_5_id = quote_1_id = quote_2_id = quote_3_id = quote_4_id = quote_5_id = 0
		vendor_1 = vendor_2 = vendor_3 = vendor_4 = vendor_5 = ''
		ven_1_qty = ven_2_qty = ven_3_qty = ven_4_qty = ven_5_qty = ven_1_price = ven_2_price = ven_3_price = ven_4_price = ven_5_price = ven_1_val = ven_2_val = ven_3_val = ven_4_val = ven_5_val = 0.00
		ven_1_flag = True
		ven_2_flag = ven_3_flag = ven_4_flag = ven_5_flag = False		
		
		price_sample = []
		value_sample = []
		partners_list = []		
		d = {}
		for entry in self.browse(cr, uid, ids, context):
			del_sql = """ delete from kg_quotation_entry_lines where header_id=%s """ %(ids[0])
			cr.execute(del_sql)
			rfq_ven_lin_ids = rfq_ven_lin_obj.search(cr, uid, [('header_id','=',entry.rfq_no_id.id)])
			rfq_ven_list_ids = rfq_ven_list_obj.search(cr, uid, [('header_id','=',entry.rfq_no_id.id)])
			q_ids = q_obj.search(cr, uid, [('rfq_no_id','=',entry.rfq_no_id.id)])
			qline_ids = qline_obj.search(cr, uid, [('header_id','=',q_ids[0]),('cmp_flag','=',True),('state','=','approved')])
			for loop in qline_ids:
				record = qline_obj.browse(cr,uid,loop)
				price_sub_list = []
				value_sub_list = []
				sub_partners_list = []		
				for lines in record.pi_line_ids:
					price_sub_list.append(lines.vendors_price)
					value_sub_list.append(lines.vendors_value)
					sub_partners_list.append(lines.partner_id.id)
				result = list(set(sub_partners_list))
				sub_partners_list = result
				price_sample.append(price_sub_list)
				value_sample.append(value_sub_list)
				partners_list.append(sub_partners_list)
			for rfq_lin in rfq_ven_lin_ids:
				indx_0 = 0
				indx_1 = 0
				indx_2 = 0
				indx_3 = 0
				indx_4 = 0
				indx = rfq_ven_lin_ids.index(rfq_lin)
				rec_lin = rfq_ven_lin_obj.browse(cr,uid,rfq_lin)
				cmp_list = []
				for num in range(0,len(price_sample)):
					dump = sum(value_sample[num])
					cmp_list.append(dump)
				list1 = partners_list
				list2 = cmp_list
				if len(list2)==1:
					indx_0 = 0
				if len(list2)==2:
					indx_0 = 0
					indx_1 = 1
				if len(list2)==3:
					indx_0 = 0
					indx_1 = 1
					indx_2 = 2
				if len(list2)==4:
					indx_0 = 0
					indx_1 = 1
					indx_2 = 2
					indx_3 = 3
				if len(list2)==5:
					indx_0 = 0																				
					indx_1 = 1
					indx_2 = 2																				
					indx_3 = 3																				
					indx_4 = 4																				
				for i in range(0,len(cmp_list)):
					a = list1[i][0]
					d[a] = list2[i]
				for k, v in d.items():
					k, v
				d_sorted_by_value = sorted(d.items(), key=lambda x: x[1])
				d_len = len(d_sorted_by_value)
				if (d_len-(d_len-indx_0))==0:
					rec_ven = rfq_ven_list_obj.browse(cr,uid,rfq_ven_list_ids[0])
					vendor_1_id = d_sorted_by_value[0][0]
					quote_pi_line_ids = quote_pi_line_obj.search(cr, uid, [('rfq_no_id','=',entry.rfq_no_id.id),('product_id','=',rec_lin.product_id.id),('partner_id','=',vendor_1_id)])
					quote_pi_line_rec = quote_pi_line_obj.browse(cr,uid,quote_pi_line_ids[0])
					vendor_1 = quote_pi_line_rec.partner_name
					ven_1_flag = True
					ven_1_qty = quote_pi_line_rec.quotation_qty
					ven_1_price = quote_pi_line_rec.vendors_price
					ven_1_val = quote_pi_line_rec.vendors_value
				if (d_len-(d_len-indx_1))==1:
					rec_ven = rfq_ven_list_obj.browse(cr,uid,rfq_ven_list_ids[1])
					vendor_2_id = d_sorted_by_value[1][0]
					quote_pi_line_ids = quote_pi_line_obj.search(cr, uid, [('rfq_no_id','=',entry.rfq_no_id.id),('product_id','=',rec_lin.product_id.id),('partner_id','=',vendor_2_id)])
					quote_pi_line_rec = quote_pi_line_obj.browse(cr,uid,quote_pi_line_ids[0])
					vendor_2 = quote_pi_line_rec.partner_name
					ven_2_flag = True
					ven_2_qty = quote_pi_line_rec.quotation_qty
					ven_2_price = quote_pi_line_rec.vendors_price
					ven_2_val = quote_pi_line_rec.vendors_value
				if (d_len-(d_len-indx_2))==2:
					rec_ven = rfq_ven_list_obj.browse(cr,uid,rfq_ven_list_ids[2])
					vendor_3_id = d_sorted_by_value[2][0]
					quote_pi_line_ids = quote_pi_line_obj.search(cr, uid, [('rfq_no_id','=',entry.rfq_no_id.id),('product_id','=',rec_lin.product_id.id),('partner_id','=',vendor_3_id)])
					quote_pi_line_rec = quote_pi_line_obj.browse(cr,uid,quote_pi_line_ids[0])
					vendor_3 = quote_pi_line_rec.partner_name
					ven_3_flag = True
					ven_3_qty = quote_pi_line_rec.quotation_qty
					ven_3_price = quote_pi_line_rec.vendors_price
					ven_3_val = quote_pi_line_rec.vendors_value
				if (d_len-(d_len-indx_3))==3:
					rec_ven = rfq_ven_list_obj.browse(cr,uid,rfq_ven_list_ids[3])
					vendor_4_id = d_sorted_by_value[3][0]
					quote_pi_line_ids = quote_pi_line_obj.search(cr, uid, [('rfq_no_id','=',entry.rfq_no_id.id),('product_id','=',rec_lin.product_id.id),('partner_id','=',vendor_4_id)])
					quote_pi_line_rec = quote_pi_line_obj.browse(cr,uid,quote_pi_line_ids[0])
					vendor_4 = quote_pi_line_rec.partner_name
					ven_4_flag = True
					ven_4_qty = quote_pi_line_rec.quotation_qty
					ven_4_price = quote_pi_line_rec.vendors_price
					ven_4_val = quote_pi_line_rec.vendors_value
				if (d_len-(d_len-indx_4))==4:
					rec_ven = rfq_ven_list_obj.browse(cr,uid,rfq_ven_list_ids[4])
					vendor_5_id = d_sorted_by_value[4][0]
					quote_pi_line_ids = quote_pi_line_obj.search(cr, uid, [('rfq_no_id','=',entry.rfq_no_id.id),('product_id','=',rec_lin.product_id.id),('partner_id','=',vendor_5_id)])
					quote_pi_line_rec = quote_pi_line_obj.browse(cr,uid,quote_pi_line_ids[0])
					vendor_5 = quote_pi_line_rec.partner_name
					ven_5_flag = True
					ven_5_qty = quote_pi_line_rec.quotation_qty
					ven_5_price = quote_pi_line_rec.vendors_price
					ven_5_val = quote_pi_line_rec.vendors_value
				self.write(cr, uid, ids, 
					{
					'rfq_date' : entry.rfq_date,
					'rfq_name' : entry.rfq_name,
					'vendor_1_id': vendor_1_id,
					'vendor_2_id': vendor_2_id,
					'vendor_3_id': vendor_3_id,
					'vendor_4_id': vendor_4_id,
					'vendor_5_id': vendor_5_id,
					'vendor_1_name': vendor_1,
					'vendor_2_name': vendor_2,
					'vendor_3_name': vendor_3,
					'vendor_4_name': vendor_4,
					'vendor_5_name': vendor_5,
					'vendor_1_flag': ven_1_flag,
					'vendor_2_flag': ven_2_flag,
					'vendor_3_flag': ven_3_flag,
					'vendor_4_flag': ven_4_flag,
					'vendor_5_flag': ven_5_flag,
					'quote_list_flag': True,
					}
					)				
				vals = {
					'header_id': entry.id,
					'rfq_no_line_id':rec_lin.id,
					'product_id': rec_lin.product_id.id,
					'product_name': rec_lin.product_name,
					'vendor_1_id': vendor_1_id,
					'vendor_2_id': vendor_2_id,
					'vendor_3_id': vendor_3_id,
					'vendor_4_id': vendor_4_id,
					'vendor_5_id': vendor_5_id,
					'vendor_1_name': vendor_1,
					'vendor_2_name': vendor_2,
					'vendor_3_name': vendor_3,
					'vendor_4_name': vendor_4,
					'vendor_5_name': vendor_5,
					'vendor_1_select': False,
					'vendor_1_quantity':ven_1_qty,
					'vendor_1_price_input':ven_1_price,
					'vendor_1_value':ven_1_val,
					'vendor_2_select': False,
					'vendor_2_quantity':ven_2_qty,
					'vendor_2_price_input':ven_2_price,
					'vendor_2_value':ven_2_val,
					'vendor_3_select': False,
					'vendor_3_quantity':ven_3_qty,
					'vendor_3_price_input':ven_3_price,
					'vendor_3_value':ven_3_val,
					'vendor_4_select': False,
					'vendor_4_quantity':ven_4_qty,
					'vendor_4_price_input':ven_4_price,
					'vendor_4_value':ven_4_val,
					'vendor_5_select': False,
					'vendor_5_quantity':ven_5_qty,
					'vendor_5_price_input':ven_5_price,
					'vendor_5_value':ven_5_val,
					'state': 'draft',
					'requested_qty': rec_lin.requested_qty,
					'quotation_qty': rec_lin.quotation_qty,
				}
				line_id = line_obj.create(cr, uid, vals)
			for loop in qline_ids:
				record = qline_obj.browse(cr,uid,loop)
				ref = record.partner_id.id
				for key, value in vals.items():
					if ref == value:
						key_name = key
						key_name = key_name.replace("_", " ")
						key_name = [int(s) for s in key_name.split() if s.isdigit()]
						if key_name[0] == 1:
							freight_vendor_1 = record.freight_type
							tax_vendor_1 = record.tax_type
							other_vendor_1 = record.other_charges
							line_ids = line_obj.search(cr, uid, [('vendor_1_id', '=', ref)])
							self.write(cr, uid,ids, {'vendor_1_freight':freight_vendor_1,'vendor_1_tax':tax_vendor_1,'vendor_1_others':other_vendor_1})							
						if key_name[0] == 2:
							freight_vendor_2 = record.freight_type
							tax_vendor_2 = record.tax_type
							other_vendor_2 = record.other_charges
							line_ids = line_obj.search(cr, uid, [('vendor_2_id', '=', ref)])
							self.write(cr, uid, ids, {'vendor_2_freight':freight_vendor_2,'vendor_2_tax':tax_vendor_2,'vendor_2_others':other_vendor_2})									
						if key_name[0] == 3:
							freight_vendor_3 = record.freight_type
							tax_vendor_3 = record.tax_type
							other_vendor_3 = record.other_charges
							line_ids = line_obj.search(cr, uid, [('vendor_3_id', '=', ref)])
							self.write(cr, uid, ids, {'vendor_3_freight':freight_vendor_3,'vendor_3_tax':tax_vendor_3,'vendor_3_others':other_vendor_3})												
						if key_name[0] == 4:
							freight_vendor_4 = record.freight_type
							tax_vendor_4 = record.tax_type
							other_vendor_4 = record.other_charges
							line_ids = line_obj.search(cr, uid, [('vendor_4_id', '=', ref)])
							self.write(cr, uid, ids, {'vendor_4_freight':freight_vendor_4,'vendor_4_tax':tax_vendor_4,'vendor_4_others':other_vendor_4})											
						if key_name[0] == 5:
							freight_vendor_5 = record.freight_type
							tax_vendor_5 = record.tax_type
							other_vendor_5 = record.other_charges
							line_ids = line_obj.search(cr, uid, [('vendor_5_id', '=', ref)])
							self.write(cr, uid, ids, {'vendor_5_freight':freight_vendor_5,'vendor_5_tax':tax_vendor_5,'vendor_5_others':other_vendor_5})													
			for lines in entry.line_ids:
				count = 0
				value = 0.0
				if lines.vendor_1_value > 0.0:
					count = 1
					price = lines.vendor_1_value
				if count > 0 and lines.vendor_2_value < price and lines.vendor_2_value > 0.0:
					count = 2
					price = lines.vendor_2_value
				elif count <= 0 and lines.vendor_2_value > 0.0:
					count = 2
					price = lines.vendor_2_value
				if count > 0 and lines.vendor_3_value < price and lines.vendor_3_value > 0.0:
					count = 3
					price = lines.vendor_3_value
				elif count <= 0 and lines.vendor_3_value > 0.0:
					count = 3
					price = lines.vendor_3_value
				if count > 0 and lines.vendor_4_value < price and lines.vendor_4_value > 0.0:
					count = 4
					price = lines.vendor_4_value
				elif count <= 0 and lines.vendor_4_value > 0.0:
					count = 4
					price = lines.vendor_4_value
				if count > 0 and lines.vendor_5_value < price and lines.vendor_5_value > 0.0:
					count = 5
					price = lines.vendor_5_value
				elif count <= 0 and lines.vendor_5_value > 0.0:
					count = 5
					price = lines.vendor_5_value
				if count > 0:
					cr.execute('''update kg_quotation_entry_lines set color_highlight_vendor_%s = %s,vendor_%s_select=%s
					where id = %s''',(count,'highlight',count,True,lines.id))
		return True					
		
	def create(self, cr, uid, vals, context=None):			
		rfq_par_obj = self.pool.get('kg.rfq.vendor.selection')
		rfq_par_rec = rfq_par_obj.browse(cr, uid, vals.get('rfq_no_id'))
		vals.update({'rfq_name': rfq_par_rec.rfq_name,'rfq_date':rfq_par_rec.quotation_date})
		return super(kg_quotation_entry_header, self).create(cr, uid, vals, context=context)
		
	def write(self, cr, uid, ids, vals, context=None):
		for quo in self.browse(cr, uid, ids, context=context):
			vals.update({'rfq_name': quo.rfq_name,'rfq_date':quo.rfq_date})
		return super(kg_quotation_entry_header, self).write(cr, uid, ids, vals, context)				
	
	def send_for_approval(self, cr, uid, ids, context=None):
		count_list = []
		rec = self.browse(cr, uid, ids[0])
		line_obj = self.pool.get('kg.quotation.entry.lines')
		quote_obj = self.pool.get('kg.rfq.vendor.selection')
		line_ids = line_obj.search(cr, uid, [('header_id','=',rec.id)], context=context)
		for i in range(1,6):
			cr.execute("""select count(*) from kg_quotation_entry_lines where vendor_%s_select = 't' and header_id = %s """%(i,ids[0]))
			result = cr.fetchone()
			if result[0]>0:
				count_list.append(result[0])
		tmp_list = []
		for i in range(1,6):
			cr.execute('''select id from kg_quotation_entry_header where vendor_%s_flag = %s and id = %s''',(i,True,ids[0],))
			resultant = cr.fetchall()
			if resultant!=[]:
				tmp_list.append(i)
		if tmp_list !=[]:
			for loop in tmp_list:
				cr.execute('''select quotation_validity_vendor_%s from kg_quotation_entry_header where vendor_%s_flag = %s and id = %s''',(loop,loop,True,ids[0]))
				result = cr.fetchone()
				if result[0] == 0:
					raise osv.except_osv(_('Warning'),_('Quotation Validity Days should be Greater than Zero'))
		if len(line_ids) != sum(count_list):
			raise osv.except_osv(_('Warning'),_('Please Select All Line Items to Proceed'))
		for loop in line_ids:
			line_obj.write(cr, uid, loop, {'state':'approved'}, context=context)
		quote_obj.write(cr,uid, rec.rfq_no_id.id, {'visible_quote' : True})
		self.write(cr, uid, ids, {'state':'confirmed'})
		return True
	
	def approve_quote(self, cr, uid, ids, context=None):
		rec= self.browse(cr,uid,ids[0])
		self.write(cr, uid, ids, {'state':'approved'})
		return True
	
	def po_record_create(self, cr, uid, ids, vendor_id, vendor_count, context=None):
		quo_obj = self.pool.get('kg.rfq.vendor.selection')
		quo_line_obj = self.pool.get('kg.rfq.vendor.selection.line')
		po_obj = self.pool.get('purchase.order')
		po_lin_obj = self.pool.get('purchase.order.line')
		ven_obj = self.pool.get('res.partner')
		line_obj = self.pool.get('kg.quotation.entry.lines')
		for quo in self.browse(cr, uid, ids, context):
			cr.execute('''
			select 
			vendor_%s_id as vendor_id, vendor_%s_value as vendor_value,
			rfq_no_line_id from kg_quotation_entry_lines where header_id=%s  
			and vendor_%s_select = %s 
			 and id in (
			select id from kg_quotation_entry_lines 
			where header_id=%s group by id having sum(case when vendor_1_select then 1 else 0 end+case when vendor_2_select then 1 else 0 end+case when 
			vendor_3_select then 1 else 0 end+case when vendor_4_select then 1 else 0 end+case when vendor_5_select then 1 else 0 end)=1 ) ''',(vendor_count,vendor_count,quo.id,vendor_count,True,quo.id,))
			res = cr.dictfetchall()
			if res:
				res = res[0]
				quo_rec = quo_obj.browse(cr, uid, quo.rfq_no_id.id)
				cr.execute('''select rfq_no_id,vendor_%s_freight as vendor_freight,vendor_%s_tax as vendor_tax from kg_quotation_entry_header where id = (
				select distinct header_id from kg_quotation_entry_lines where vendor_%s_select = %s  and id in (
				select id from kg_quotation_entry_lines where header_id=%s group by id having sum(case when vendor_1_select then 1 else 0 end+case when vendor_2_select then 1 else 0 end+case when 
				vendor_3_select then 1 else 0 end+case when vendor_4_select then 1 else 0 end+case when vendor_5_select then 1 else 0 end)=1 ) )''',(vendor_count,vendor_count,vendor_count,True,quo.id,))
				result = cr.dictfetchall()
				result = result[0]
				user_obj = self.pool.get('res.users')
				user_rec = user_obj.browse(cr,uid,uid)
				dep_rec = user_rec.dep_name
				location = dep_rec.main_location.id
				com_obj = self.pool.get('res.company').search(cr,uid,([('id','=',user_rec.company_id.id)]))
				com_rec = self.pool.get('res.company').browse(cr,uid,com_obj[0])
				part_obj = self.pool.get('res.partner').search(cr,uid,([('id','=',com_rec.partner_id.id)]))
				part_rec = self.pool.get('res.company').browse(cr,uid,part_obj[0])
				address = (part_rec.street or '')+ ' ' + (part_rec.street2 or '') + '\n'+(part_rec.city.name or '')+ ',' +(part_rec.state_id.name or '') + '-' +(part_rec.country_id.name or '') + ','+ (part_rec.zip or '')					
				supplier = ven_obj.browse(cr, uid, res['vendor_id'])
				tot_add = (supplier.street or '')+ ' ' + (supplier.street2 or '') + '\n'+(supplier.city_id.name or '')+ ',' +(supplier.state_id.name or '') + '-' +(supplier.zip or '') + '\nPh:' + (supplier.phone or '')+ '\n' +(supplier.mobile or '')		
				po_vals = {
					'partner_id': res['vendor_id'],
					'term_price': result['vendor_tax'],
					'term_freight': result['vendor_freight'],
					'quot_ref_no': quo_rec.name,
					'location_id': location,					
					'amount_untaxed': res['vendor_value'],
					'amount_total': res['vendor_value'],
					'pricelist_id': 2,
					'po_type': 'fromquote',
					'company_id': 1,
					'state': 'draft',
					'entry_mode': 'auto',
					'amend_flag': False,
					'po_type': 'fromquote',
					'po_flag': True,
					'grn_flag': False,
					'bill_flag': False,
					'add_text' : tot_add or False,
					'delivery_address': self.pool.get('res.company').browse(cr,uid,1).street,
				}
				po_id = po_obj.create(cr, uid, po_vals)	
				if po_id:
					cr.execute('''select product_id as product_id,uom as product_uom_id,vendor_%s_price_input as price_unit,vendor_%s_id as partner_id,quotation_qty as group_qty,
					case when rfq_no_line_id is not null then
					(select purchase_requisition_line_id from kg_rfq_vendor_selection_line where id = rfq_no_line_id)
					end as pi_line_id,
					quotation_qty as received_qty,requested_qty as pi_qty,quotation_qty as pending_qty,quotation_qty as product_qty
					from kg_quotation_entry_lines where vendor_%s_select = %s and header_id = %s''',(vendor_count,vendor_count,vendor_count,True,quo.id,))
					resultant = cr.dictfetchall()	
					
					for items in resultant:
						po_line_vals = {
							'product_id': items['product_id'],
							'product_uom_id': items['product_uom_id'],
							'order_id': po_id,
							'price_unit': items['price_unit'],
							'partner_id': items['partner_id'],
							'invoice': False,
							'company_id': 1,
							'state': 'draft',
							'group_qty': items['group_qty'],
							'line_bill': False,
							'pi_line_id': items['pi_line_id'],
							'received_qty': 0,
							'group_flag': False,
							'po_type' :'fromquote',
							'pi_qty': items['pi_qty'],
							'line_state':'draft',
							'pending_qty': items['pending_qty'],
							'cancel_flag': False,
							'line_flag': False,
							'product_qty': items['product_qty'],
						}
						po_line_id = po_lin_obj.create(cr, uid, po_line_vals)						
						cr.execute('insert into kg_poindent_po_line(po_order_id,piline_id) values(%s,%s)', (po_id,items['pi_line_id']))	
		return True
	
	
	def po_generate(self, cr, uid, ids, context=None):
		for quo in self.browse(cr, uid, ids, context):
			for loop in quo.line_ids:
				count = 0
				if loop.vendor_1_select == True:
					count = count+1
				if loop.vendor_2_select == True:
					count = count+1
				if loop.vendor_3_select == True:
					count = count+1
				if loop.vendor_4_select == True:
					count = count+1
				if loop.vendor_5_select == True:
					count = count+1
				if count>1:
					raise osv.except_osv(_('Invalid action !'), _('Selection of same product against different vednors is not allowed!!!'))
			self.po_record_create(cr, uid, ids, quo.vendor_1_id.id, 1)
			self.po_record_create(cr, uid, ids, quo.vendor_2_id.id, 2)
			self.po_record_create(cr, uid, ids, quo.vendor_3_id.id, 3)
			self.po_record_create(cr, uid, ids, quo.vendor_4_id.id, 4)
			self.po_record_create(cr, uid, ids, quo.vendor_5_id.id, 5)
			self.write(cr, uid, ids, {'state':'po_generate'})
		return True	
	
	def reject_quote(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.remarks == False:
			raise osv.except_osv(_('Warning'),_('Please enter Approve/Reject Remarks'))
		self.write(cr, uid, ids, {'state':'cancel'})
		return True
		
	def _future_entry_date_check(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])		
		if rec.vendor_reference_date_vendor_1 != False:
			if rec.vendor_reference_date_vendor_1 < rec.rfq_date:
				return False
		if rec.vendor_reference_date_vendor_2 != False:
			if rec.vendor_reference_date_vendor_2 < rec.rfq_date:
				return False
		if rec.vendor_reference_date_vendor_3 != False:
			if rec.vendor_reference_date_vendor_3 < rec.rfq_date:
				return False
		if rec.vendor_reference_date_vendor_4 != False:
			if rec.vendor_reference_date_vendor_4 < rec.rfq_date:
				return False
		if rec.vendor_reference_date_vendor_5 != False:
			if rec.vendor_reference_date_vendor_5 < rec.rfq_date:
				return False
		return True
		
	
	
	_constraints = [		
		
		(_future_entry_date_check, 'System not allow to save with future date. !!',['']),   
		
		
	   ]	
		
kg_quotation_entry_header()


class kg_quotation_entry_lines(osv.osv):
	_name = 'kg.quotation.entry.lines'
	
	_columns = {
		'header_id': fields.many2one('kg.quotation.entry.header', 'Quo Header Id', required=True, ondelete='cascade'),
		'rfq_no_line_id':fields.many2one('kg.rfq.vendor.selection.line', 'RFQ', readonly=True),
		'product_id':fields.many2one('product.product', 'ProductDetails', readonly=True),
		'product_name': fields.related('product_id', 'name', type='char', string='Product Name', readonly=True, store=True, size=300),
		'uom': fields.related('product_id', 'uom_id', type='many2one', relation='product.uom', string='UOM', readonly=True, store=True),'vendor_1_id': fields.many2one('res.partner', 'Vendor 1' , readonly=True),
		'vendor_1_select':fields.boolean('Select'),
		'vendor_1_quantity':fields.float('Qty', readonly=True, digits=(16,3)),
		'vendor_1_price_input':fields.float('Rate', readonly=True, digits=(16,3)),
		'vendor_1_value':fields.float('Value', readonly=True, digits=(16,3)),
		'vendor_2_id': fields.many2one('res.partner', 'Vendor 2', readonly=True),
		'vendor_2_select':fields.boolean('Select'),
		'vendor_2_quantity':fields.float('Qty', readonly=True, digits=(16,3)),
		'vendor_2_price_input':fields.float('Rate', readonly=True, digits=(16,3)),
		'vendor_2_value':fields.float('Value', readonly=True, digits=(16,3)),
		'vendor_3_id': fields.many2one('res.partner', 'Vendor 3', readonly=True),
		'vendor_3_select':fields.boolean('Select'),
		'vendor_3_quantity':fields.float('Qty', readonly=True, digits=(16,3)),
		'vendor_3_price_input':fields.float('Rate', readonly=True, digits=(16,3)),
		'vendor_3_value':fields.float('Value', readonly=True, digits=(16,3)),
		'vendor_4_id': fields.many2one('res.partner', 'Vendor 4', readonly=True),
		'vendor_4_select':fields.boolean('Select'),
		'vendor_4_quantity':fields.float('Qty', readonly=True, digits=(16,3)),
		'vendor_4_price_input':fields.float('Rate', readonly=True, digits=(16,3)),
		'vendor_4_value':fields.float('Value', readonly=True, digits=(16,3)),
		'vendor_5_id': fields.many2one('res.partner', 'Vendor 5', readonly=True),
		'vendor_5_select':fields.boolean('Select'),
		'vendor_5_quantity':fields.float('Qty', readonly=True, digits=(16,3)),
		'vendor_5_price_input':fields.float('Rate', readonly=True, digits=(16,3)),
		'vendor_5_value':fields.float('Value', readonly=True, digits=(16,3)),
		'state': fields.selection([('draft', 'Draft'),('confirmed', 'Waiting For Approval'),('approved', 'Approved'),], 'State'),
		'requested_qty': fields.related('rfq_no_line_id', 'requested_qty', store=True, type='float', string='MRN Approved Qty', readonly=True),
		'quotation_qty': fields.related('rfq_no_line_id', 'quotation_qty', store=True, type='float', string='RFQ Qty', readonly=True),
		'color_highlight_vendor_1': fields.selection([('dont_highlight', 'Dont Highlight'),('highlight', 'Highlight'),], 'Color Highlight for Least Value'),
		'color_highlight_vendor_2': fields.selection([('dont_highlight', 'Dont Highlight'),('highlight', 'Highlight'),], 'Color Highlight for Least Value'),
		'color_highlight_vendor_3': fields.selection([('dont_highlight', 'Dont Highlight'),('highlight', 'Highlight'),], 'Color Highlight for Least Value'),
		'color_highlight_vendor_4': fields.selection([('dont_highlight', 'Dont Highlight'),('highlight', 'Highlight'),], 'Color Highlight for Least Value'),
		'color_highlight_vendor_5': fields.selection([('dont_highlight', 'Dont Highlight'),('highlight', 'Highlight'),], 'Color Highlight for Least Value'),
		'approved_date':fields.date('Approved Date'),
		'freight_vendor_1': fields.char('Freight Vendor 1' , size=64, required=True),
		'freight_vendor_2': fields.char('Freight Vendor 2' , size=64, required=True),
		'freight_vendor_3': fields.char('Freight Vendor 3' , size=64, required=True),
		'freight_vendor_4': fields.char('Freight Vendor 4' , size=64, required=True),
		'freight_vendor_5': fields.char('Freight Vendor 5' , size=64, required=True),
		'tax_vendor_1': fields.char('Tax Vendor 1' , size=64, required=True),
		'tax_vendor_2': fields.char('Tax Vendor 2' , size=64, required=True),
		'tax_vendor_3': fields.char('Tax Vendor 3' , size=64, required=True),
		'tax_vendor_4': fields.char('Tax Vendor 4' , size=64, required=True),
		'tax_vendor_5': fields.char('Tax Vendor 5' , size=64, required=True),
		'others_vendor_1': fields.char('Others Vendor 1' , size=64, required=True),
		'others_vendor_2': fields.char('Others Vendor 2' , size=64, required=True),
		'others_vendor_3': fields.char('Others Vendor 3' , size=64, required=True),
		'others_vendor_4': fields.char('Others Vendor 4' , size=64, required=True),
		'others_vendor_5': fields.char('Others Vendor 5' , size=64, required=True),
		
	}
	
	_defaults = {
		'state':'draft',
		'color_highlight_vendor_1':'dont_highlight',
		'color_highlight_vendor_2':'dont_highlight',
		'color_highlight_vendor_3':'dont_highlight',
		'color_highlight_vendor_4':'dont_highlight',
		'color_highlight_vendor_5':'dont_highlight',
		'freight_vendor_1':'',
		'freight_vendor_2':'',
		'freight_vendor_3':'',
		'freight_vendor_4':'',
		'freight_vendor_5':'',
		'tax_vendor_1':'',
		'tax_vendor_2':'',
		'tax_vendor_3':'',
		'tax_vendor_4':'',
		'tax_vendor_5':'',
		'others_vendor_1':'',
		'others_vendor_2':'',
		'others_vendor_3':'',
		'others_vendor_4':'',
		'others_vendor_5':'',
	}
	
kg_quotation_entry_lines()

