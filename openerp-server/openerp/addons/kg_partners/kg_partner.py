from functools import partial
import logging
from lxml import etree
from lxml.builder import E
import openerp
import time
from openerp import SUPERUSER_ID
from openerp import pooler, tools
import openerp.exceptions
from openerp.osv import fields,osv
from openerp.osv.orm import browse_record
from openerp.tools.translate import _
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import datetime
from lxml import etree
import math
import pytz
from datetime import datetime
import openerp
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools.yaml_import import is_comment

class kg_partner(osv.osv):

	_name = "res.partner"
	_inherit = "res.partner"
	_description = "Partner Managment"
	
	def _get_modify(self, cr, uid, ids, field_name, arg,  context=None):
		res={}
		if field_name == 'modify':
			for h in self.browse(cr, uid, ids, context=None):
				res[h.id] = 'no'
				if h.sup_state == 'approved':
					cr.execute(""" select * from 
					(SELECT tc.table_schema, tc.constraint_name, tc.table_name, kcu.column_name, ccu.table_name
					AS foreign_table_name, ccu.column_name AS foreign_column_name
					FROM information_schema.table_constraints tc
					JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
					JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
					WHERE constraint_type = 'FOREIGN KEY'
					AND ccu.table_name='%s')
					as sam  """ %('res_partner'))
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
	
	'city_id' : fields.many2one('res.city', 'City'),
	'tin_no' : fields.char('TIN'),
	'vat_no' : fields.char('VAT'),
	'pan_no' : fields.char('PAN'),
	'tan_no' : fields.char('TAN'),
	'cst_no' : fields.char('CST'),
	'gst_no' : fields.char('GST'),
	'supply_type': fields.selection([('material','Material'),('service','Service'),('contractor','Contractor'),('labour','Labour'),('all','All')],'Supply Type'),
	'company_type': fields.selection([('individual','Individual'),('company','Company')],'Type'),
	'tds': fields.selection([('yes','Yes'),('no','No')],'TDS Applicable'),
	'grade': fields.selection([('a','A'),('b','B'),('c','C')],'Grade'),
	'payment_id': fields.many2one('kg.payment.master','Payment Terms'),
	'language': fields.selection([('tamil', 'Tamil'),('english', 'English'),('hindi', 'Hindi'),('malayalam', 'Malayalam'),('others','Others')],'Preferred Language'),
	'cheque_in_favour': fields.char('Cheque in Favor Of'),
	'advance_limit': fields.float('Credit Limit'),
	'contact_person': fields.char('Contact Person', size=128),
	'landmark': fields.char('Landmark', size=128),
	'partner_state': fields.selection([('draft','Draft'),('confirm','WFA'),('approve','Approved'),('reject','Rejected'),('cancel','Cancelled')],'Status'),
	'group_flag': fields.boolean('Is Group Company'),
	'delivery_id': fields.many2one('kg.delivery.master','Delivery Type'),
	'creation_date': fields.datetime('Created Date',readonly=True),
	'created_by': fields.many2one('res.users', 'Created by',readonly=True),
	'confirmed_date': fields.datetime('Confirmed Date',readonly=True),
	'confirmed_by': fields.many2one('res.users','Confirmed By',readonly=True),
	'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
	'reject_date': fields.datetime('Rejected Date', readonly=True),
	'approved_date': fields.datetime('Approved Date',readonly=True),
	'approved_by': fields.many2one('res.users','Approved By',readonly=True),
	'cancel_date': fields.datetime('Cancelled Date', readonly=True),
	'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
	'updated_date': fields.datetime('Last Updated Date',readonly=True),
	'updated_by': fields.many2one('res.users','Last Updated By',readonly=True),
	'con_designation': fields.char('Designation'),
	'con_whatsapp': fields.char('Whatsapp No'),
	'delivery_ids':fields.one2many('kg.delivery.address', 'src_id', 'Delivery Address'),
	'billing_ids':fields.one2many('kg.billing.address', 'bill_id', 'Billing Address'),
	'consult_ids':fields.one2many('kg.consultant.fee', 'consult_id', 'Consultant Fees'),
	'dealer': fields.boolean('Dealer'),
	'economic_category': fields.selection([('budget','Budget'),('loyalty','Loyalty')],'Economic Category'),
	'sector': fields.selection([('cp','CP'),('ip','IP'),('both','Both')],'Marketing Division'),
	'dealer_id': fields.many2one('res.partner','Dealer Name',domain=[('dealer','=',True)]),
	'remark': fields.text('Approve/Reject'),
	'cancel_remark': fields.text('Cancel Remarks'),
	'modify': fields.function(_get_modify, string='Modify', method=True, type='char', size=3),
	'user_ref_id': fields.many2one('res.users','User Name'),
	'adhar_id': fields.char('Adhar ID'),
	'contractor': fields.boolean('Contractor'),
	'tin_flag': fields.boolean('TIN Flag'),
	'mobile_2': fields.char('Mobile2'),
	'birthdate': fields.datetime('birthdate'),
	
	}
	
	_defaults = {
	  
	  'is_company': True,
	  'creation_date': fields.datetime.now,
	  'created_by': lambda obj, cr, uid, context: uid,
	  'partner_state': 'draft',	  
	  'company_type': 'company',	  
	  'supply_type': 'material',	  
	  'modify': 'no',
	  'tin_flag': False,
		 
	}

	def onchange_city(self, cr, uid, ids, city_id, context=None):
		if city_id:
			state_id = self.pool.get('res.city').browse(cr, uid, city_id, context).state_id.id
			return {'value':{'state_id':state_id}}
		return {}
	
	def onchange_zip(self,cr,uid,ids,zip,context=None):
		if len(str(zip)) in (6,7,8):
			value = {'zip':zip}
		else:
			raise osv.except_osv(_('Check zip number !!'),
				_('Please enter 6-8 digit number !!'))
		if zip.isdigit() == False:
			raise osv.except_osv(_('Check zip number !!'),
				_('Please enter numeric values !!'))
		return {'value': value}
			
			
	def confirm_partner(self, cr, uid, ids, context=None): 
		rec = self.browse(cr, uid, ids[0])
		self.write(cr, uid, ids, {'partner_state': 'confirm','confirmed_by':uid,'confirmed_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		
		return True
		
	def reject_partner(self, cr, uid, ids, context=None): 
		rec = self.browse(cr, uid, ids[0])
		if rec.remark:
			self.write(cr, uid, ids, {'partner_state': 'reject','update_user_id':uid,'reject_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
		return True
		
	def approve_partner(self, cr, uid, ids, context=None): 
		rec = self.browse(cr, uid, ids[0])
		self.write(cr, uid, ids, {'partner_state': 'approve','approved_by':uid,'approved_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		
		return True

	def entry_draft(self,cr,uid,ids,context=None):
		a = datetime.now()
		dt_time = a.strftime('%m/%d/%Y %H:%M:%S')		
		self.write(cr, uid, ids, {'sup_state': 'draft'})
		return True
		
	def entry_cancel(self,cr,uid,ids,context=None):
		a = datetime.now()
		dt_time = a.strftime('%m/%d/%Y %H:%M:%S')			
		rec = self.browse(cr,uid,ids[0])
		if rec.cancel_remark:
			self.write(cr, uid, ids, {'sup_state': 'cancel','cancel_user_id': uid, 'cancel_date': dt_time})
		else:
			raise osv.except_osv(_('Cancel remark is must !!'),
				_('Enter the remarks in Cancel remarks field !!'))
		return True
		
	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_by':uid})
		return super(kg_partner, self).write(cr, uid, ids, vals, context)
	
	def _check_zip(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.zip:
			if len(str(rec.zip)) in (6,7,8) and rec.zip.isdigit() == True:
				return True
		else:
			return True
		return False
		
	def _check_tin(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.tin_no:
			if len(str(rec.tin_no)) == 11 and rec.tin_no.isdigit() == True:
				return True
		else:
			return True
		return False
		
	def _check_cst(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.cst_no:
			if len(str(rec.cst_no)) == 11 and rec.cst_no.isdigit() == True:
				return True
		else:
			return True
		return False
		
	def _check_vat(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.vat_no:
			if len(str(rec.vat_no)) == 15:
				return True
		else:
			return True
		return False
	
	def _check_phone(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.phone:
			if len(str(rec.phone)) in (8,9,10,11,12,13,14,15) and rec.phone.isdigit() == True:
				return True
		else:
			return True
		return False
	
	def _check_website(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.website != False:
			if re.match('www.(?:www)?(?:[\w-]{2,255}(?:\.\w{2,6}){1,2})(?:/[\w&%?#-]{1,300})?',rec.website):
				return True
			else:
				return False
		return True
		
		#check tan no
		
	def _check_tan(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.tan_no != False:
			for item in rec.tan_no:
				if  len(str(rec.tan_no))==10 and item.isalnum() == True:
					return True
				else:
					return False
		return True
		
		#check Pan no
		
	def _check_pan(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.pan_no != False:
			for item in rec.pan_no:
				if  len(str(rec.tan_no))==10 and item.isalnum() == True:
					return True
				else:
					return False
		return True
		
		#check adhar no
		
	def _check_adhar(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.adhar_id != False:
			for item in rec.adhar_id:
				if len(str(rec.tan_no))==12 and item.isdigit() == True:
					return True
				else:
					return False
		return True
		
		#check gst no
		
	def _check_gst(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.gst_no != False:
			for item in rec.gst_no:
				if len(str(rec.gst_no))>=11 and item.isalnum() == True:
					return True
				else:
					return False
		return True

	def _check_ifsc(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.bank_ids:
			for item in rec.bank_ids:
				if item.bank_bic:
					if len(str(item.bank_bic)) == 11:
						return True
				else:
					return True
		else:
			return True
		return False
			
	def _check_acc_no(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.bank_ids:
			for item in rec.bank_ids:
				if item.acc_number:
					if len(str(item.acc_number)) in (6,7,8,9,10,11,12,13,14,15,16,17,18) and item.acc_number.isdigit() == True:
						return True
				else:
					return True
		else:
			return True
		return False
		
	def _check_mobile_no(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.mobile_2:
			if len(str(rec.mobile_2)) in (10,11,12) and rec.mobile_2.isdigit() == True:
				return True
		else:
			return True
		return False
	
			
kg_partner()



class kg_delivery_address(osv.osv):

	_name = "kg.delivery.address"
	_description = "Delivery Address"
	
	_columns = {

	'src_id': fields.many2one('res.partner', 'Partner Master'),
	'street': fields.char('Street', size=128,select=True),
	'street1': fields.char('Street 1', size=128,select=True),
	'landmark': fields.char('Landmark',size=128),
	'city_id': fields.many2one('res.city', 'City',select=True),
	'state_id': fields.many2one('res.country.state', 'State'),
	'country_id': fields.many2one('res.country', 'Country'),	
	'contact_no': fields.char('Contact No', size=128),
	'zip': fields.char('ZIP', size=128),
	'date': fields.date('Creation Date'),
	'default': fields.boolean('Default'),
	
	}

	_defaults = {

	'date' : fields.date.context_today,

	} 
	
kg_delivery_address()

class kg_billing_address(osv.osv):

	_name = "kg.billing.address"
	_description = "Billing Address"
	
	_columns = {

	'bill_id': fields.many2one('res.partner', 'Partner Master'),
	'street': fields.char('Street', size=128,select=True),
	'street1': fields.char('Street 1', size=128,select=True),
	'landmark': fields.char('Landmark',size=128),
	'city_id': fields.many2one('res.city', 'City',select=True),
	'state_id': fields.many2one('res.country.state', 'State'),
	'country_id': fields.many2one('res.country', 'Country'),	
	'contact_no': fields.char('Contact No', size=128),
	'zip': fields.char('ZIP', size=128),
	'date': fields.date('Creation Date'),
	'default': fields.boolean('Default'),
	
	}
	
	
#check contact number

	def _validate_phone_no(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.contact_no:
			if len(str(rec.contact_no)) in (10,11,12) and rec.contact_no.isdigit() == True:
				return True
			else:
				return False
		return True				
	
	_defaults = {

	'date' : fields.date.context_today,

	} 

kg_billing_address()


class kg_consultant_fee(osv.osv):

	_name = "kg.consultant.fee"
	_description = "Consultant Fees"
	
	_columns = {

	'consult_id': fields.many2one('res.partner', 'Partner Master'),
	'effective_date': fields.date('Effective Date'),
	'value': fields.float('Value (%)'),
	'state': fields.selection([('active','Active'),('expire','Expired')],'Status'),
	'read_flag': fields.boolean('Read Flag'),
	
	}

	_defaults = {

	'state' : 'active',
	'read_flag': False,
	
	} 
	
	def create(self, cr, uid, vals, context=None):
		new_id = super(kg_consultant_fee, self).create(cr, uid, vals, context=context)
		partner = self.browse(cr, uid, new_id, context=context)
		
		obj = self.search(cr,uid,([('consult_id','=',vals['consult_id'])]))
		if obj:
			for item in obj:
				self.write(cr,uid,item,{'state':'expire','read_flag':True})
			self.write(cr,uid,obj[-1],{'state':'active','read_flag':False})
		
		return new_id
		
kg_consultant_fee()
