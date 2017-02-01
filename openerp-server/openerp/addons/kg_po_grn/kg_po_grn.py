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
dt_time = a.strftime('%Y-%m-%d ')

class kg_po_grn(osv.osv):

	def _amount_line_tax(self, cr, uid, line, context=None):
		val = 0.0
		amt_to_per = (line.kg_discount / (line.po_grn_qty * line.price_unit or 1.0 )) * 100
		kg_discount_per = line.kg_discount_per
		tot_discount_per = amt_to_per + kg_discount_per
		for c in self.pool.get('account.tax').compute_all(cr, uid, line.grn_tax_ids,
			line.price_unit * (1-(tot_discount_per or 0.0)/100.0), line.po_grn_qty, line.product_id,
			 line.po_grn_id.supplier_id)['taxes']:			 
			val += c.get('amount', 0.0)
		return val
	
	def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		vals ,tax_amt = 0 , 0
		cur_obj=self.pool.get('res.currency')
		grn_entry = self.browse(cr, uid, ids[0])
		for add in grn_entry.expense_line_id:
			vals = vals + add.expense_amt
			tax_amt = tax_amt + vals * add.tax.amount
		for order in self.browse(cr, uid, ids, context=context):
			res[order.id] = {
				'amount_untaxed': 0.0,
				'amount_tax': 0.0,
				'amount_total': 1110.0,
				'discount' : 0.0,
				'other_charge': 0.0,
				'additional_charge': 0.0,
			}
			val = val1 = val3 = line_total  = val4 = 0.0
			cur = order.supplier_id.property_product_pricelist_purchase.currency_id
			po_charges=order.value1 + order.value2	
			for line in order.line_ids:
				per_to_amt = (line.po_grn_qty * line.price_unit) * line.kg_discount_per / 100.00
				tot_discount = line.kg_discount
				val1 += line.tot_price 
				line_total += line.po_grn_qty * line.price_unit
				val += self._amount_line_tax(cr, uid, line, context=context)
				val3 += tot_discount	
				val4 += line.tot_price
			tax_am = val + tax_amt
			val1 = val1 + vals
			res[order.id]['line_amount_total']= (round(val4,0))
			res[order.id]['other_charge']=(round(po_charges,0))
			res[order.id]['amount_tax']=(round(tax_am,0))
			res[order.id]['additional_charge']=(round(vals,0))
			res[order.id]['amount_untaxed']=((round(val4,0)) - (round(val3,0)))
			res[order.id]['amount_total']=((round(val1 + res[order.id]['other_charge'] + tax_am,0)) - (round(val3,0)))
			res[order.id]['discount']=(round(val3,0))   
		return res
		
	def _get_journal(self, cr, uid, context=None):	
		journal_obj = self.pool.get('account.journal')
		res = journal_obj.search(cr, uid, [('type','=','sale')], limit=1)
		return res and res[0] or False

	def _get_currency(self, cr, uid, context=None):
		res = False
		journal_id = self._get_journal(cr, uid, context=context)
		if journal_id:
			journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
			res = journal.currency and journal.currency.id or journal.company_id.currency_id.id
		return res
		
	def _get_order(self, cr, uid, ids, context=None):
		result = {}
		for line in self.pool.get('po.grn.line').browse(cr, uid, ids, context=context):
			result[line.po_grn_id.id] = True
		return result.keys()
		
	def button_dummy(self, cr, uid, ids, context=None):
		return True
	
	_name = "kg.po.grn"
	_description = "PO GRN"
	_order = "grn_date desc,name desc"

	_columns = {
		
		'created_by':fields.many2one('res.users','Created By',readonly=True),
		'creation_date':fields.datetime('Created Date',required=True,readonly=True),
		'confirmed_by':fields.many2one('res.users','Confirmed By',readonly=True),
		'confirmed_date':fields.datetime('Confirmed Date',readonly=True),
		'approved_by':fields.many2one('res.users','Approved By',readonly=True),
		'approved_date':fields.datetime('Approved Date',readonly=True),
		'name': fields.char('GRN NO',readonly=True),
		'grn_date':fields.date('GRN Date',required=True,readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'dc_no': fields.char('DC NO', required=True,readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'dc_date':fields.date('DC Date',required=True, readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),		
		'po_id':fields.many2one('purchase.order', 'PO NO',
					domain="[('state','=','approved'), '&', ('order_line.pending_qty','>','0'), '&', ('grn_flag','=',False), '&', ('partner_id','=',supplier_id), '&', ('order_line.line_state','!=','cancel')]"), 
		'po_ids':fields.many2many('purchase.order', 'multiple_po', 'grn_id', 'po_id', 'PO Nos',
					domain="[('state','=','approved'), '&', ('order_line.pending_qty','>','0'), '&', ('grn_flag','=',False), '&',('partner_id','=',supplier_id), '&', ('order_line.line_state','!=','cancel')]",readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}), 
		'po_name': fields.char('PO NO',readonly=True),
		'order_no': fields.char('Order NO',readonly=True),
		'order_date': fields.char('Order Date',readonly=True),
		'pos_date': fields.char('PO Date',readonly=True),
		'po_date':fields.date('PO Date',readonly=True),
		'supplier_id':fields.many2one('res.partner','Supplier',domain=[('supplier','=',True),('sup_state','=','approved')],required=True),
		'billing_status': fields.selection([
			('applicable', 'Applicable'),
			('not_applicable', 'Not Applicable')], 'Billing Status',required=True,readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'inward_type': fields.many2one('kg.inwardmaster', 'Inward Type',domain=[('state','=','approved')],readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'line_ids':fields.one2many('po.grn.line','po_grn_id','Line Entry',readonly=False, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'department_id': fields.many2one('kg.depmaster','Department',readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'state': fields.selection([('item_load','Draft'),('draft', 'WFC'), ('confirmed', 'WFA'), ('done', 'Approved'), ('inv', 'Invoiced'), ('cancel', 'Cancelled'),('reject','Rejected')], 'Status',readonly=True),
		'type': fields.selection([('in', 'IN'), ('out', 'OUT'), ('internal', 'Internal')], 'Type'),
		'active':fields.boolean('Active'),
		'remark': fields.text('Approve/Reject',readonly=False),
		'po_so_remark':fields.text('PO/SO Remarks'),
		'cancel_remark': fields.text('Cancel Remarks'),				
		'confirm_flag':fields.boolean('Confirm Flag'),
		'approve_flag':fields.boolean('Expiry Flag'),
		'bill_flag':fields.boolean('Bill Flag'),
		'invoice_flag':fields.boolean('Invoice Flag'),
		'company_id':fields.many2one('res.company','Company'),
		'other_charge': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Other Charges(+)',
			 multi="sums", help="The amount without tax", track_visibility='always'),	  
		'discount': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total Discount(-)',
			store={
				'kg.po.grn': (lambda self, cr, uid, ids, c={}: ids, ['line_ids'], 10),
				'po.grn.line': (_get_order, ['price_unit', 'grn_tax_ids', 'kg_discount', 'po_grn_qty'], 10),
			}, multi="sums", help="The amount without tax", track_visibility='always'),
		'amount_untaxed': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Untaxed Amount',
			store={
				'kg.po.grn': (lambda self, cr, uid, ids, c={}: ids, ['line_ids'], 10),
				'po.grn.line': (_get_order, ['price_unit', 'grn_tax_ids', 'kg_discount', 'po_grn_qty'], 10),
			}, multi="sums", help="The amount without tax", track_visibility='always'),
	
		'amount_tax': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Taxes',store=True,
			 multi="sums", help="The tax amount"),
		'amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total',
			store=True,multi="sums",help="The total amount"),
		'pricelist_id':fields.many2one('product.pricelist', 'Pricelist'),
		'currency_id': fields.many2one('res.currency', 'Currency', readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'po_expenses_type1': fields.selection([('freight','Freight Charges'),('others','Others')], 'Expenses Type1', 
										readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'po_expenses_type2': fields.selection([('freight','Freight Charges'),('others','Others')], 'Expenses Type2', 
								 readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'value1':fields.float('Value1', readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'value2':fields.float('Value2',  readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'grn_type': fields.selection([('from_po','Purchase Order'),('from_so','Service Order'),('from_gp','Gate Pass')], 'GRN From', 
										required=True, readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),			  		
		'grn_dc': fields.selection([('dc_invoice','DC & Invoice'),('only_grn','Only grn')], 'GRN Type', 
										required=True, readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),			  										
		'so_id':fields.many2one('kg.service.order', 'SO NO',
					domain="[('state','=','approved'), '&', ('service_order_line.pending_qty','>','0'), '&', ('grn_flag','=',False), '&', ('partner_id','=',supplier_id),'&',('so_type','=','service')]"), 
		'so_ids':fields.many2many('kg.service.order', 'multiple_so', 'grn_id', 'so_id', 'SO NO',
					domain="[('state','=','approved'), '&', ('service_order_line.pending_qty','>','0'), '&', ('grn_flag','=',False), '&', ('partner_id','=',supplier_id),'&',('so_type','=','service')]"), 
		'gp_line_ids':fields.many2many('kg.gate.pass.line', 'multiple_gp', 'grn_id', 'gp_line_id', 'Gate Pass No',
					domain="[('gate_id.state','=','done'), '&', ('grn_pending_qty','>','0'), '&', ('so_flag','=',False)]"), 
		'gp_ids':fields.many2many('kg.gate.pass', 'multiple_gate', 'grn_id', 'gp_id', 'Gate Pass No',
					domain="[('state','=','done'), '&', ('gate_line.grn_pending_qty','>','0'), '&', ('gate_line.so_flag','=',False),'&', ('partner_id','=',supplier_id)]"), 
		'so_date':fields.date('SO Date',readonly=True),
		'so_name': fields.char('SO NO',readonly=True),
		'gp_date':fields.char('GP Date',readonly=True),
		'gp_name': fields.char('GP NO',readonly=True),
		'sos_date': fields.char('SO Date',readonly=True),
		'payment_type': fields.selection([('cash', 'Cash'), ('credit', 'Credit')], 'Payment Type', readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'reject_remark':fields.text('Cancel Remarks', readonly=True, states={'confirmed':[('readonly',False)]}),
		'sup_invoice_no':fields.char('Supplier Invoice No',size=200, readonly=False, states={'done':[('readonly',True)]}),
		'sup_invoice_date':fields.date('Supplier Invoice Date', readonly=False, states={'done':[('readonly',True)]}),
		'product_id': fields.related('line_ids','product_id', type='many2one', relation='product.product', string='Product',domain=[('state','=','approved')]),
		'notes': fields.text('Notes'),
#newly added
		'expense_line_id': fields.one2many('kg.po.grn.expense.track','expense_id','Expense Track',readonly=True, states={'item_load':[('readonly',False)],'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'company_id':fields.many2one('res.company','Company',readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'approved_by':fields.many2one('res.users','Approved By',readonly=True),
		'approved_date':fields.datetime('Approved Date',readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'update_date' : fields.datetime('Last Updated Date',readonly=True),
		'update_user_id' : fields.many2one('res.users','Last Updated By',readonly=True),		
		'additional_charge': fields.function(_amount_all,  string='Additional Charges(+)',
			 multi="sums", track_visibility='always'),	  
		'line_amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Net Amount',
			store=True, multi="sums",help="The total amount"),		
			 
		}
	
	_defaults = {
		
		'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'grn_date': lambda * a: time.strftime('%Y-%m-%d'),
		'created_by': lambda obj, cr, uid, context: uid,
		'state':'item_load',
		'type':'in',
		'name':'',
		'billing_status':'applicable',
		'active':True,
		'confirm_flag':False,
		'approve_flag':False,
		'company_id' : lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.po.grn', context=c),
	}
	
	### Back Entry Date ###
		
	def email_ids(self,cr,uid,ids,context = None):
		email_from = []
		email_to = []
		email_cc = []
		val = {'email_from':'','email_to':'','email_cc':''}
		ir_model = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		mail_form_ids = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		for ids in mail_form_ids:
			mail_form_rec = self.pool.get('kg.mail.settings').browse(cr,uid,ids)
			if mail_form_rec.doc_name.model == 'kg.po.grn':
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
	
	def sechedular_email_ids(self,cr,uid,ids,context = None):
		email_from = []
		email_to = []
		email_cc = []
		val = {'email_from':'','email_to':'','email_cc':''}
		ir_model = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		mail_form_ids = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		for ids in mail_form_ids:
			mail_form_rec = self.pool.get('kg.mail.settings').browse(cr,uid,ids)
			if mail_form_rec.sch_type == 'scheduler':
				s = mail_form_rec.sch_name
				s = s.lower()
				if s == 'goods receipt register':
					email_sub = mail_form_rec.subject
					email_from.append(mail_form_rec.name)
					mail_line_id = self.pool.get('kg.mail.settings.line').search(cr,uid,[('line_entry','=',ids)])
					for mail_id in mail_line_id:
						mail_line_rec = self.pool.get('kg.mail.settings.line').browse(cr,uid,mail_id)
						if mail_line_rec.to_address:
							email_to.append(mail_line_rec.mail_id)
						if mail_line_rec.cc_address:
							email_cc.append(mail_line_rec.mail_id)
		val['email_from'] = email_from
		val['email_to'] = email_to
		val['email_cc'] = email_cc
		return val
	
	def onchange_grn_date(self, cr, uid, ids, grn_date):
		today_date = today.strftime('%Y-%m-%d')
		back_list = []
		today_new = today.date()
		bk_date = date.today() - timedelta(days=3)
		back_date = bk_date.strftime('%Y-%m-%d')
		
		d1 = today_new
		d2 = bk_date

		delta = d1 - d2

		for i in range(delta.days + 1):
			bkk_date = d1 - timedelta(days=i)
			backk_date = bkk_date.strftime('%Y-%m-%d')
			back_list.append(backk_date)
		if grn_date > today_date:
			raise osv.except_osv(
					_('Warning'),
					_('GRN Date should be less than or equal to current date!'))
		return True
	
	# Onchange PO Date #
	
	def onchange_po_id(self, cr, uid, ids, po_ids, context=None):
		value = {'po_date': today,'po_so_remark':''}
		if len(po_ids) > 1:
			po_rec = self.pool.get('purchase.order').browse(cr, uid, po_ids[0][2][0], context=context)
			value = {'po_date': po_rec.date_order,'po_so_remark':po_rec.dep_project_name}
		return {'value': value}
		
	# Onchange SO Date #
		
	def onchange_so_id(self, cr, uid, ids, so_ids, context=None):	   
		value = {'so_date': today,'po_so_remark':''}
		if so_ids[0][2][0]:
			so_rec = self.pool.get('kg.service.order').browse(cr, uid, so_ids[0][2][0], context=context)
			value = {'so_date': so_rec.date,'po_so_remark':so_rec.origin}
		return {'value': value}	 
	
	def onchange_user_id(self, cr, uid, ids, created_by, context=None):	 
		value = {'department_id': ''}
		if created_by:
			user = self.pool.get('res.users').browse(cr, uid, created_by, context=context)
			value = {'department_id': user.dep_name.id}
		return {'value': value}

	def onchange_partner_id(self, cr, uid, ids, supplier_id):
		partner = self.pool.get('res.partner')	
		supplier_address = partner.address_get(cr, uid, [supplier_id], ['default'])
		supplier = partner.browse(cr, uid, supplier_id)
		return {'value': {
			'pricelist_id': supplier.property_product_pricelist_purchase.id,
			}}
	
	
	# Reject Method #
	
	def grn_reject(self, cr, uid, ids, context=None):
		grn = self.browse(cr, uid, ids[0])
		po_id = self.pool.get('purchase.order')
		so_id = self.pool.get('kg.service.order')
		if not grn.reject_remark:
			raise osv.except_osv(_('Remarks is must !!'), _('Enter Remarks for GRN Rejection !!!'))
		else:
			self.write(cr, uid, ids[0], {'state' : 'draft'})
		for line in grn.grn_line:
			if grn.grn_type == 'from_po':
				po_id.write(cr, uid, line.po_line_id.order_id.id, {'grn_flag' : False})
			if grn.grn_type == 'from_so':
				so_id.write(cr, uid, line.so_line_id.service_id.id, {'grn_flag' : False})   
			
		return True  

	# Delete Method #

	def unlink(self, cr, uid, ids, context=None):
		unlink_ids = []		  
		grn_rec = self.browse(cr, uid, ids[0])
		if grn_rec.state != 'draft':
			raise osv.except_osv(_('Invalid action !'), _('System not allow to delete Confirmed and Done state GRN !!'))
		else:
			unlink_ids.append(grn_rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		
	# GRN LINE Creation #
		
	def update_potogrn(self,cr,uid,ids,picking_id=False,context={}):
		### PO TO GRN ####
		
		
		self.write(cr,uid,ids[0],{'state':'draft'})
		po_id = False
		grn_entry_obj = self.browse(cr,uid,ids[0])
		if grn_entry_obj.state == 'confirmed':
			self.write(cr,uid,ids[0],{'state':'confirmed'})
		else:
			self.write(cr,uid,ids[0],{'state':'draft'})
		if grn_entry_obj.grn_type == 'from_po':
			cr.execute(""" select po_id from multiple_po where grn_id = %s and po_id in (select id from purchase_order where closing_flag = 'f') """ %(grn_entry_obj.id))
			po_data = cr.dictfetchall()
			po_obj=self.pool.get('purchase.order')
			po_grn_obj=self.pool.get('kg.po.grn')
			po_grn_line_obj=self.pool.get('po.grn.line')
			pol_obj = self.pool.get('purchase.order.line')
			#po_order = grn_entry_obj.po_id
			line_ids = map(lambda x:x.id,grn_entry_obj.line_ids)
			po_grn_line_obj.unlink(cr,uid,line_ids)
			value1 = 0
			value2 = 0
			po_list = []
			podate_list = []
			poremark_list = []
			for item in po_data:
				po_id = item['po_id']
				po_record = po_obj.browse(cr, uid, po_id)
				po_list.append(po_record.name)
				date_order = po_record.date_order
				date_order = datetime.strptime(date_order, '%Y-%m-%d')
				date_order = date_order.strftime('%d/%m/%Y')
				podate_list.append(date_order)
				po_name = ",".join(po_list)
				po_date = ",".join(podate_list)
				if po_record.dep_project_name:
					poremark_list.append(po_record.dep_project_name)
					po_remark = ",".join(poremark_list)
				else:
					po_remark = ""  
				po_expenses_type1 = po_record.po_expenses_type1 
				po_expenses_type2 = po_record.po_expenses_type2 
				value1 += po_record.value1 or 0
				value2 += po_record.value2 or 0
				self.write(cr,uid,ids[0],{
							'order_no':po_name,
							'order_date':po_date,
							'po_name':po_name,
							'pos_name':po_date,
							'po_expenses_type1':po_expenses_type1,
							'po_expenses_type2':po_expenses_type2,
							'value1':value1,
							'value2':value2,
							'po_so_remark':po_remark,
							})
				po_grn_id = grn_entry_obj.id
				order_lines=po_record.order_line
				for order_line in order_lines:
					if order_line.pending_qty > 0 and order_line.line_state != 'cancel':
						po_grn_line_obj.create(cr, uid, {
							'name': order_line.product_id.name or '/',
							'product_id': order_line.product_id.id,
							'brand_id':order_line.brand_id.id,
							'po_grn_qty': order_line.pending_qty,
							'po_qty':order_line.product_qty,
							'po_pending_qty':order_line.pending_qty,
							'uom_id': order_line.product_uom.id,
							'po_id': order_line.order_id.id,
							'location_id': po_record.partner_id.property_stock_supplier.id,
							'location_dest_id': po_record.location_id.id,
							'po_grn_id': po_grn_id,
							'state': 'confirmed',
							'po_line_id': order_line.id,
							'price_unit': order_line.price_unit,
							'tot_price': order_line.tot_price,
							'pi_line_id':order_line.pi_line_id.id,
							'grn_tax_ids': [(6, 0, [x.id for x in order_line.taxes_id])],
							'kg_discount_per':order_line.kg_discount_per,
							'kg_discount': order_line.kg_discount,
							'po_grn_date':grn_entry_obj.grn_date,
							'po_flag':'True',
							'inward_type':grn_entry_obj.inward_type.id,
							'billing_type':'cost',
							'order_no': order_line.order_id.name,
							'order_date': order_line.order_id.date_order,
						})
					else:
						print "NO Qty or Cancel"
		if grn_entry_obj.grn_type == 'from_so':  
				
			### SO TO GRN ####
		
			so_id = False
			
			cr.execute(""" select so_id from multiple_so where grn_id = %s """ %(grn_entry_obj.id))
			so_data = cr.dictfetchall()
			so_obj=self.pool.get('kg.service.order')
			po_grn_obj=self.pool.get('kg.po.grn')
			po_grn_line_obj=self.pool.get('po.grn.line')
			sol_obj = self.pool.get('kg.service.order.line')
			#so_order = grn_entry_obj.so_id
			line_ids = map(lambda x:x.id,grn_entry_obj.line_ids)
			po_grn_line_obj.unlink(cr,uid,line_ids)
			value1 = 0
			value2 = 0
			so_list = []
			sodate_list = []
			soremark_list = []
			for item in so_data:
				so_id = item['so_id']
				so_record = so_obj.browse(cr, uid, so_id)
				so_list.append(so_record.name)
				date_order = so_record.date
				date_order = datetime.strptime(date_order, '%Y-%m-%d')
				date_order = date_order.strftime('%d/%m/%Y')
				sodate_list.append(date_order)
				soremark_list.append(so_record.origin or 'Nil')
				so_name = ",".join(so_list)
				so_date = ",".join(sodate_list)
				so_remark = ",".join(soremark_list)
				po_expenses_type1 = so_record.po_expenses_type1 
				po_expenses_type2 = so_record.po_expenses_type2 
				value1 += so_record.value1 or 0
				value2 += so_record.value2 or 0
				self.write(cr,uid,ids[0],{
							'order_no':so_name,
							'order_date':so_date,
							'so_name':so_name,
							'sos_date':so_date,
							'po_expenses_type1':po_expenses_type1,
							'po_expenses_type2':po_expenses_type2,
							'value1':value1,
							'value2':value2,
							'po_so_remark':so_remark,
							})
				po_grn_id = grn_entry_obj.id
				order_lines=so_record.service_order_line
				for order_line in order_lines:
					if order_line.pending_qty > 0 and order_line.state != 'cancel':
						po_grn_line_obj.create(cr, uid, {
							'name': order_line.product_id.name or '/',
							'product_id': order_line.product_id.id,
							'brand_id':order_line.brand_id.id,
							'po_grn_qty': order_line.pending_qty,
							'so_qty':order_line.product_qty,
							'so_pending_qty':order_line.pending_qty,
							'uom_id': order_line.product_uom.id,
							'location_id': so_record.partner_id.property_stock_supplier.id,
							#'location_dest_id': so_order.location_id.id,
							'po_grn_id': po_grn_id,
							'state': 'confirmed',
							'so_line_id': order_line.id,
							'so_id': order_line.service_id.id,
							'price_unit': order_line.price_unit,
							'tot_price': order_line.tot_price,
							'si_line_id':order_line.soindent_line_id.id,
							'grn_tax_ids': [(6, 0, [x.id for x in order_line.taxes_id])],
							'kg_discount_per':order_line.kg_discount_per,
							'kg_discount': order_line.kg_discount,
							'po_grn_date':grn_entry_obj.grn_date,
							'so_flag':'True',
							'billing_type':'cost',
							'ser_no':order_line.ser_no,
							'serial_no':order_line.serial_no.id,
							'order_no': order_line.service_id.name,
							'order_date': order_line.service_id.date,
						})
						
					else:
						print "NO Qty or Cancel"
						
		if grn_entry_obj.grn_type == 'from_gp':  
			
			cr.execute(""" select gp_id from multiple_gate where grn_id = %s """ %(grn_entry_obj.id))
			gp_data = cr.dictfetchall()
			gp_obj=self.pool.get('kg.gate.pass')
			po_grn_obj=self.pool.get('kg.po.grn')
			po_grn_line_obj=self.pool.get('po.grn.line')
			gpl_obj = self.pool.get('kg.gate.pass.line')
			#so_order = grn_entry_obj.so_id
			line_ids = map(lambda x:x.id,grn_entry_obj.line_ids)
			po_grn_line_obj.unlink(cr,uid,line_ids)
			value1 = 0
			value2 = 0
			gp_list = []
			gpdate_list = []
			for item in gp_data:
				gp_id = item['gp_id']
				gp_record = gp_obj.browse(cr, uid, gp_id)
				gp_list.append(gp_record.name)
				date_order = gp_record.date
				date_order = datetime.strptime(date_order, '%Y-%m-%d')
				date_order = date_order.strftime('%d/%m/%Y')
				
				gpdate_list.append(date_order)
				gp_name = ",".join(gp_list)
				gp_date = ",".join(gpdate_list)
				self.write(cr,uid,ids[0],{
							'order_no':gp_name,
							'order_date':gp_date,
							'gp_name':gp_name,
							'gp_date':gp_date,
							})
				po_grn_id = grn_entry_obj.id
				order_lines=gp_record.gate_line
				for order_line in order_lines:
					if order_line.grn_pending_qty > 0:
						po_grn_line_obj.create(cr, uid, {
							'name': order_line.product_id.name or '/',
							'product_id': order_line.product_id.id,
							'brand_id':order_line.brand_id.id,
							'po_grn_qty': order_line.grn_pending_qty,
							'gp_qty':order_line.qty,
							'gp_pending_qty':order_line.grn_pending_qty,
							'uom_id': order_line.uom.id,
							'location_id': order_line.gate_id.partner_id.property_stock_supplier.id,
							'po_grn_id': po_grn_id,
							'state': 'confirmed',
							'gp_line_id': order_line.id,
							'price_unit': 0,
							'po_grn_date':grn_entry_obj.grn_date,
							'gp_flag':'True',
							'billing_type':'free',
							'ser_no':order_line.ser_no,
							'serial_no':order_line.serial_no.id,
							'order_no': order_line.gate_id.name,
							'order_date': order_line.gate_id.date,
						})
					else:
						print "NO Qty or Cancel"								

		return True
	
	# PO GRN Confirm #
		
	def po_grn_confirm(self, cr, uid, ids,context=None):
		back_list = []
		grn_entry = self.browse(cr, uid, ids[0])
		if grn_entry.line_ids:
			for i in grn_entry.line_ids:
				cr.execute(""" select pending_qty from purchase_order_line where order_id = %s """ %(i.po_id.id))
				data3 = cr.dictfetchall()
				if (data3[0]['pending_qty']) - (i.po_grn_qty) < i.rejected_items:
					raise osv.except_osv(
						_('Unable to confirm this GRN.'),
						_('Check the rejection quantity lesser than purchase order pending quantity.'))
		po_obj=self.pool.get('purchase.order')
		so_obj=self.pool.get('kg.service.order')
		exp_grn_qty = 0
		grn_date = grn_entry.grn_date
		today_date = today.strftime('%Y-%m-%d')
		back_list = []
		today_new = today.date()
		bk_date = date.today() - timedelta(days=3)
		back_date = bk_date.strftime('%Y-%m-%d')
		d1 = today_new
		d2 = bk_date
		delta = d1 - d2
		for i in range(delta.days + 1):
			bkk_date = d1 - timedelta(days=i)
			backk_date = bkk_date.strftime('%Y-%m-%d')
			back_list.append(backk_date)
		
		if grn_date > today_date:
			raise osv.except_osv(
					_('Warning'),
					_('GRN Date should be less than or equal to current date!'))
		grn_name = ''		
		if not grn_entry.name:
			grn_no = self.pool.get('ir.sequence').get(cr, uid, 'kg.po.grn') or ''
			grn_no_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.po.grn')])
			rec = self.pool.get('ir.sequence').browse(cr,uid,grn_no_id[0])
			cr.execute("""select generatesequenceno(%s,'%s','%s') """%(grn_no_id[0],rec.code,grn_entry.grn_date))
			grn_name = cr.fetchone();	
			self.write(cr,uid,ids,{'name':str(grn_name[0])})				
		if grn_entry.dc_date and grn_entry.dc_date > grn_entry.grn_date:
			raise osv.except_osv(_('DC Date Error!'),_('DC Date Should Be Less Than GRN Date.'))			
		if grn_entry.sup_invoice_date and grn_entry.sup_invoice_date > grn_entry.grn_date:
			raise osv.except_osv(_('Supplier Invoice Date Error!'),_('Supplier Invoice Date Should Be Less Than GRN Date.'))			
		if not grn_entry.line_ids:
			raise osv.except_osv(_('Item Line Empty!'),_('You cannot process GRN without Item Line.'))
		for line in grn_entry.line_ids:
			dt_time = a.strftime('%Y-%m-%d')		
			for exp in line.po_exp_id:
				if exp.exp_date:
					if exp.exp_date < dt_time:
						raise osv.except_osv(_('Warning!'), _('Expiery Date in Line items should not be in past date!!'))			
		for line in grn_entry.line_ids:
			if line.inward_type.id == False:
				raise osv.except_osv(_('Warning!'), _('Kindly Give Inward Type for %s !!' %(line.product_id.name)))
			if line.billing_type == 'cost':
				if grn_entry.grn_type == 'from_po':
					po_obj.write(cr,uid,line.po_line_id.order_id.id, {'grn_flag': True})
				if grn_entry.grn_type == 'from_so':
					so_obj.write(cr,uid,line.so_line_id.service_id.id, {'grn_flag': True})
			product_id = line.product_id.id
			product_rec = self.pool.get('product.product').browse(cr, uid, product_id)
			if product_rec.expiry == True:
				if not line.po_exp_id:
					raise osv.except_osv(_('Warning!'), _('You should specify expiry date and batch no for %s !!' %(line.product_id.name)))
			if line.po_exp_id:
				for exp_line in line.po_exp_id:
					if line.po_grn_date > exp_line.exp_date:
						raise osv.except_osv(
								_('Expiry Date Should Not Be Less Than Current Date!'),
								_('Change the product expity date to greater than current date for Product %s' %(line.product_id.name)))
				cr.execute(""" select sum(product_qty) from kg_po_exp_batch where po_grn_line_id = %s """ %(line.id))
				exp_data = cr.dictfetchone()
				exp_grn_qty = exp_data['sum']
				if exp_grn_qty > line.po_grn_qty:
					raise osv.except_osv(_('Please Check!'), _('Quantity specified in Batch Details should not exceed than GRN Quantity for %s!!'%(line.product_id.name)))
				if exp_grn_qty < line.po_grn_qty:
					raise osv.except_osv(_('Please Check!'), _('Quantity specified in Batch Details should not less than GRN Quantity for %s!!'%(line.product_id.name)))
			if line.po_grn_qty == 0:
					raise osv.except_osv(
					_('Item Qty can not Zero!'),
					_('You cannot process GRN with Item Line Qty Zero for Product %s.' %(line.product_id.name)))
			#Write a tax amount in line
			product_tax_amt = self._amount_line_tax(cr, uid, line, context=context)
			cr.execute("""update po_grn_line set product_tax_amt = %s where id = %s"""%(product_tax_amt,line.id))
		self.write(cr,uid,ids[0],{'state':'confirmed',
								  'confirm_flag':True,
								  'confirmed_by':uid,
								  'confirmed_date':today,
								   })
		return True
		
		# PO GRN APPROVE #
		
	def kg_po_grn_approve(self, cr, uid, ids,context=None):
		user_id = self.pool.get('res.users').browse(cr, uid, uid)
		grn_entry = self.browse(cr, uid, ids[0])
		gate_obj = self.pool.get('kg.gate.pass')
		gate_obj_line = self.pool.get('kg.gate.pass.line')
		cr.execute(""" select rejection_flag from po_grn_line where rejection_flag='t' and po_id=%s """ %(grn_entry.po_ids[0].id))
		rej_flag = cr.dictfetchone()
		if rej_flag:
			gate_idd = gate_obj.create(cr, uid, {'dep_id': 72,'partner_id': grn_entry.supplier_id.id,'mode': 'from_grn',	'out_type': 'rejection'})
			for i in grn_entry.line_ids:
				if i.rejection_flag == True:
					gate_obj_line.create(cr,uid,
						{
						'gate_id':gate_idd,
						'product_id':i['product_id'].id,
						'uom':i['uom_id'].id,
						'qty':i['rejected_items'],
						'grn_pending_qty':i['rejected_items'],
						'so_pending_qty':i['rejected_items'],
						'mode':'from_grn',
						})	
					cr.execute(""" select pending_qty from purchase_order_line where order_id = %s """ %(i.po_id.id))
					pend_qty = cr.dictfetchone()
					if pend_qty:
						updated_qty = pend_qty['pending_qty'] - i['rejected_items']
						cr.execute(""" update purchase_order_line set pending_qty = %s where order_id = %s """ %(updated_qty,i.po_id.id))
		val = 0
		gate_obj = self.pool.get('kg.gate.pass')
		if grn_entry.dc_date and grn_entry.dc_date > grn_entry.grn_date:
			raise osv.except_osv(_('DC Date Error!'),_('DC Date Should Be Less Than GRN Date.'))			
		if grn_entry.sup_invoice_date and grn_entry.sup_invoice_date > grn_entry.grn_date:
			raise osv.except_osv(_('Supplier Invoice Date Error!'),_('Supplier Invoice Date Should Be Less Than GRN Date.'))				
		if grn_entry.confirmed_by.id == uid:
			raise osv.except_osv(
					_('Warning'),
					_('Approve cannot be done by Confirmed user'))
		else:
			lot_obj = self.pool.get('stock.production.lot')
			stock_move_obj=self.pool.get('stock.move')
			dep_obj = self.pool.get('kg.depmaster')
			po_line_obj = self.pool.get('purchase.order.line')
			po_obj = self.pool.get('purchase.order')
			so_line_obj = self.pool.get('kg.service.order.line')
			so_obj = self.pool.get('kg.service.order')
			gp_line_obj = self.pool.get('kg.gate.pass.line')
			gp_obj = self.pool.get('kg.gate.pass')
			pi_obj = self.pool.get('kg.purchase.invoice')
			pi_po_grn_obj = self.pool.get('ch.invoice.line')
			po_order = grn_entry.po_id
			dep_id = user_id.dep_name.id
			dep_record = dep_obj.browse(cr,uid,dep_id)
			dest_location_id = dep_record.main_location.id 
			line_tot = 0			
			line_id_list = []
			if grn_entry.grn_dc == 'dc_invoice' and grn_entry.grn_type != 'from_gp':
				partner = self.pool.get('res.partner')
				supplier = partner.browse(cr, uid, grn_entry.supplier_id.id)
				tot_add = (supplier.street or '')+ ' ' + (supplier.street2 or '') + '\n'+(supplier.city.name or '')+ ',' +(supplier.state_id.name or '') + '-' +(supplier.zip or '') + '\nPh:' + (supplier.phone or '')+ '\n' +(supplier.mobile or '')
				if grn_entry.grn_type == 'from_po':
					grn_type = 'from_po'
				if grn_entry.grn_type == 'from_so':
					grn_type = 'from_so'
				grn_date = time.strftime('%Y-%m-%d')
				inv_sql = """select * from kg_purchase_invoice where to_char(invoice_date,'yyyy-mm-dd')="""+"""'"""+str(grn_date)+"""'""" + """and supplier_id="""+str(grn_entry.supplier_id.id)+""" and sup_invoice_no="""+"""'"""+str(grn_entry.sup_invoice_no)+"""'""" """  """
				cr.execute(inv_sql)
				inv_data = cr.dictfetchall()
				if inv_data:
					invdel_sql = """delete from kg_purchase_invoice where to_char(invoice_date,'yyyy-mm-dd')="""+"""'"""+str(grn_date)+"""'""" + """and supplier_id="""+str(grn_entry.supplier_id.id)+""" and sup_invoice_no="""+"""'"""+str(grn_entry.sup_invoice_no)+"""'""" """  """
					cr.execute(invdel_sql)	
				invoice_no = pi_obj.create(cr, uid, {
							'created_by': uid,
							'creation_date': today,
							'type':grn_type,
							'purpose': 'consu',
							'grn_type':'from_po_grn',
							'grn_no': grn_entry.name,
							'po_so_name': grn_entry.order_no,
							'po_so_date': grn_entry.order_date,
							'supplier_id':grn_entry.supplier_id.id,
							'sup_address': tot_add,
							'sup_invoice_date' : today,
							'entry_mode' : 'auto',
							'sup_invoice_no':grn_entry.sup_invoice_no,
							'sup_invoice_date':grn_entry.sup_invoice_date,
						})
				sql1 = """ insert into purchase_invoice_grn_ids(invoice_id,grn_id) values(%s,%s)"""%(invoice_no,grn_entry.id)
				cr.execute(sql1)
			for add in grn_entry.expense_line_id:
				val = val + add.expense_amt
			for line in grn_entry.line_ids:
				if line.price_unit > 0 :
					line.write({'billing_type':'cost'})
				line_id = line.id
				brand = []
				if line.brand_id:
					brand.append("brand_id = %s"%(line.brand_id.id))
				if brand:
					brand = 'and ('+' or '.join(brand)
					brand =  brand+')'
				else:
					brand = ''
				sql = """select * from stock_move where product_id="""+str(line.product_id.id)+""" and move_type='in' """+ brand +""" and po_grn_line_id="""+str(line.id)+"""  """
				cr.execute(sql)
				data = cr.dictfetchall()
				if data:
					del_sql = """delete from stock_move where product_id="""+str(line.product_id.id)+""" and move_type='in'  """+ brand +"""  and po_grn_line_id="""+str(line.id)+""" """
					cr.execute(del_sql)
				sql1 = """select * from stock_production_lot where lot_type='in' """+ brand +""" and product_id="""+str(line.product_id.id)+""" and grn_no='"""+str(line.po_grn_id.name)+"""' """
				cr.execute(sql1)
				data1 = cr.dictfetchall()
				if data1:
					del_sql1 = """delete from stock_production_lot where lot_type='in' """+ brand +""" and product_id="""+str(line.product_id.id)+""" and grn_no='"""+str(line.po_grn_id.name)+"""'"""
					cr.execute(del_sql1)
				if grn_entry.grn_type == 'from_po':
					if line.po_line_id.order_id:
						po_obj.write(cr,uid,line.po_line_id.order_id.id, {'grn_flag': False})
					if line.billing_type == 'cost':
						#code for tolarance
						if line.product_id.tolerance_applicable ==  True:
							tolarance = line.product_id.tolerance_plus
							cal_val = (line.po_qty*int(tolarance))/100
							tolarance_value  = line.po_pending_qty + cal_val
							if line.po_grn_qty < tolarance_value + 1:
								pass
							else:
								raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than PO Qty for %s !!' %(line.product_id.name)))
						else:
							if line.po_grn_qty > line.po_pending_qty:
								raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than PO Qty for %s !!' %(line.product_id.name)))
					if line.po_line_id.line_state == 'cancel':
						raise osv.except_osv(_('Warning!'), _('%s has been cancelled, kindly delete this product for proceed further!!' %(line.product_id.name)))					
					# This code is to update pending qty in Purchase Order #
					rec_qty = line.po_line_id.received_qty
					pending_qty = line.po_line_id.pending_qty
					if line.po_line_id:
						po_line_id = line.po_line_id
						grn_qty = line.po_grn_qty
						po_line_qty = line.po_qty
						po_line_pending_qty = pending_qty - grn_qty
						rec_qty += line.po_grn_qty
						po_line_obj.write(cr, uid, [line.po_line_id.id],
								{
								'pending_qty' : po_line_pending_qty,
								'received_qty' : rec_qty,
								})
				if grn_entry.grn_type == 'from_so':
					so_id = grn_entry.so_id.id
					so_obj.write(cr,uid,so_id, {'grn_flag':False})
					if line.so_line_id:
						so_obj.write(cr,uid,line.so_line_id.service_id.id, {'grn_flag': False})
					if line.billing_type == 'cost':
						#code for tolarance
						if line.product_id.tolerance_applicable ==  True:
							tolarance = line.product_id.tolerance_plus
							cal_val = (line.so_qty*int(tolarance))/100
							tolarance_value  = line.so_pending_qty + cal_val
							if line.po_grn_qty < tolarance_value + 1:
								pass
							else:
								raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than SO Qty for %s !!' %(line.product_id.name)))
						else:
							if line.po_grn_qty > line.so_pending_qty:
								raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than SO Qty for %s !!' %(line.product_id.name)))						
					# This code is to update pending qty in Service Order #
					rec_qty = line.so_line_id.received_qty
					pending_qty = line.so_line_id.pending_qty
					if line.so_line_id:
						so_line_id = line.so_line_id
						grn_qty = line.po_grn_qty
						so_line_qty = line.so_qty
						so_line_pending_qty = pending_qty - grn_qty
						rec_qty += line.po_grn_qty
						so_line_obj.write(cr, uid, [line.so_line_id.id],
								{
								'pending_qty' : so_line_pending_qty,
								'received_qty' : rec_qty,
								})
				if grn_entry.grn_type == 'from_gp' :
						#code for tolarance
					if line.product_id.tolerance_applicable ==  True:
						tolarance = line.product_id.tolerance_plus
						cal_val = (line.gp_qty*int(tolarance))/100
						tolarance_value  = line.gp_pending_qty + cal_val
						if line.po_grn_qty < tolarance_value + 1:
							pass
						else:
							raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than GP Qty for %s !!' %(line.product_id.name)))
					else:
						if line.po_grn_qty > line.gp_pending_qty and line.gp_flag == True:
							raise osv.except_osv(_('Warning!'), _('GRN Qty should not be greater than GP Qty for %s !!' %(line.product_id.name)))						
					# This code is to update pending qty in Gate Pass #
					if line.gp_line_id:
						pending_qty = line.gp_line_id.grn_pending_qty
						grn_qty = line.po_grn_qty
						gp_line_pending_qty = pending_qty - grn_qty
						if gp_line_pending_qty > 0:
							status = 'pending'
						else:
							status = 'done'
						gp_obj.write(cr, uid, [line.gp_line_id.gate_id.id],
								{
								'in_state' : status
								})
						gp_line_obj.write(cr, uid, [line.gp_line_id.id],
								{
								'grn_pending_qty' : gp_line_pending_qty,
								})
				# This code will create PO GRN to Stock Move
				# UOM Checking #
				if grn_entry.grn_type == 'from_po':
					if line.billing_type == 'cost':
						if line.uom_id.id != line.product_id.uom_id.id:
							product_uom = line.product_id.uom_id.id
							po_coeff = line.product_id.po_uom_coeff
							product_qty = line.po_grn_qty * po_coeff
							price_unit =  line.po_line_id.price_subtotal / product_qty
						elif line.uom_id.id == line.product_id.uom_id.id:
							product_uom = line.product_id.uom_id.id
							product_qty = line.po_grn_qty
							price_unit = line.po_line_id.price_subtotal / product_qty
					if line.billing_type == 'free':
						if line.uom_id.id != line.product_id.uom_id.id:
							product_uom = line.product_id.uom_id.id
							po_coeff = line.product_id.po_uom_coeff
							product_qty = line.po_grn_qty * po_coeff
							price_unit =  line.price_subtotal / product_qty
						elif line.uom_id.id == line.product_id.uom_id.id:
							product_uom = line.product_id.uom_id.id
							product_qty = line.po_grn_qty
							price_unit =  line.price_subtotal / product_qty
					stock_move_obj.create(cr,uid,
						{
						'po_grn_id':grn_entry.id,
						'po_grn_line_id':line.id,
						'purchase_line_id':line.po_line_id.id,
						'po_id':grn_entry.po_id.id,
						'product_id': line.product_id.id,
						'brand_id': line.brand_id.id,
						'name':line.product_id.name,
						'product_qty': product_qty,
						'po_to_stock_qty':product_qty,
						'stock_uom':product_uom,
						'product_uom': product_uom,
						'location_id': grn_entry.supplier_id.property_stock_supplier.id,
						'location_dest_id': dest_location_id,
						'move_type': 'in',
						'state': 'done',
						'price_unit': price_unit or 0.0,
						'price_tax': price_unit or 0.0,
						'origin':grn_entry.po_id.name,
						'stock_rate':price_unit or 0.0,
						'billing_type':line.billing_type
						})
					if  line.po_line_id.order_id:
						po_name = line.po_line_id.order_id.name
					else:
						po_name = ''	 
					if grn_entry.grn_dc == 'dc_invoice':	
						pi_po_grn_obj.create(cr,uid,
								{
								'po_grn_id':grn_entry.id,
								'po_grn_line_id':line.id,
								'purchase_line_id':line.po_line_id.id,
								'po_id':line.po_id.id,
								'product_id': line.product_id.id,
								'dc_no':grn_entry.dc_no,
								'po_so_no':po_name,
								'po_so_qty': line.po_qty,
								'tot_rec_qty':line.po_grn_qty,
								'uom_id':line.uom_id.id,
								'total_amt': line.po_grn_qty * line.price_unit,
								'price_unit': line.price_unit or 0.0,
								'discount': line.kg_discount,
								'kg_discount_per': line.kg_discount_per,
								'invoice_tax_ids': [(6, 0, [x.id for x in line.grn_tax_ids])],
								'net_amt': line.price_subtotal or 0.0,
								'invoice_header_id' :invoice_no
								})
					line.write({'state':'done'})
				if grn_entry.grn_type == 'from_so':
					if line.billing_type == 'cost':
						if line.uom_id.id != line.product_id.uom_id.id:
							product_uom = line.product_id.uom_id.id
							po_coeff = line.product_id.po_uom_coeff
							product_qty = line.po_grn_qty * po_coeff
							price_unit =  line.so_line_id.price_subtotal / product_qty
						elif line.uom_id.id == line.product_id.uom_id.id:
							product_uom = line.product_id.uom_id.id
							product_qty = line.po_grn_qty
							price_unit = line.so_line_id.price_subtotal / product_qty
					if line.billing_type == 'free':
						if line.uom_id.id != line.product_id.uom_id.id:
							product_uom = line.product_id.uom_id.id
							po_coeff = line.product_id.po_uom_coeff
							product_qty = line.po_grn_qty * po_coeff
							price_unit =  line.price_subtotal / product_qty
						elif line.uom_id.id == line.product_id.uom_id.id:
							product_uom = line.product_id.uom_id.id
							product_qty = line.po_grn_qty
							price_unit =  line.price_subtotal / product_qty
					if line.si_line_id and line.so_line_id.service_id.gp_id:		
						sql1 = """ update kg_gate_pass_line set grn_pending_qty=(grn_pending_qty - %s) where si_line_id = %s and gate_id = %s"""%(product_qty,
															line.si_line_id.id,line.so_line_id.service_id.gp_id.id)
						cr.execute(sql1)
					elif not line.si_line_id and line.so_line_id:
						sql1 = """ update kg_gate_pass_line set grn_pending_qty=(grn_pending_qty - %s) where product_id = %s and gate_id = %s"""%(product_qty,
															line.product_id.id,line.so_line_id.service_id.gp_id.id)
						cr.execute(sql1)	
					else:
						pass	
					stock_move_obj.create(cr,uid,
						{
						'po_grn_id':grn_entry.id,
						'po_grn_line_id':line.id,
						'so_line_id':line.so_line_id.id,
						'so_id':grn_entry.so_id.id,
						'product_id': line.product_id.id,
						'brand_id': line.brand_id.id,
						'name':line.product_id.name,
						'product_qty': product_qty,
						'po_to_stock_qty':product_qty,
						'stock_uom':product_uom,
						'product_uom': product_uom,
						'location_id': grn_entry.supplier_id.property_stock_supplier.id,
						'location_dest_id': dest_location_id,
						'move_type': 'in',
						'state': 'done',
						'price_unit': price_unit or 0.0,
						'price_tax': price_unit or 0.0,
						'origin':grn_entry.so_id.name,
						'stock_rate':price_unit or 0.0,
						})
					if grn_entry.grn_dc == 'dc_invoice': 
						
						if line.so_line_id:
							sso_id = line.so_line_id.service_id.id
							sso_name = line.so_line_id.service_id.name
						else:
							sso_id = False
							sso_name = ''
						
						pi_po_grn_obj.create(cr,uid,
								{
								'po_grn_id':grn_entry.id,
								'po_grn_line_id':line.id,
								'so_line_id':line.so_line_id.id,
								'so_id':sso_id,
								'product_id': line.product_id.id,
								'dc_no':grn_entry.dc_no,
								'po_so_no':sso_name,
								'po_so_qty': line.so_qty,
								'tot_rec_qty':line.po_grn_qty,
								'uom_id':line.uom_id.id,
								'total_amt': line.po_grn_qty * line.price_unit,
								'price_unit': line.price_unit or 0.0,
								'discount': line.kg_discount,
								'kg_discount_per': line.kg_discount_per,
								'invoice_tax_ids': [(6, 0, [x.id for x in line.grn_tax_ids])],
								'net_amt': line.price_subtotal or 0.0,
								'invoice_header_id' :invoice_no
								})
					line.write({'state':'done'})
				if grn_entry.grn_type == 'from_gp':
					if line.billing_type == 'free':
						if line.uom_id.id != line.product_id.uom_id.id:
							product_uom = line.product_id.uom_id.id
							po_coeff = line.product_id.po_uom_coeff
							product_qty = line.po_grn_qty * po_coeff
							price_unit =  line.price_subtotal / product_qty
						elif line.uom_id.id == line.product_id.uom_id.id:
							product_uom = line.product_id.uom_id.id
							product_qty = line.po_grn_qty
							price_unit =  line.price_subtotal / product_qty
					if line.gp_line_id:
						pass_id = line.gp_line_id.gate_id.id
						pass_line_id = line.gp_line_id.id
						pass_name = line.gp_line_id.gate_id.name
					else:
						pass_id = False
						pass_line_id = False
						pass_name = ''
					stock_move_obj.create(cr,uid,
						{
						'po_grn_id':grn_entry.id,
						'po_grn_line_id':line.id,
						'gp_line_id':pass_line_id,
						'gp_id':pass_id,
						'product_id': line.product_id.id,
						'brand_id': line.brand_id.id,
						'name':line.product_id.name,
						'product_qty': line.po_grn_qty,
						'po_to_stock_qty':line.po_grn_qty,
						'stock_uom':line.product_id.uom_id.id,
						'product_uom': line.product_id.uom_id.id,
						'location_id': grn_entry.supplier_id.property_stock_supplier.id,
						'location_dest_id': dest_location_id,
						'move_type': 'in',
						'state': 'done',
						'price_unit': (line.price_subtotal / line.po_grn_qty) or 0.0,
						'price_unit': (line.price_subtotal / line.po_grn_qty) or 0.0,
						'origin':pass_name,
						'stock_rate':(line.price_subtotal / line.po_grn_qty) or 0.0,
						})
					line.write({'state':'done'})
				# This code will create Production lot
				# UOM Checking #
				if grn_entry.grn_type == 'from_po':
					if line.po_exp_id:
						for exp in line.po_exp_id:
							if line.billing_type == 'cost':
								if line.uom_id.id != line.product_id.uom_id.id:
									product_uom = line.product_id.uom_id.id
									po_coeff = line.product_id.po_uom_coeff
									product_qty = exp.product_qty * po_coeff
									price_unit =  line.price_unit
								elif line.uom_id.id == line.product_id.uom_id.id:
									product_uom = line.product_id.uom_id.id
									product_qty = exp.product_qty
									price_unit = line.price_unit
							if line.billing_type == 'free':
								if line.uom_id.id != line.product_id.uom_id.id:
									product_uom = line.product_id.uom_id.id
									po_coeff = line.product_id.po_uom_coeff
									product_qty = exp.product_qty * po_coeff
									price_unit =  line.price_unit
								elif line.uom_id.id == line.product_id.uom_id.id:
									product_uom = line.product_id.uom_id.id
									product_qty = exp.product_qty
									price_unit =  line.price_unit
							lot_obj.create(cr,uid,
								{
								'po_grn_id':grn_entry.id,
								'po_grn_line_id':line.id,
								'grn_no':line.po_grn_id.name,
								'product_id':line.product_id.id,
								'brand_id':line.brand_id.id,
								'product_uom':product_uom,
								'product_qty':product_qty,
								'pending_qty':product_qty,
								'issue_qty':product_qty,
								'batch_no':exp.batch_no,
								'expiry_date':exp.exp_date,
								'price_unit':price_unit or 0.0,
								'price_tax':(line.price_subtotal / line.po_grn_qty) or 0.0,
								'po_uom':line.uom_id.id,
								'grn_type':'material'
							})
					else:
						if line.billing_type == 'cost':
							if line.uom_id.id != line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								po_coeff = line.product_id.po_uom_coeff
								product_qty = line.po_grn_qty * po_coeff
								price_unit =  line.po_line_id.price_subtotal / product_qty
							elif line.uom_id.id == line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								product_qty = line.po_grn_qty
								price_unit = line.po_line_id.price_subtotal / product_qty
						if line.billing_type == 'free':
							if line.uom_id.id != line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								po_coeff = line.product_id.po_uom_coeff
								product_qty = line.po_grn_qty * po_coeff
								price_unit =  line.price_subtotal / product_qty
							elif line.uom_id.id == line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								product_qty = line.po_grn_qty
								price_unit =  line.price_subtotal / product_qty
						lot_obj.create(cr,uid,
							{
							'po_grn_id':grn_entry.id,
							'po_grn_line_id':line.id,
							'grn_no':line.po_grn_id.name,
							'product_id':line.product_id.id,
							'brand_id':line.brand_id.id,
							'product_uom':product_uom,
							'product_qty':product_qty,
							'pending_qty':product_qty,
							'issue_qty':product_qty,
							'price_unit':price_unit or 0.0,
							'po_uom':product_uom,
							'batch_no':line.po_grn_id.name,
							'grn_type':'material',
							'price_tax':(line.price_subtotal / line.po_grn_qty) or 0.0,
						})
				if grn_entry.grn_type == 'from_so':
					if line.po_exp_id:
						for exp in line.po_exp_id:
							if line.billing_type == 'cost':
								if line.uom_id.id != line.product_id.uom_id.id:
									product_uom = line.product_id.uom_id.id
									po_coeff = line.product_id.po_uom_coeff
									product_qty = exp.product_qty * po_coeff
									price_unit = line.price_unit
								elif line.uom_id.id == line.product_id.uom_id.id:
									product_uom = line.product_id.uom_id.id
									product_qty = exp.product_qty
									price_unit = line.price_unit
							if line.billing_type == 'free':
								if line.uom_id.id != line.product_id.uom_id.id:
									product_uom = line.product_id.uom_id.id
									po_coeff = line.product_id.po_uom_coeff
									product_qty = exp.product_qty * po_coeff
									price_unit =  line.price_unit
								elif line.uom_id.id == line.product_id.uom_id.id:
									product_uom = line.product_id.uom_id.id
									product_qty = exp.product_qty
									price_unit =  line.price_unit
							lot_obj.create(cr,uid,
								{
								'po_grn_id':grn_entry.id,
								'po_grn_line_id':line.id,
								'grn_no':line.po_grn_id.name,
								'product_id':line.product_id.id,
								'brand_id':line.brand_id.id,
								'product_uom':product_uom,
								'product_qty':product_qty,
								'pending_qty':product_qty,
								'issue_qty':product_qty,
								'batch_no':exp.batch_no,
								'expiry_date':exp.exp_date,
								'price_unit':price_unit or 0.0,
								'po_uom':line.uom_id.id,
								'grn_type':'service',
								'price_tax':(line.price_subtotal / line.po_grn_qty) or 0.0,
							})
					else:
						if line.billing_type == 'cost':
							if line.uom_id.id != line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								po_coeff = line.product_id.po_uom_coeff
								product_qty = line.po_grn_qty * po_coeff
								price_unit =  line.so_line_id.price_subtotal / product_qty
							elif line.uom_id.id == line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								product_qty = line.po_grn_qty
								price_unit = line.so_line_id.price_subtotal / product_qty
						if line.billing_type == 'free':
							if line.uom_id.id != line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								po_coeff = line.product_id.po_uom_coeff
								product_qty = line.po_grn_qty * po_coeff
								price_unit =  line.price_subtotal / product_qty
							elif line.uom_id.id == line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								product_qty = line.po_grn_qty
								price_unit =  line.price_subtotal / product_qty
						lot_obj.create(cr,uid,
							{
							'po_grn_id':grn_entry.id,
							'po_grn_line_id':line.id,
							'grn_no':line.po_grn_id.name,
							'product_id':line.product_id.id,
							'brand_id':line.brand_id.id,
							'product_uom':product_uom,
							'product_qty':product_qty,
							'pending_qty':product_qty,
							'issue_qty':product_qty,
							'price_unit':price_unit or 0.0,
							'price_tax':(line.price_subtotal / line.po_grn_qty) or 0.0,
							'po_uom':product_uom,
							'batch_no':line.po_grn_id.name,
							'grn_type':'service'  
						})
				if grn_entry.grn_type == 'from_gp':
					if line.po_exp_id:
						for exp in line.po_exp_id:
							if line.uom_id.id != line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								po_coeff = line.product_id.po_uom_coeff
								product_qty =  exp.product_qty * po_coeff
								price_unit =  line.price_unit
									
							elif line.uom_id.id == line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								product_qty =  exp.product_qty
								price_unit =  line.price_unit
							lot_obj.create(cr,uid,
								{
								'po_grn_id':grn_entry.id,
								'po_grn_line_id':line.id,
								'grn_no':line.po_grn_id.name,
								'product_id':line.product_id.id,
								'brand_id':line.brand_id.id,
								'product_uom':product_uom,
								'product_qty':product_qty,
								'pending_qty':product_qty,
								'issue_qty':product_qty,
								'batch_no':exp.batch_no,
								'expiry_date':exp.exp_date,
								'price_unit':price_unit or 0.0,
								'price_tax':(line.price_subtotal / line.po_grn_qty) or 0.0,
								'po_uom':line.uom_id.id,
								'grn_type':'service'
							})
					else:
						if line.billing_type == 'free':
							if line.uom_id.id != line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								po_coeff = line.product_id.po_uom_coeff
								product_qty = line.po_grn_qty * po_coeff
								price_unit =  line.price_subtotal / product_qty
							elif line.uom_id.id == line.product_id.uom_id.id:
								product_uom = line.product_id.uom_id.id
								product_qty = line.po_grn_qty
								price_unit =  line.price_subtotal / product_qty
						lot_obj.create(cr,uid,
							{
							'po_grn_id':grn_entry.id,
							'po_grn_line_id':line.id,
							'grn_no':line.po_grn_id.name,
							'product_id':line.product_id.id,
							'brand_id':line.brand_id.id,
							'product_uom':line.product_id.uom_id.id,
							'product_qty':line.po_grn_qty,
							'pending_qty':line.po_grn_qty,
							'issue_qty':line.po_grn_qty,
							'price_unit':(line.price_subtotal / line.po_grn_qty) or 0.0,
							'price_tax':(line.price_subtotal / line.po_grn_qty) or 0.0,
							'po_uom':line.product_id.uom_id.id,
							'batch_no':line.po_grn_id.name,
							'grn_type':'service'
						})
				#Write a tax amount in line
				product_tax_amt = self._amount_line_tax(cr, uid, line, context=context)
				cr.execute("""update po_grn_line set product_tax_amt = %s where id = %s"""%(product_tax_amt,line.id))
			self.write(cr,uid,ids[0],{'state':'done',
								  'approve_flag':True,
								  'confirm_flag':True,
								  'approved_by':uid,
								  'approved_date':today })
			if grn_entry.billing_status == 'applicable':
				self.write(cr,uid,ids[0],{'invoice_flag':'True'})
			if grn_entry.grn_type == 'from_so' and grn_entry.so_id.gp_id:
				sql = """ select * from kg_gate_pass_line where grn_pending_qty > 0 and gate_id = %s"""%(grn_entry.so_id.gp_id.id)
				cr.execute(sql)
				data = cr.dictfetchall()
				if data:
					gate_obj.write(cr,uid,grn_entry.so_id.gp_id.id,{'in_state':'pending'})
				else:
					gate_obj.write(cr,uid,grn_entry.so_id.gp_id.id,{'in_state':'done'})
			return True
		
	## GRN to PO Bill creation Part ##
	
	def _get_invoice_type(self, pick):
		move_obj = self.pool.get('stock.move')
		src_usage = dest_usage = None
		inv_type = None
		if pick.state == 'done':
			move_ids = pick.line_ids
			for move_id in move_ids:
				src_usage = move_id.location_id.usage
				dest_usage = move_id.location_dest_id.usage
			if pick.type == 'out' and dest_usage == 'supplier':
				inv_type = 'in_refund'
			elif pick.type == 'out' and dest_usage == 'customer':
				inv_type = 'out_invoice'
			elif pick.type == 'in' and src_usage == 'supplier':
				inv_type = 'in_invoice'
			elif pick.type == 'in' and src_usage == 'customer':
				inv_type = 'out_refund'
			else:
				inv_type = 'in_invoice'
		return inv_type
	
	def action_invoice_create(self, cr, uid, ids, journal_id=False,
			group=False, type='out_invoice', context=None):
		if context is None:
			context = {}
		invoice_obj = self.pool.get('account.invoice')
		invoice_line_obj = self.pool.get('account.invoice.line')
		partner_obj = self.pool.get('res.partner')
		po_obj = self.pool.get('purchase.order')
		pol_obj = self.pool.get('purchase.order.line')
		move_obj = self.pool.get('stock.move')
		picking_obj = self.pool.get('stock.picking')
		invoices_group = {}
		res = {}
		inv_type = type
		for picking in self.browse(cr, uid, ids, context=context):
			po_rec = picking.po_id
			po_obj.write(cr,uid,po_rec.id, {'bill_flag': True})	 
			partner = picking.supplier_id
			if isinstance(partner, int):
				partner = partner_obj.browse(cr, uid, [partner], context=context)[0]
			if not partner:
				raise osv.except_osv(_('Error, no partner!'),
					_('Please put a partner on the picking list if you want to generate invoice.'))
			if not inv_type:
				inv_type = self._get_invoice_type(picking)
			if group and partner.id in invoices_group:
				invoice_id = invoices_group[partner.id]
				invoice = invoice_obj.browse(cr, uid, invoice_id)
				invoice_vals_group = self._prepare_invoice_group(cr, uid, picking, partner, invoice, context=context)
				invoice_obj.write(cr, uid, [invoice_id], invoice_vals_group, context=context)
			else:
				invoice_vals = self._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
				invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
				invoices_group[partner.id] = invoice_id
			res[picking.id] = invoice_id
			move_ids = move_obj.search(cr, uid, [('po_grn_id','=',picking.id),('billing_type','=','cost')])
			for move_id in move_ids:
				move_line = move_obj.browse(cr, uid, move_id)
				if move_line.state == 'cancel':
					continue
				if move_line.scrapped:
					# do no invoice scrapped products
					continue
				vals = self._prepare_invoice_line(cr, uid, group, picking, move_line,
							invoice_id, invoice_vals, context=context)
				if vals:
					invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)
				if move_line.purchase_line_id:
					pl_id = move_line.purchase_line_id.id
					pol_obj.write(cr, uid, pl_id, {'line_bill': True})				

			invoice_obj.button_compute(cr, uid, [invoice_id], context=context,
					set_total=(inv_type in ('in_invoice', 'in_refund')))
			self.write(cr, uid, [picking.id], {
				'state': 'inv',
				}, context=context)
		self.write(cr, uid, res.keys(), {
			'state': 'inv',
			'invoice_flag': False
			}, context=context)
		return res
	
	def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
		po_rec = picking.po_id
		val1 = po_rec.value1 or 0.0
		val2 = po_rec.value2 or 0.0
		other_ch1 = po_rec.po_expenses_type1 or False
		other_ch2 = po_rec.po_expenses_type2 or False
		sub = po_rec.amount_untaxed
		dis = po_rec.discount
		tax = po_rec.amount_tax
		total = po_rec.amount_total
		other_charge = val1 + val2
		bill = po_rec.bill_type
		if isinstance(partner, int):
			partner = self.pool.get('res.partner').browse(cr, uid, partner, context=context)
		if inv_type in ('out_invoice', 'out_refund'):
			payment_term = partner.property_payment_term.id or False
		else:
			payment_term = partner.property_supplier_payment_term.id or False
		comment = 'Invoice'
		invoice_vals = {
			'name': self.pool.get('ir.sequence').get(cr, uid, 'account.invoice'),
			'origin': (picking.name or ''),
			'type': inv_type,
			#'account_id': account_id,
			'partner_id': partner.id,
			'comment': comment,
			'payment_term': payment_term,
			'fiscal_position': partner.property_account_position.id,
			'date_invoice': context.get('date_inv', False),
			'company_id': picking.company_id.id,
			'user_id': uid,
			'po_id':picking.po_id.id,
			'grn_id':picking.id,
			'po_expenses_type1':other_ch1,
			'po_expenses_type2':other_ch2,
			'value1':val1,
			'value2':val2,
			'state':'proforma',
			'supplier_invoice_number': context.get('sup_inv_no', False),
			'sup_inv_date': context.get('sup_inv_date', False),
			'bill_type':'credit',
			'po_date':po_rec.date_order,
			'grn_date':picking.grn_date,
			'amount_untaxed':po_rec.amount_untaxed,
			'amount_tax':po_rec.amount_tax,
			'tot_discount':po_rec.discount,
			'other_charge':other_charge
		}
		if journal_id:
			invoice_vals['journal_id'] = journal_id
		return invoice_vals

	def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id,
		invoice_vals, context=None):
		pol_rec = move_line.purchase_line_id
		if group:
			name = (picking.name or '') + '-' + move_line.name
		else:
			name = move_line.name
		origin = move_line.po_grn_id.name or ''
		if move_line.po_grn_id.name:
			origin += ':' + move_line.po_grn_id.name
		if invoice_vals['type'] in ('out_invoice', 'out_refund'):
			account_id = move_line.product_id.property_account_income.id
			if not account_id:
				account_id = move_line.product_id.categ_id.\
						property_account_income_categ.id
		else:
			account_id = move_line.product_id.property_account_expense.id
			if not account_id:
				account_id = move_line.product_id.categ_id.\
						property_account_expense_categ.id
		if invoice_vals['fiscal_position']:
			fp_obj = self.pool.get('account.fiscal.position')
			fiscal_position = fp_obj.browse(cr, uid, invoice_vals['fiscal_position'], context=context)
			account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)
		# set UoS if it's a sale and the picking doesn't have one
		uos_id = move_line.product_uom.id
		return {
			'name': name,
			'origin': origin,
			'invoice_id': invoice_id,
			'uos_id': uos_id,
			'poline_id':move_line.purchase_line_id,
			'product_id': move_line.product_id.id,
			'brand_id': move_line.brand_id.id,
			'price_unit': pol_rec.price_unit,
			'quantity': move_line.product_qty or 0.00,
			'invoice_line_tax_id': [(6, 0, [x.id for x in move_line.po_grn_line_id.grn_tax_ids])],
			'discount':pol_rec.kg_discount_per,
			'kg_disc_amt':pol_rec.kg_discount,
		}		
		
	def print_grn(self, cr, uid, ids, context=None):		
		assert len(ids) == 1, 'This option should only be used for a single id at a time'
		wf_service = netsvc.LocalService("workflow")
		wf_service.trg_validate(uid, 'kg.po.grn', ids[0], 'send_rfq', cr)
		datas = {
				 'model': 'kg.po.grn',
				 'ids': ids,
				 'form': self.read(cr, uid, ids[0], context=context),
		}
		return {'type': 'ir.actions.report.xml', 'report_name': 'grn.print', 'datas': datas, 'nodestroy': True,'name': 'GRN'}	  
	
	def grn_register_scheduler_mail(self,cr,uid,ids,context=None):
		return True

kg_po_grn()

class po_grn_line(osv.osv):

	_name = "po.grn.line"
	_description = "PO GRN Line"


	def _amount_line(self, cr, uid, ids, prop, arg, context=None):
		cur_obj=self.pool.get('res.currency')
		tax_obj = self.pool.get('account.tax')
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			amt_to_per = (line.kg_discount / (line.po_grn_qty * line.price_unit or 1.0 )) * 100
			kg_discount_per = line.kg_discount_per
			tot_discount_per = amt_to_per + kg_discount_per
			price = line.price_unit * (1 - (tot_discount_per or 0.0) / 100.0)
			taxes = tax_obj.compute_all(cr, uid, line.grn_tax_ids, price, line.po_grn_qty, line.product_id, line.po_grn_id.supplier_id)
			cur = line.po_grn_id.supplier_id.property_product_pricelist_purchase.currency_id
			res[line.id] = cur_obj.round(cr, uid, cur, taxes['total_included'])
		return res  
		
	_columns = {
		
		'po_grn_date':fields.date('PO GRN Date'),
		'po_grn_id':fields.many2one('kg.po.grn','PO GRN Entry'),
		'name':fields.char('Product'),
		'product_id':fields.many2one('product.product','Product Name',required=True, domain=[('state','=','approved')]),
		'uom_id':fields.many2one('product.uom','UOM',required=True),
		'po_grn_qty':fields.float('Quantity',required=True),
		'po_qty':fields.float('PO Qty'),
		'so_qty':fields.float('SO Qty'),
		'gp_qty':fields.float('GP Qty'),
		'po_pending_qty':fields.float('PO Pending Qty'),
		'so_pending_qty':fields.float('SO Pending Qty'),
		'gp_pending_qty':fields.float('GP Pending Qty'),
		'price_unit':fields.float('Unit Price',required=True),
		'kg_discount_per': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount')),
		'kg_discount': fields.float('Discount Amount'),
		'grn_tax_ids': fields.many2many('account.tax', 'po_grn_tax', 'order_id', 'taxes_id', 'Taxes',domain=[('state','=','approved')]),
		'location_id': fields.many2one('stock.location', 'Source Location'),
		'location_dest_id': fields.many2one('stock.location', 'Destination Location'),
		'po_line_id':fields.many2one('purchase.order.line','PO Line'),
		'po_id':fields.many2one('purchase.order','PO NO'),
		'so_line_id':fields.many2one('kg.service.order.line','SO Line'),
		'so_id':fields.many2one('kg.service.order','SO NO'),
		'gp_line_id':fields.many2one('kg.gate.pass.line','GP Line'),
		'gp_id':fields.many2one('kg.gate.pass','GP NO'),
		'pi_line_id':fields.many2one('purchase.requisition.line','PI Line'),
		'si_line_id':fields.many2one('kg.service.indent.line','SI Line'),
		'po_exp_id':fields.one2many('kg.po.exp.batch','po_grn_line_id','Expiry Line'),
		'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'),('done', 'Done'), ('cancel', 'Cancelled')], 'Status',readonly=True),
		'remark':fields.text('Remarks'),
		'price_subtotal': fields.function(_amount_line,string='Line Total', digits_compute= dp.get_precision('Account')),
		'brand_id':fields.many2one('kg.brand.master','Brand',domain=[('state','=','approved')]),
		'so_flag':fields.boolean('SO Flag'),
		'po_flag':fields.boolean('PO Flag'),
		'gp_flag':fields.boolean('PO Flag'),
		'billing_type': fields.selection([('free', 'Free'), ('cost', 'Cost')], 'Billing Type'),
		'inward_type': fields.many2one('kg.inwardmaster', 'Inward Type',domain=[('state','=','approved')]),
		'ser_no':fields.char('Ser No', size=128, readonly=True),
		'serial_no':fields.many2one('stock.production.lot','Serial No',domain="[('product_id','=',product_id)]", readonly=True),  
		'order_no': fields.char('Order NO',readonly=True),
		'order_date': fields.char('Order Date',readonly=True),
		'product_tax_amt':fields.float('Tax Amount'),  
		'price_type': fields.selection([('po_uom','PO UOM'),('per_kg','Per KG')],'Price Type'),
		'length': fields.float('Length'),
		'breadth': fields.float('Breadth'),
		'tot_price': fields.float('Total Amount',readonly=True),
		'rejected_items': fields.float('Rejected Item'),
		'rej_remark': fields.text('Rejection remarks'),
		'rejection_flag': fields.boolean('Rejection Flag'),
	}
	
	
	
	def onchange_qty(self,cr,uid,ids,po_grn_qty,price_unit,tot_price,kg_discount_per,context=None):
		discount_value_price = 0.00
		if price_unit >0.00 and po_grn_qty > 0.00:
			tot_price = (price_unit * po_grn_qty)						
			if kg_discount_per:
				discount_value_price = (tot_price/100.00)*kg_discount_per	
		if price_unit >0.00 and po_grn_qty > 0.00:
			tot_price = (price_unit * po_grn_qty)				
		return {'value' : {'tot_price':(round(tot_price,2)),'kg_discount': discount_value_price}}
		
	
	def onchange_product_id(self, cr, uid, ids, product_id, uom_id,context=None):
			
		value = {'uom_id': ''}
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			value = {'uom_id': prod.uom_id.id}
		return {'value': value}
	
	def onchange_po_grn_qty(self,cr,uid, ids, po_grn_qty ):
		rec = self.browse(cr,uid,ids[0])
		if rec.po_grn_id.so_id.id:
			service_id = self.pool.get('kg.service.order.line').search(cr,uid,[('service_id','=',rec.po_grn_id.so_id.id)])
			service_rec = self.pool.get('kg.service.order.line').browse(cr,uid,service_id[0])
			pending_qty = service_rec.pending_qty
		else:
			purchase_id = self.pool.get('kg.purchase.order.line').search(cr,uid,[('order_id','=',rec.po_grn_id.po_id.id)])
			purchase_rec = self.pool.get('kg.purchase.order.line').browse(cr,uid,purchase_id[0])
			pending_qty = purchase_rec.pending_qty
		if po_grn_qty > pending_qty:
			raise osv.except_osv(
						_('Please check the Quantity amount'),
						_('Quantity Should not be greater than PO Quantity!'))
		return True
	
	_defaults = {
	
		'state':'draft',
		'billing_type':'free',
		'price_type':'po_uom'
		
		
	}   

po_grn_line()

class kg_po_exp_batch(osv.osv):

	_name = "kg.po.exp.batch"
	_description = "Expiry Date and Batch NO"

	
	_columns = {
		
		'po_grn_line_id':fields.many2one('po.grn.line','PO GRN Entry Line'),
		'exp_date':fields.date('Expiry Date'),
		'batch_no':fields.char('Batch No'),
		'product_qty':fields.float('Product Qty'),
		
		
	}
	def _check_values(self, cr, uid, ids, context=None):
		entry = self.browse(cr,uid,ids[0])
		
		cr.execute(""" select batch_no from kg_po_exp_batch where batch_no  = '%s' """ %(entry.batch_no))
		data = cr.dictfetchall() 
		if len(data) > 1:
			raise osv.except_osv(_('Warning!'), _('%s Serial NO %s is getting duplicated') % (entry.po_grn_line_id.product_id.name_template,entry.batch_no)) 
			return False
		return True

	
	
	
kg_po_exp_batch()


class kg_po_stock_move(osv.osv):

	_name = "stock.move"
	_inherit = "stock.move"

	
	_columns = {
		
		'po_grn_line_id':fields.many2one('po.grn.line','PO GRN Entry Line'),
		'po_grn_id':fields.many2one('kg.po.grn','PO GRN Entry'),
		'po_id':fields.many2one('purchase.order','Purchase Order'),
		'so_id':fields.many2one('kg.service.order','Service Order'),
		'so_line_id':fields.many2one('kg.service.order.line','Service Order Line'),
		'billing_type': fields.selection([('free', 'Free'), ('cost', 'Cost')], 'Billing Type'),
		'brand_id':fields.many2one('kg.brand.master','Brand Name'),
		
		
		
	}	  
	
kg_po_stock_move()

class kg_po_grn_expense_track(osv.osv):

	_name = "kg.po.grn.expense.track"
	_description = "kg expense track"
	
	_columns = {
		
		'expense_id': fields.many2one('kg.po.grn', 'Expense Track'),
		'name': fields.char('Number', size=128, select=True,readonly=False),
		'date': fields.date('Creation Date'),
		'company_id': fields.many2one('res.company', 'Company Name'),
		'description': fields.selection([('transport','Transport'),('packing','Packing'),('others','Others')],'Description'),
		'expense_amt': fields.float('Amount'),
		'tax': fields.many2one('account.tax','Tax',domain="[('state','=','approved')]"),
		
	}
	
	_defaults = {
		
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.po.grn.expense.track', context=c),
		'date' : fields.date.context_today,
	
		}
		
kg_po_grn_expense_track()		
