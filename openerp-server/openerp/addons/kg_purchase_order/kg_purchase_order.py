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
import logging
from openerp import netsvc
from tools import number_to_text_convert_india
logger = logging.getLogger('server')
today = datetime.now()
import urllib
import urllib2
import logging
import base64

UOM_CONVERSATION = [
    ('one_dimension','One Dimension'),('two_dimension','Two Dimension')
]

class kg_purchase_order(osv.osv):
	
	def _amount_line_tax(self, cr, uid, line, context=None):
		logger.info('[KG OpenERP] Class: kg_purchase_order, Method: _amount_line_tax called...')
		val = 0.0
		new_amt_to_per = line.kg_discount / line.product_qty
		amt_to_per = (line.kg_discount / (line.product_qty * line.price_unit or 1.0 )) * 100
		kg_discount_per = line.kg_discount_per
		tot_discount_per = amt_to_per + kg_discount_per
		qty = 0
		if line.price_type == 'per_kg':
			if line.product_id.uom_conversation_factor == 'two_dimension':
				if line.product_id.po_uom_in_kgs > 0:
					qty = line.product_qty * line.product_id.po_uom_in_kgs * line.length * line.breadth
			elif line.product_id.uom_conversation_factor == 'one_dimension':
				if line.product_id.po_uom_in_kgs > 0:
					qty = line.product_qty * line.product_id.po_uom_in_kgs
				else:
					qty = line.product_qty
			else:
				qty = line.product_qty
		else:
			qty = line.product_qty
		for c in self.pool.get('account.tax').compute_all(cr, uid, line.taxes_id,
			line.price_unit * (1-(tot_discount_per or 0.0)/100.0), qty, line.product_id,
				line.order_id.partner_id)['taxes']:
			val += c.get('amount', 0.0)
		return val	
	
	def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
		logger.info('[KG OpenERP] Class: kg_purchase_order, Method: _amount_all called...')
		res = {}
		cur_obj=self.pool.get('res.currency')
		other_charges_amt = 0
		for order in self.browse(cr, uid, ids, context=context):
			res[order.id] = {
				'amount_untaxed': 0.0,
				'amount_tax': 0.0,
				'amount_total': 0.0,
				'discount' : 0.0,
				'other_charge': 0.0,
			}
			val = val1 = val3 = val4 = val5 = 0.0
			cur = order.pricelist_id.currency_id
			po_charges=order.value1 + order.value2
			if order.expense_line_id:
				for item in order.expense_line_id:
					other_charges_amt += item.expense_amt
			else:
				other_charges_amt = 0
			pol = self.pool.get('purchase.order.line')
			for line in order.order_line:
				tot_discount = line.kg_discount
				val1 += line.price_subtotal
				val += self._amount_line_tax(cr, uid, line, context=context)
				val3 += tot_discount
				val4 += line.tot_price
				val5 += line.price_subtotal
			res[order.id]['line_amount_total']= (round(val4,0))
			res[order.id]['other_charge']= other_charges_amt or 0
			res[order.id]['amount_tax']=(round(val,0))
			res[order.id]['amount_untaxed']=(round(val5,0))
			res[order.id]['discount']=(round(val3,0))
			res[order.id]['amount_total']=res[order.id]['amount_untaxed'] + res[order.id]['amount_tax'] + res[order.id]['other_charge']
		return res
		
	def _get_order(self, cr, uid, ids, context=None):
		logger.info('[KG OpenERP] Class: kg_purchase_order, Method: _get_order called...')
		result = {}
		for line in self.pool.get('purchase.order.line').browse(cr, uid, ids, context=context):
			result[line.order_id.id] = True
		return result.keys()

	_name = "purchase.order"
	_inherit = "purchase.order"
	_order = "creation_date desc"

	_columns = {
		
		'po_type': fields.selection([('direct', 'Direct'),('frompi', 'From PI'),('fromquote', 'From Quote')], 'PO Mode',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}),
		'bill_type': fields.selection([('cash','CASH BILL'),('credit','CREDIT BILL')], 'Bill Type',states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}),
		'po_expenses_type1': fields.selection([('freight','Freight Charges'),('others','Others')], 'Expenses Type1', readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'po_expenses_type2': fields.selection([('freight','Freight Charges'),('others','Others')], 'Expenses Type2', readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'value1':fields.float('Value1',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'value2':fields.float('Value2',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'note': fields.text('Remarks'),
		'vendor_bill_no': fields.float('Vendor.Bill.No',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'vendor_bill_date': fields.date('Vendor.Bill.Date',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'location_id': fields.many2one('stock.location', 'Destination', required=True, domain=[('usage','=','internal')], states={'approved':[('readonly',True)],'done':[('readonly',True)]} ),		
		'payment_term_id': fields.many2one('account.payment.term', 'Payment Term', readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'pricelist_id':fields.many2one('product.pricelist', 'Pricelist', states={'approved':[('readonly',True)],'done':[('readonly',True)]}, help="The pricelist sets the currency used for this purchase order. It also computes the supplier price for the selected products/quantities."),	
		'date_order': fields.date('PO Date',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}),
		'payment_mode': fields.many2one('kg.payment.master', 'Payment Term', readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]},domain=[('state','=','approved')]),
		'delivery_mode': fields.many2one('kg.delivery.master','Delivery Term', required=False,readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]},domain=[('state','=','approved')]),
		'partner_address':fields.char('Supplier Address', size=128,readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'email':fields.char('Contact Email', size=128,readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'contact_person':fields.char('Contact Person', size=128),
		'other_charge': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Other Charges(+)',
			 multi="sums", help="The amount without tax", track_visibility='always',store=True),		
		'confirm_flag':fields.boolean('Confirm Flag'),
		'discount': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total Discount(-)',
			store={
				'purchase.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
				'purchase.order.line': (_get_order, ['price_unit', 'tax_id', 'kg_discount', 'product_qty'], 10),
			}, multi="sums", help="The amount without tax", track_visibility='always'),
		'amount_untaxed': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Untaxed Amount',
			store={
				'purchase.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
				'purchase.order.line': (_get_order, ['price_unit', 'tax_id', 'kg_discount', 'product_qty'], 10),
			}, multi="sums", help="The amount without tax", track_visibility='always'),
		'amount_tax': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Taxes',
			store=True, multi="sums", help="The tax amount"),
		'amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total Amount',
			 multi="sums", store=True, help="The amount without tax", track_visibility='always'),		
		'po_flag': fields.boolean('PO Flag'),
		'grn_flag': fields.boolean('GRN'),
		'kg_seq_id':fields.many2one('ir.sequence','Document Type',domain=[('code','=','purchase.order')],
			readonly=True, states={'draft': [('readonly', False)]}),
		'name': fields.char('PO NO', size=64, select=True,readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'amend_flag': fields.boolean('Amendment', select=True),
		'add_text': fields.text('Address',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}),
		'type_flag':fields.boolean('Type Flag'),
		'pi_flag':fields.boolean('Type Flag'),
		'delivery_address':fields.text('Delivery Address',store=True,readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}),
		'term_price':fields.selection([('inclusive','Inclusive of all Taxes and Duties'),('exclusive', 'Exclusive')], 'Price',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}), 
		'term_warranty':fields.char('Warranty',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}),
		'term_freight':fields.selection([('Inclusive','Inclusive'),('Extra','Extra'),('To Pay','To Pay'),('Paid','Paid'),
						  ('Extra at our Cost','Extra at our Cost')], 'Freight',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}), 
		'quot_ref_no':fields.char('Quot. Ref.',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}),
		'dep_project_name':fields.char('Dept/Project Name',readonly=False),
		'text_amt':fields.char('Amount in Words'),
		'approve_flag':fields.boolean('Expiry Flag'),
		'frieght_flag':fields.boolean('Expiry Flag'),
		'version':fields.char('Version'),
		'purpose':fields.selection([('for_sale','For Production'),('own_use','Own use')], 'Purpose',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}), 
		'expense_line_id': fields.one2many('kg.purchase.order.expense.track','expense_id','Expense Track',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
		'quotation_date': fields.date('Quotation Date',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}),
		'entry_mode': fields.selection([('manual','Manual'),('auto','Auto')],'Entry Mode'),
		'insurance': fields.selection([('sam','By Our Self'),('supplier','By Supplier'),('na','N/A')],'Insurance',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}),
		'excise_duty': fields.selection([('inclusive','Inclusive'),('extra','Extra'),('nil','Nil')],'Excise Duty',readonly=False, states={'approved':[('readonly',True)],'done':[('readonly',True)],'cancel':[('readonly',True)]}),
		'division': fields.selection([('foundry','Foundry')],'Division',readonly=True),
		'revision': fields.integer('Revision',readonly=True),
		
		
		# Entry Info
		
		'creation_date':fields.datetime('Created Date',readonly=True),
		'user_id': fields.many2one('res.users', 'Created by',readonly=True),
		'confirmed_by':fields.many2one('res.users','Confirmed By',readonly=True),
		'confirmed_date':fields.datetime('Confirmed Date',readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'approved_by':fields.many2one('res.users','Approved By',readonly=True),
		'approved_date':fields.datetime('Approved Date',readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'update_date' : fields.datetime('Last Updated Date',readonly=True),
		'update_user_id' : fields.many2one('res.users','Last Updated By',readonly=True),
		'active': fields.boolean('Active'),
		'closing_flag': fields.boolean('Manual Closing'),
		'line_amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Net Amount',
			 multi="sums", store=True, help="The amount without tax", track_visibility='always'),		
		
	}
	
	_defaults = {
	
		'bill_type' :'credit',
		'date_order': lambda * a: time.strftime('%Y-%m-%d'),
		'po_type': 'frompi',
		'name': lambda self, cr, uid, c: self.pool.get('purchase.order').browse(cr, uid, id, c).id,
		'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id,
		'creation_date':lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'confirm_flag':False,
		'approve_flag':False,
		'frieght_flag':False,
		'version':'00',
		'pricelist_id': 2,
		'type_flag': False,
		'insurance': 'na',
		'division': 'foundry',
		'active': True,
		'closing_flag': False,
		'delivery_address': lambda self, cr, uid, c: self.pool.get('res.company').browse(cr,uid,1).street,
	
	}
	
	
	def create(self, cr, uid, vals,context=None):
		"""inv_seq = vals['kg_seq_id']
		next_seq_num = self.pool.get('ir.sequence').kg_get_id(cr, uid, inv_seq,'id',{'noupdate':False})
		vals.update({
						'name':next_seq_num,
						
						})"""
		order =  super(kg_purchase_order, self).create(cr, uid, vals, context=context)
		return order
	
	def onchange_seq_id(self, cr, uid, ids, kg_seq_id,name):
		"""value = {'name':''}
		if kg_seq_id:
			next_seq_num = self.pool.get('ir.sequence').kg_get_id(cr, uid, kg_seq_id,'id',{'noupdate':False})
			value = {'name': next_seq_num}"""
		return True
		
	def onchange_type_flag(self, cr, uid, ids, po_type):
		value = {'type_flag':False}
		if po_type == 'direct':
			value = {'type_flag': True}
		else:
			value = {'pi_flag': True}
		return {'value': value}
	

		
	### Back Entry Date #####	
		
	def onchange_date_order(self, cr, uid, ids, date_order):
		today_date = today.strftime('%Y-%m-%d')
		back_list = []
		today_new = today.date()
		bk_date = date.today() - timedelta(days=2)
		back_date = bk_date.strftime('%Y-%m-%d')
		d1 = today_new
		d2 = bk_date
		delta = d1 - d2
		for i in range(delta.days + 1):
			bkk_date = d1 - timedelta(days=i)
			backk_date = bkk_date.strftime('%Y-%m-%d')
			back_list.append(backk_date)
		if date_order <= back_date:
			raise osv.except_osv(
				_('Warning'),
				_('PO Entry is not allowed!'))
		return True
		
	def onchange_frieght_flag(self, cr, uid, ids, term_freight):
		value = {'frieght_flag':False}
		if term_freight == 'Extra':
			value = {'frieght_flag': True}
		return {'value': value}
	
	def onchange_partner_id(self, cr, uid, ids, partner_id,add_text):
		logger.info('[KG OpenERP] Class: kg_purchase_order, Method: onchange_partner_id called...')
		partner = self.pool.get('res.partner')
		if not partner_id:
			return {'value': {
				'fiscal_position': False,
				'payment_term_id': False,
				}}
		supplier_address = partner.address_get(cr, uid, [partner_id], ['default'])
		supplier = partner.browse(cr, uid, partner_id)
		tot_add = (supplier.street or '')+ ' ' + (supplier.street2 or '') + '\n'+(supplier.city_id.name or '')+ ',' +(supplier.state_id.name or '') + '-' +(supplier.zip or '') + '\nPh:' + (supplier.phone or '')+ '\n' +(supplier.mobile or '')		
		return {'value': {
			'pricelist_id': supplier.property_product_pricelist_purchase.id,
			'fiscal_position': supplier.property_account_position and supplier.property_account_position.id or False,
			'payment_term_id': supplier.property_supplier_payment_term.id or False,
			'add_text' : tot_add or False
			}}
			
	def onchange_user(self, cr, uid, ids, user_id,location_id):
		value = {'location_id': ''}
		if user_id:			
			user_obj = self.pool.get('res.users')
			user_rec = user_obj.browse(cr,uid,user_id)
			dep_rec = user_rec.dep_name
			location = dep_rec.main_location.id
			value = {'location_id': location}
		return {'value':value}
		
	def confirm_po(self,cr,uid,ids, context=None):
		back_list = []
		obj = self.browse(cr,uid,ids[0])
		if obj.po_type == 'direct':
			for i in obj.order_line:
				pro_price = """ select price from ch_supplier_details where supplier_id=%s and partner_id = %s""" %(i.product_id.id,obj.partner_id.id)
				cr.execute(pro_price)
				data = cr.dictfetchall()
				if data:
					price_val = data[0]['price']
				else:
					price_val = 0.0	
				print "----------------------iii--------------",i.id
				print "-------------------price_unit------------",price_val
				cr.execute(""" update purchase_order_line set price_unit = %d where id = %s """ %(price_val,i.id))							
		for i in obj.order_line:
			val = []
			val_id = []
			line_id = i.id
			cr.execute(""" select id from ch_invoice_line where approved_status = 't' and product_id = %s """ %(i.product_id.id))
			data1 = cr.dictfetchall()
			if data1:
				for k in data1:
					val_id.append(k["id"])
				if val_id:
					cr.execute(""" select price_unit from ch_invoice_line where approved_status = 't' and id = %s """ %(max(val_id)))
					data2 = cr.dictfetchall()			
					if data2:
						for m in data2:
							recent_price =  m['price_unit']
					else: 
						recent_price = 0.00
				else: 
					recent_price = 0.00
				cr.execute(""" select price_unit from ch_invoice_line where approved_status = 't' and product_id = %s """ %(i.product_id.id))
				data = cr.dictfetchall()
				for j in data:
					val.append(j["price_unit"])
				if val:
					cr.execute(""" update purchase_order_line set least_price = %d , high_price = %d , recent_price = %d where id = %s """ %(int(min(val)),int(max(val)),recent_price,i.id))			
			else:
				cr.execute(""" update purchase_order_line set least_price = %d , high_price = %d , recent_price = %d where id = %s """ %(0.00,0.00,0.00,i.id))							
		approval = ''
		user_obj = self.pool.get('res.users').search(cr,uid,[('id','=',uid)])
		if user_obj:
			user_rec = self.pool.get('res.users').browse(cr,uid,user_obj[0])
		for item in obj.order_line:
			if item.price_type == 'per_kg':
				if item.product_id.uom_conversation_factor == 'two_dimension':
					if item.product_id.po_uom_in_kgs > 0:
						qty = item.product_qty * item.product_id.po_uom_in_kgs * item.length * item.breadth
				elif item.product_id.uom_conversation_factor == 'one_dimension':
					if item.product_id.po_uom_in_kgs > 0:
						qty = item.product_qty * item.product_id.po_uom_in_kgs
					else:
						qty = item.product_qty
				else:
					qty = item.product_qty
			else:
				qty = item.product_qty
			self.pool.get('purchase.order.line').write(cr,uid,item.id,{'quantity':qty})			
		date_order = obj.date_order
		date_order1 = datetime.strptime(date_order, '%Y-%m-%d')
		date_order1 = datetime.date(date_order1)
		today_date = datetime.date(today)
		today_new = today.date()
		bk_date = date.today() - timedelta(days=2)
		back_date = bk_date.strftime('%Y-%m-%d')
		d1 = today_new
		d2 = bk_date
		delta = d1 - d2
		for i in range(delta.days + 1):
			bkk_date = d1 - timedelta(days=i)
			backk_date = bkk_date.strftime('%Y-%m-%d')
			back_list.append(backk_date)
		sql = """ select id,name,date_order from purchase_order where state != 'draft' and state != 'cancel 'order by id desc limit 1 """
		cr.execute(sql)
		data = cr.dictfetchall()
		if obj.name == False:
			seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','purchase.order')])
			seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
			cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,obj.date_order))
			seq_name = cr.fetchone();
			self.write(cr,uid,ids,{'name':seq_name[0]})
		"""if obj.frieght_flag == True and obj.value1 == 0.00: 
			raise osv.except_osv(
					_('Warning'),
					_('You should specify Frieght charges!'))"""
		#~ if obj.amount_total <= 0:
			#~ raise osv.except_osv(
					#~ _('Purchase Order Value Error !'),
					#~ _('System not allow to confirm a Purchase Order with Zero Value'))	
		po_lines = obj.order_line
		cr.execute("""select piline_id from kg_poindent_po_line where po_order_id = %s"""  %(str(ids[0])))
		data = cr.dictfetchall()
		val = [d['piline_id'] for d in data if 'piline_id' in d] # Get a values form list of dict if the dict have with empty values
		for i in range(len(po_lines)):
			po_qty=po_lines[i].product_qty
			if po_lines[i].line_id:
				total = sum(wo.qty for wo in po_lines[i].line_id)
				if total <= po_qty:
					pass
				else:
					raise osv.except_osv(
						_('Warning!'),
						_('Please Check WO Qty'))
				wo_sql = """ select count(wo_id) as wo_tot,wo_id as wo_name from ch_purchase_wo where header_id = %s group by wo_id"""%(po_lines[i].id)
				cr.execute(wo_sql)		
				wo_data = cr.dictfetchall()
				for wo in wo_data:
					if wo['wo_tot'] > 1:
						raise osv.except_osv(
						_('Warning!'),
						_('%s This WO No. repeated'%(wo['wo_name'])))
					else:
						pass
		for order_line in obj.order_line:
			product_tax_amt = self._amount_line_tax(cr, uid, order_line, context=context)			
			cr.execute("""update purchase_order_line set product_tax_amt = %s where id = %s"""%(product_tax_amt,order_line.id))
		self.write(cr, uid, ids, {'state': 'confirmed',
								  'confirm_flag':'True',
								  'confirmed_by':uid,
								  'confirmed_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		if approval == 'yes' and obj.approval_flag == True:
			self.spl_po_apl_mail(cr,uid,ids,obj,context)
		return True
			
	def wkf_approve_order(self, cr, uid, ids, context=None):
		logger.info('[KG OpenERP] Class: kg_purchase_order, Method: wkf_approve_order called...')
		obj = self.browse(cr,uid,ids[0])
		if obj.po_type == 'direct':
			for i in obj.order_line:		
				if i.price_unit <= 0:
					raise osv.except_osv(
						_('Purchase Order Value Error !'),
						_('System not allow to confirm a Purchase Order with Zero Value'))	
		user_obj = self.pool.get('res.users').search(cr,uid,[('id','=',uid)])
		if user_obj:
			user_rec = self.pool.get('res.users').browse(cr,uid,user_obj[0])
		for item in obj.order_line:
			price_sql = """ 
						select line.price_unit
						from purchase_order_line line
						left join purchase_order po on (po.id = line.order_id)
						where line.product_id = %s and line.order_id != %s 
						and po.state in ('approved')
						order by line.price_unit desc limit 1"""%(item.product_id.id,obj.id)
			cr.execute(price_sql)		
			price_data = cr.dictfetchall()
			if price_data:
				if price_data[0]['price_unit'] < item.price_unit:
					if user_rec.special_approval == True:
						pass
					else:
						raise osv.except_osv(
							_('Warning'),
							_('%s price is exceeding last purchase price. It should be approved by Admin User'%(item.product_id.name)))
		if obj.payment_mode.term_category == 'advance':
			cr.execute("""select * from kg_supplier_advance where state='confirmed' and po_id= %s"""  %(str(ids[0])))
			data = cr.dictfetchall()
			if not data:
				raise osv.except_osv(
					_('Warning'),
					_('Advance is mandate for this PO'))
			else:
				pass		
		text_amount = number_to_text_convert_india.amount_to_text_india(obj.amount_total,"INR:")
		self.write(cr,uid,ids[0],{'text_amt':text_amount})
		line_obj = self.pool.get('purchase.order.line')
		line_rec = line_obj.search(cr, uid, [('order_id','=',obj.id)])
		for order_line in line_rec:
			order_line_rec = line_obj.browse(cr, uid, order_line)
			product_tax_amt = self._amount_line_tax(cr, uid, order_line_rec, context=context)
			cr.execute("""update purchase_order_line set product_tax_amt = %s where id = %s"""%(product_tax_amt,order_line_rec.id))
			line_obj.write(cr,uid,order_line,{'cancel_flag':'True','line_flag':'True','indent_state':True})
		self.write(cr, uid, ids, {'state': 'approved', 'date_approve': fields.date.context_today(self,cr,uid,context=context),'order_line.line_state' : 'confirm'})
		self.write(cr, uid, ids, {'approve_flag':'True',
								  'approved_by':uid,
								  'approved_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		po_order_obj=self.pool.get('purchase.order')
		po_id=obj.id
		po_lines = obj.order_line
		cr.execute("""select piline_id from kg_poindent_po_line where po_order_id = %s"""  %(str(ids[0])))
		data = cr.dictfetchall()
		val = [d['piline_id'] for d in data if 'piline_id' in d] # Get a values form list of dict if the dict have with empty values
		for i in range(len(po_lines)):
			po_qty=po_lines[i].product_qty
			if po_lines[i].line_id:
				total = sum(wo.qty for wo in po_lines[i].line_id)
				if total <= po_qty:
					pass
				else:
					raise osv.except_osv(
						_('Warning!'),
						_('Please Check WO Qty'))
				wo_sql = """ select count(wo_id) as wo_tot,wo_id as wo_name from ch_purchase_wo where header_id = %s group by wo_id"""%(po_lines[i].id)
				cr.execute(wo_sql)		
				wo_data = cr.dictfetchall()
				for wo in wo_data:
					if wo['wo_tot'] > 1:
						raise osv.except_osv(
						_('Warning!'),
						_('%s This WO No. repeated'%(wo['wo_name'])))
					else:
						pass
			if obj.po_type == 'frompi':
				if po_lines[i].pi_line_id and po_lines[i].group_flag == False:
					pi_line_id=po_lines[i].pi_line_id
					product = po_lines[i].product_id.name
					po_qty=po_lines[i].product_qty
					po_pending_qty=po_lines[i].pi_qty
					pi_pending_qty= po_pending_qty - po_qty
					if po_qty > po_pending_qty:
						raise osv.except_osv(
						_('If PO from Purchase Indent'),
						_('PO Qty should not be greater than purchase indent Qty. You can raise this PO Qty upto %s --FOR-- %s.'
									%(po_pending_qty, product)))
													
					pi_obj=self.pool.get('purchase.requisition.line')
					pi_line_obj=pi_obj.search(cr, uid, [('id','=',val[i])])
					pi_obj.write(cr,uid,pi_line_id.id,{'draft_flag' : False})
					sql = """ update purchase_requisition_line set pending_qty=%s where id = %s"""%(pi_pending_qty,pi_line_id.id)
					cr.execute(sql)
					if pi_pending_qty == 0:
						pi_obj.write(cr,uid,pi_line_id.id,{'line_state' : 'noprocess'})
					if po_lines[i].group_flag == True:
							self.update_product_pending_qty(cr,uid,ids,line=po_lines[i])
					else:
						print "All are correct Values and working fine"
			prod_obj = self.pool.get('product.product')
			prod_obj.write(cr,uid,po_lines[i].product_id.id,{'latest_price' : po_lines[i].price_unit})
				
	def spl_po_apl_mail(self,cr,uid,ids,obj,context=None):
		cr.execute("""select trans_po_spl_approval('po spl approval',"""+str(obj.id)+""")""")
		data = cr.fetchall();
		if data[0][0] is None:
			return False
		if data[0][0] is not None:	
			maildet = (str(data[0])).rsplit('~');
			cont = data[0][0].partition('UNWANTED.')		
			email_from = maildet[1]	
			if maildet[2]:	
				email_to = [maildet[2]]
			else:
				email_to = ['']			
			if maildet[3]:
				email_cc = [maildet[3]]	
			else:
				email_cc = ['']		
			ir_mail_server = self.pool.get('ir.mail_server')
			if maildet[4] != '':
				msg = ir_mail_server.build_email(
					email_from = email_from,
					email_to = email_to,
					subject = maildet[4],
					body = cont[0],
					email_cc = email_cc,
					object_id = ids and ('%s-%s' % (ids, 'kg.mail.settings')),
					subtype = 'html',
					subtype_alternative = 'plain')
				res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=1, context=context)
			else:
				pass
				
		return True
		
	def poindent_line_move(self, cr, uid,ids, poindent_lines , context=None):
		logger.info('[KG OpenERP] Class: kg_purchase_order, Method: poindent_line_move called...')
		return {}
		
	def _create_pickings(self, cr, uid, order, order_lines, picking_id=False, context=None):
		logger.info('[KG OpenERP] Class: kg_purchase_order, Method: _create_pickings called...')
		return {}
		# Default Openerp workflow stopped and inherited the function
		
	def action_cancel(self, cr, uid, ids, context=None):
		logger.info('[KG OpenERP] Class: kg_purchase_order, Method: action_cancel called...')
		wf_service = netsvc.LocalService("workflow")
		product_obj = self.pool.get('product.product')
		pi_line_obj = self.pool.get('purchase.requisition.line')
		po_grn_obj = self.pool.get('kg.po.grn')
		purchase = self.browse(cr, uid, ids[0], context=context)
		if not purchase.can_remark:
			raise osv.except_osv(
						_('Remarks Needed !!'),
						_('Enter Remark in Remarks Tab....'))
						
		if purchase.po_type == 'frompi':
			if purchase.state in ('draft','confirmed'):
				for line in purchase.order_line:
					sql = """ update purchase_requisition_line set draft_flag=False where line_state = 'process' and id = %s """%(line.pi_line_id.id)
					cr.execute(sql)
				self.write(cr,uid,ids,{'state':'cancel','cancel_user_id': uid,'cancel_date':time.strftime('%Y-%m-%d %H:%M:%S')})
			elif purchase.state == 'approved': 
				cr.execute(""" select grn_id from multiple_po where po_id = %s """ %(ids[0]))
				multi_po = cr.dictfetchall()
				if multi_po:
					for pick in multi_po:
						pick = po_grn_obj.browse(cr, uid, pick['grn_id'])
						if pick.state not in ('draft','cancel'):
							raise osv.except_osv(
								_('Unable to cancel this purchase order.'),
								_('First cancel all GRN related to this purchase order.'))
				for line in purchase.order_line:
					if line.pi_line_id and line.group_flag == False:
						pi_obj=self.pool.get('purchase.requisition.line')
						pi_line_obj=pi_obj.search(cr, uid, [('id','=',line.pi_line_id.id)])
						orig_pending_qty = line.pi_line_id.pending_qty
						po_qty = line.product_qty
						orig_pending_qty += po_qty
						sql = """ update purchase_requisition_line set line_state = 'process',pending_qty=%s where id = %s"""%(orig_pending_qty,line.pi_line_id.id)
						cr.execute(sql)
					else:
						if line.pi_line_id and line.group_flag == True:
							cr.execute(""" select piline_id from kg_poindent_po_line where po_order_id = %s """ %(str(ids[0])))
							data = cr.dictfetchall()
							val = [d['piline_id'] for d in data if 'piline_id' in d] 
							product_id = line.product_id.id
							product_record = product_obj.browse(cr, uid, product_id)
							list_line = pi_line_obj.search(cr,uid,[('id', 'in', val), ('product_id', '=', product_id)],context=context)
							po_used_qty = line.product_qty
							orig_pi_qty = line.group_qty
							for i in list_line:
								bro_record = pi_line_obj.browse(cr, uid,i)
								pi_pen_qty = bro_record.pending_qty
								pi_qty = orig_pi_qty + pi_pen_qty
								orig_pi_qty +=pi_pen_qty
								po_qty = po_used_qty
								if po_qty < pi_qty:
									pi_qty = pi_pen_qty + po_qty
									sql = """ update purchase_requisition_line set line_state = 'process',pending_qty=%s where id = %s"""%(pi_qty,bro_record.id)
									cr.execute(sql)
									break		
								else:
									remain_qty = po_used_qty - orig_pi_qty
									sql = """ update purchase_requisition_line set line_state = 'process',pending_qty=%s where id = %s"""%(orig_pi_qty,bro_record.id)
									cr.execute(sql)
									if remain_qty < 0:
										break
									po_used_qty = remain_qty
									orig_pi_qty = pi_pen_qty + remain_qty
				self.write(cr,uid,ids,{'state':'cancel','cancel_user_id': uid,'cancel_date':time.strftime('%Y-%m-%d %H:%M:%S')})					
			else:
				for line in purchase.order_line:
					pi_line_obj.write(cr,uid,line.pi_line_id.id,{'line_state' : 'noprocess'})		
		else:
			self.write(cr,uid,ids,{'state':'cancel','cancel_user_id': uid,'cancel_date':time.strftime('%Y-%m-%d %H:%M:%S')})
			
		"""		
		for inv in purchase.invoice_ids:
			
			if inv:
				wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_cancel', cr)
				"""
		for (id, name) in self.name_get(cr, uid, ids):
			wf_service.trg_validate(uid, 'purchase.order', id, 'purchase_cancel', cr)
		return True			
	
	def entry_reject(self, cr, uid, ids, context=None):
		pi_line_obj = self.pool.get('purchase.requisition.line')
		purchase = self.browse(cr, uid, ids[0], context=context)
		for line in purchase.order_line:
			pi_line_obj.write(cr,uid,line.pi_line_id.id,{'line_state' : 'noprocess'})	
		if not purchase.reject_remark:
			raise osv.except_osv(
				_('Remarks Needed !!'),
				_('Enter Remark in Remarks Tab....'))
		else:
			self.write(cr,uid,ids,{'state':'reject','rej_user_id': uid,'reject_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		return True
		
	def action_set_to_draft(self, cr, uid, ids, context=None):
		purchase = self.browse(cr, uid, ids[0], context=context)
		self.write(cr,uid,ids,{'state':'draft'})
		return True
		
	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(kg_purchase_order, self).write(cr, uid, ids, vals, context)
		
	def _check_line(self, cr, uid, ids, context=None):
		logger.info('[KG ERP] Class: kg_purchase_order, Method: _check_line called...')
		for po in self.browse(cr,uid,ids):
			if po.po_type != 'direct': 
				if po.kg_poindent_lines==[]:
					tot = 0.0
					for line in po.order_line:
						tot += line.price_subtotal
					if tot <= 0.0 or po.amount_total <=0:			
						return False
				return True
			
	def _check_total(self, cr, uid, ids, context=None):		
		po_rec = self.browse(cr, uid, ids[0])
		if po_rec.kg_seq_id:
			for line in po_rec.order_line:				
				if line.price_subtotal <= 0:
					return False					
		return True
			
	def print_quotation(self, cr, uid, ids, context=None):		
		assert len(ids) == 1, 'This option should only be used for a single id at a time'
		wf_service = netsvc.LocalService("workflow")
		wf_service.trg_validate(uid, 'purchase.order', ids[0], 'send_rfq', cr)
		datas = {
				 'model': 'purchase.order',
				 'ids': ids,
				 'form': self.read(cr, uid, ids[0], context=context),
		}
		return {'type': 'ir.actions.report.xml', 'report_name': 'onscreen.po.report', 'datas': datas, 'ids' : ids, 'nodestroy': True}
	
kg_purchase_order()


class kg_purchase_order_line(osv.osv):
		
	def onchange_unit_price(self,cr,uid,ids,price_unit,product_qty,context = None):
		tot_price = 0.00
		if price_unit >0.00 and product_qty > 0.00:
			tot_price = (price_unit * product_qty)
		return {'value':{'tot_price':(round(tot_price,2)),'kg_discount': 0.00}}
		
	def onchange_discount_value_calc(self, cr, uid, ids, kg_discount_per, product_qty, price_unit , tot_price):
		logger.info('[KG OpenERP] Class: kg_purchase_order_line, Method: onchange_discount_value_calc called...')
		discount_value_price = 0.00
		if kg_discount_per > 25:
			raise osv.except_osv(_(' Warning!!'),_("Discount percentage must be lesser than 25 % !") )			
		if kg_discount_per:
			discount_value_price = (tot_price/100.00)*kg_discount_per
		discount_value = (product_qty * price_unit) * kg_discount_per / 100.00
		return {'value': {'kg_discount_per_value': discount_value,'kg_discount': discount_value_price}}
		
	def onchange_disc_amt(self,cr,uid,ids,kg_discount,product_qty,price_unit,kg_disc_amt_per,tot_price):
		logger.info('[KG OpenERP] Class: kg_purchase_order_line, Method: onchange_disc_amt called...')
		disc_per = 0.00
		if kg_discount:
			disc_per = (kg_discount*100)/tot_price
			kg_discount = kg_discount + 0.00
			amt_to_per = (kg_discount / (product_qty * price_unit or 1.0 )) * 100.00
			return {'value': {'kg_disc_amt_per': amt_to_per,'kg_discount_per': disc_per}}	
		else:
			return {'value': {'kg_disc_amt_per': 0.0,'kg_discount_per': disc_per}}			
	

		

			
	def _amount_line(self, cr, uid, ids, prop, arg, context=None):
		logger.info('[KG OpenERP] Class: kg_purchase_order_line, Method: _amount_line called...')
		cur_obj=self.pool.get('res.currency')
		tax_obj = self.pool.get('account.tax')
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			# Qty Calculation
			qty = 0.00
			if line.price_type == 'per_kg':
				if line.product_id.uom_conversation_factor == 'two_dimension':
					if line.product_id.po_uom_in_kgs > 0:
						qty = line.product_qty * line.product_id.po_uom_in_kgs * line.length * line.breadth
				elif line.product_id.uom_conversation_factor == 'one_dimension':
					if line.product_id.po_uom_in_kgs > 0:
						qty = line.product_qty * line.product_id.po_uom_in_kgs
					else:
						qty = line.product_qty
				else:
					qty = line.product_qty
			else:
				qty = line.product_qty
			
			# Price Calculation
			price_amt = 0
			if line.price_type == 'per_kg':
				if line.product_id.po_uom_in_kgs > 0:
					price_amt = line.product_qty / line.product_id.po_uom_in_kgs * line.price_unit
			else:
				price_amt = qty * line.price_unit
			
			amt_to_per = (line.kg_discount / (qty * line.price_unit or 1.0 )) * 100
			kg_discount_per = line.kg_discount_per
			tot_discount_per = amt_to_per 
			price = line.price_unit * (1 - (tot_discount_per or 0.0) / 100.0)
			taxes = tax_obj.compute_all(cr, uid, line.taxes_id, price, qty, line.product_id, line.order_id.partner_id)
			cur = line.order_id.pricelist_id.currency_id
			res[line.id] = cur_obj.round(cr, uid, cur, taxes['total_included'])
		return res
		
	_name = "purchase.order.line"
	_inherit = "purchase.order.line"
	
	_columns = {

	'price_subtotal': fields.function(_amount_line, store=True,string='Subtotal', digits_compute= dp.get_precision('Account')),
	'kg_discount': fields.float('Discount'),
	'kg_disc_amt_per': fields.float('Disc Amt(%)', digits_compute= dp.get_precision('Discount')),
	'price_unit': fields.float('Unit Price', required=True),
	'product_qty': fields.float('Quantity'),
	'pending_qty': fields.float('Pending Qty'),
	'received_qty':fields.float('Received Qty'),
	'tax_amt':fields.float('tax amt'),
	'cancel_qty':fields.float('Cancel Qty'),
	'pi_qty':fields.float('Indent Qty'),
	'group_qty':fields.float('Group Qty'),
	'product_uom': fields.many2one('product.uom', 'UOM', readonly=True),
	'name': fields.text('Description'),
	'date_planned': fields.date('Scheduled Date', select=True),
	'note': fields.text('Remarks'),
	'pi_line_id':fields.many2one('purchase.requisition.line','PI Line'),
	'po_order':fields.one2many('kg.po.line','line_id','PO order Line'),
	'kg_discount_per': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount')),
	'kg_discount_per_value': fields.float('Discount(%)Value', digits_compute= dp.get_precision('Discount')),
	'line_state': fields.selection([('draft', 'Active'),('confirm','Confirmed'),('cancel', 'Cancel')], 'State'),
	'group_flag': fields.boolean('Group By'),
	'total_disc': fields.float('Discount Amt'),
	'line_bill': fields.boolean('PO Bill'),
	'cancel_remark':fields.text('Cancel Remarks'),
	'cancel_flag':fields.boolean('Cancel Flag'),
	'move_line_id':fields.many2one('stock.move','Move Id'),
	'line_flag':fields.boolean('Line Flag'),
	'po_specification':fields.text('Specification'),
	'product_tax_amt':fields.float('Tax Amount'),
	'brand_id':fields.many2one('kg.brand.master','Brand',domain="[('product_ids','in',(product_id)),('state','in',('draft','confirmed','approved'))]"),
	'least_price': fields.float('Least Price'),
	'high_price': fields.float('Highest Price'),
	'recent_price': fields.float('Recent Price'),
	'price_type': fields.selection([('po_uom','PO UOM'),('per_kg','Per Kg')],'Price Type'),
	'line_id': fields.one2many('ch.purchase.wo','header_id','Ch Line Id'),
	'uom_conversation_factor': fields.related('product_id','uom_conversation_factor', type='selection',selection=UOM_CONVERSATION, string='UOM Conversation Factor',store=True,required=False),
	'length': fields.float('Length',digits=(16,4)),
	'breadth': fields.float('Breadth',digits=(16,4)),
	'quantity': fields.float('Weight(KGs)'),
	'indent_state': fields.boolean('Indent state'),
	'tot_price': fields.float('Total Amount'),
	
	}
	
	_defaults = {
	
	'date_planned' : fields.date.context_today,
	'line_state' : 'draft',
	'name':'PO',
	'cancel_flag': False,
	'price_type': 'po_uom',
	
	}
	
	
	def _discount_per(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.kg_discount_per:
			if rec.kg_discount_per > 25:
				raise osv.except_osv(_(' Warning!!'),_("Discount percentage must be lesser than 25 % !") )
		return True	
				
	
	def create(self, cr, uid, vals,context=None):
		if vals['product_id']:
			product_obj =  self.pool.get('product.product')
			product_rec = product_obj.browse(cr,uid,vals['product_id'])
			if product_rec.uom_id.id != product_rec.uom_po_id.id:
				vals.update({
							'product_uom':product_rec.uom_po_id.id,
							})
			elif  product_rec.uom_id.id == product_rec.uom_po_id.id:
				vals.update({
							'product_uom':product_rec.uom_id.id,
							})
		order =  super(kg_purchase_order_line, self).create(cr, uid, vals, context=context)
		return order
		
	
			
	
	def _check_length(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.order_id.po_type != 'frompi':
			if rec.uom_conversation_factor == 'two_dimension':
				if rec.length <= 0:
					return False					
		return True
		
	def _check_breadth(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.order_id.po_type != 'frompi':
			if rec.uom_conversation_factor == 'two_dimension':
				if rec.breadth <= 0:
					return False					
		return True
		
	_constraints = [
		
		(_check_length,'You can not save this Length with Zero value !',['Length']),
		(_check_breadth,'You can not save this Breadth with Zero value !',['Breadth']),
		(_discount_per,'Discount value must be Lesser than 25 % !',['Discount (%)']),
		
	]
	
	
	def onchange_qty(self, cr, uid, ids,product_qty,pending_qty,pi_line_id,pi_qty,uom_conversation_factor,length,breadth,price_type,product_id,price_unit):
		logger.info('[KG OpenERP] Class: kg_purchase_order_line, Method: onchange_qty called...')
		# Need to do block flow
		value = {'pending_qty': '','quantity': 0}
		quantity = 0
		tot_price = 0.00
		if price_unit >0.00 and product_qty > 0.00:
			tot_price = (price_unit * product_qty)		
			if price_type == 'per_kg':
				prod_rec = self.pool.get('product.product').browse(cr,uid,product_id)
				if uom_conversation_factor == 'two_dimension':
					if prod_rec.po_uom_in_kgs > 0:
						quantity = product_qty * prod_rec.po_uom_in_kgs * length * breadth
				elif uom_conversation_factor == 'one_dimension':
					if prod_rec.po_uom_in_kgs > 0:
						quantity = product_qty * prod_rec.po_uom_in_kgs
					else:
						quantity = product_qty
				else:
					quantity = product_qty
			else:
				quantity = product_qty
			if pi_line_id:
				if product_qty and product_qty > pi_qty:
					raise osv.except_osv(_(' If PO From PI !!'),_("PO Qty can not be greater than Indent Qty !") )
				else:
					value = {'pending_qty': product_qty,'quantity': quantity,'tot_price':(round(tot_price,2)),'kg_discount': 0.00}
			else:
				value = {'pending_qty': product_qty,'quantity': quantity,'tot_price':(round(tot_price,2)),'kg_discount': 0.00}
			if uom_conversation_factor == 'two_dimension':
				if length <= 0:
					raise osv.except_osv(_(' Warning !!'),_("You can not save this Length with Zero value !") )
				if breadth <= 0:
					raise osv.except_osv(_(' Warning !!'),_("You can not save this Breadth with Zero value !") )
				
		return {'value': value}
		
	def onchange_price_type(self, cr, uid, ids,product_qty,uom_conversation_factor,length,breadth,price_type,product_id):
		value = {'quantity': 0}
		quantity = 0
		if price_type == 'per_kg':
			prod_rec = self.pool.get('product.product').browse(cr,uid,product_id)
			if uom_conversation_factor == 'two_dimension':
				if prod_rec.po_uom_in_kgs > 0:
					quantity = product_qty * prod_rec.po_uom_in_kgs * length * breadth
			elif uom_conversation_factor == 'one_dimension':
				if prod_rec.po_uom_in_kgs > 0:
					quantity = product_qty * prod_rec.po_uom_in_kgs
				else:
					quantity = product_qty
			else:
				quantity = product_qty
		else:
			quantity = product_qty
		value = {'quantity': quantity}
		return {'value': value}
		
	def pol_cancel(self, cr, uid, ids, context=None):
		logger.info('[KG OpenERP] Class: kg_purchase_order_line, Method: pol_cancel called...')
		line_rec = self.browse(cr,uid,ids)
		if line_rec[0].product_qty != line_rec[0].pending_qty:
			raise osv.except_osv(
				_('Few Quanties are Received !! '),
				_('You can cancel a PO line before receiving product'))
		if not line_rec[0].cancel_remark:
			raise osv.except_osv(
				_('Remarks !! '),
				_('Enter the remarks for po line cancel'))
		else:				
			self.write(cr,uid,ids,{'line_state':'cancel'})
		return True

			
	def unlink(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for rec in self.browse(cr, uid, ids, context=context):
			parent_rec = rec.order_id
			if parent_rec.state not in ['draft','confirmed']:
				raise osv.except_osv(_('Invalid Action!'), _('Cannot delete a purchase order line which is in state \'%s\'.') %(parent_rec.state,))
			else:
				if parent_rec.po_type == 'direct' or parent_rec.po_type == 'fromquote':
					return super(kg_purchase_order_line, self).unlink(cr, uid, ids, context=context)
				else:
					order_id = parent_rec.id
					pi_line_rec = rec.pi_line_id
					pi_line_id = rec.pi_line_id.id
					pi_line_rec.write({'line_state' : 'process','draft_flag':False})
					del_sql = """ delete from kg_poindent_po_line where po_order_id=%s and piline_id=%s """ %(order_id,pi_line_id)
					cr.execute(del_sql)				
					return super(kg_purchase_order_line, self).unlink(cr, uid, ids, context=context)
				
	def get_old_details(self,cr,uid,ids,context=None):
		rec = self.browse(cr, uid, ids[0])
		last_obj = self.pool.get('kg.po.line')
		sql = """ select id,price_unit,order_id,kg_discount,kg_discount_per from purchase_order_line where product_id=%s and order_id != %s order by id desc limit 5 """%(rec.product_id.id,rec.order_id.id)
		cr.execute(sql)
		data = cr.dictfetchall()
		last_ids = last_obj.search(cr, uid, [('line_id','=',rec.id)])
		if last_ids:
			for i in last_ids:
				last_obj.unlink(cr, uid, i, context=context)
		for item in data:
			po_rec = self.pool.get('purchase.order').browse(cr,uid,item['order_id'])
			vals = {
			
				'line_id':item['id'],
				'supp_name':po_rec.partner_id.id,
				'date_order':po_rec.date_order,
				'other_ch':po_rec.other_charge,
				'kg_discount':item['kg_discount'],
				'kg_discount_per':item['kg_discount_per'],
				'price_unit':item['price_unit'],
				'po_no': po_rec.id,
			
			}
			po_entry = self.write(cr,uid,rec.id,{'po_order':[(0,0,vals)]})
		return data
			
kg_purchase_order_line()

class kg_po_line(osv.osv):
		
	_name = "kg.po.line"
	
	_columns = {
	
			'line_id': fields.many2one('purchase.order.line', 'PO No'),
			'kg_discount': fields.float('Discount Amount'),
			'kg_discount_per': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount')),
			'price_unit': fields.float('Unit Price', size=120),
			'date_order':fields.date('PO Date'),
			'supp_name':fields.many2one('res.partner','Supplier',size=120),
			'other_ch':fields.float('Other Charges',size=128),
			'po_no': fields.many2one('purchase.order','PO No'),
	
	}
	
kg_po_line()


class kg_purchase_order_expense_track(osv.osv):

	_name = "kg.purchase.order.expense.track"
	_description = "kg expense track"
	
	_columns = {
		
			'expense_id': fields.many2one('purchase.order', 'Expense Track'),
			'name': fields.char('Number', size=128, select=True,readonly=False),
			'date': fields.date('Creation Date'),
			'company_id': fields.many2one('res.company', 'Company Name'),
			'description': fields.char('Description'),
			'expense_amt': fields.float('Amount'),
			'expense': fields.many2one('kg.expense.master','Expense',domain=[('state','=','approved')]),
		
	}
	
	_defaults = {
		
			'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.purchase.order.expense.track', context=c),
			'date' : fields.date.context_today,
	
		}
	
kg_purchase_order_expense_track()

class ch_purchase_wo(osv.osv):
	
	_name = "ch.purchase.wo"
	_description = "Ch Purchase WO"
	
	_columns = {

			'header_id': fields.many2one('purchase.order.line', 'PO Line'),
			'wo_id': fields.char('WO No.'),
			'qty': fields.float('Qty'),
	
	}
	

	def _check_qty(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.qty <= 0.00:
			return False					
		return True
		
	_constraints = [
	
		(_check_qty,'You cannot save with zero qty !',['Qty']),
		
		]
		
ch_purchase_wo()

