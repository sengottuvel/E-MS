import os
import re
import openerp
from openerp import SUPERUSER_ID, tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools import image_resize_image
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import datetime
from datetime import datetime

class multi_company_default(osv.osv):
	"""
	Manage multi company default value
	"""
	_name = 'multi_company.default'
	_description = 'Default multi company'
	_order = 'company_id,sequence,id'

	_columns = {
		'sequence': fields.integer('Sequence'),
		'name': fields.char('Name', size=256, required=True, help='Name it to easily find a record'),
		'company_id': fields.many2one('res.company', 'Main Company', required=True,
			help='Company where the user is connected'),
		'company_dest_id': fields.many2one('res.company', 'Default Company', required=True,
			help='Company to store the current record'),
		'object_id': fields.many2one('ir.model', 'Object', required=True,
			help='Object affected by this rule'),
		'expression': fields.char('Expression', size=256, required=True,
			help='Expression, must be True to match\nuse context.get or user (browse)'),
		'field_id': fields.many2one('ir.model.fields', 'Field', help='Select field property'),
	}

	_defaults = {
		'expression': 'True',
		'sequence': 100,
	}

	def copy(self, cr, uid, id, default=None, context=None):
		"""
		Add (copy) in the name when duplicate record
		"""
		if not context:
			context = {}
		if not default:
			default = {}
		company = self.browse(cr, uid, id, context=context)
		default = default.copy()
		default['name'] = company.name + _(' (copy)')
		return super(multi_company_default, self).copy(cr, uid, id, default, context=context)

multi_company_default()

class res_company(osv.osv):
	_name = "res.company"
	_description = 'Companies'
	_order = 'name'

	def _get_address_data(self, cr, uid, ids, field_names, arg, context=None):
		""" Read the 'address' functional fields. """
		result = {}
		part_obj = self.pool.get('res.partner')
		for company in self.browse(cr, uid, ids, context=context):
			result[company.id] = {}.fromkeys(field_names, False)
			if company.partner_id:
				address_data = part_obj.address_get(cr, openerp.SUPERUSER_ID, [company.partner_id.id], adr_pref=['default'])
				if address_data['default']:
					address = part_obj.read(cr, openerp.SUPERUSER_ID, address_data['default'], field_names, context=context)
					for field in field_names:
						result[company.id][field] = address[field] or False
		return result

	def _set_address_data(self, cr, uid, company_id, name, value, arg, context=None):
		""" Write the 'address' functional fields. """
		company = self.browse(cr, uid, company_id, context=context)
		if company.partner_id:
			part_obj = self.pool.get('res.partner')
			address_data = part_obj.address_get(cr, uid, [company.partner_id.id], adr_pref=['default'])
			address = address_data['default']
			if address:
				part_obj.write(cr, uid, [address], {name: value or False}, context=context)
			else:
				part_obj.create(cr, uid, {name: value or False, 'parent_id': company.partner_id.id}, context=context)
		return True

	def _get_logo_web(self, cr, uid, ids, _field_name, _args, context=None):
		result = dict.fromkeys(ids, False)
		for record in self.browse(cr, uid, ids, context=context):
			size = (180, None)
			result[record.id] = image_resize_image(record.partner_id.image, size)
		return result

	def _get_companies_from_partner(self, cr, uid, ids, context=None):
		return self.pool['res.company'].search(cr, uid, [('partner_id', 'in', ids)], context=context)
		
#cancel function
		
	def _get_modify(self, cr, uid, ids, field_name, arg,  context=None):
		res={}
		if field_name == 'modify':
			for h in self.browse(cr, uid, ids, context=None):
				res[h.id] = 'no'
				if h.state == 'approved':
					cr.execute(""" select * from 
					(SELECT tc.table_schema, tc.constraint_name, tc.table_name, kcu.column_name, ccu.table_name
					AS foreign_table_name, ccu.column_name AS foreign_column_name
					FROM information_schema.table_constraints tc
					JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
					JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
					WHERE constraint_type = 'FOREIGN KEY'
					AND ccu.table_name='%s')
					as sam  """ %('res_company'))
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
		'name': fields.char('Name', size=128, required=True, store=True,readonly=True, states={'draft':[('readonly',False)]}),
		'parent_id': fields.many2one('res.company', 'Parent Company', select=True,readonly=True, states={'draft':[('readonly',False)]}),
		'child_ids': fields.one2many('res.company', 'parent_id', 'Child Companies',readonly=True, states={'draft':[('readonly',False)]}),
		'partner_id': fields.many2one('res.partner', 'Partner', required=True,readonly=True, states={'draft':[('readonly',False)]}),
		'rml_header': fields.text('RML Header', required=True,readonly=True, states={'draft':[('readonly',False)]}),
		'rml_header1': fields.char('Company Tagline', size=200, help="Appears by default on the top right corner of your printed documents (report header).",readonly=True, states={'draft':[('readonly',False)]}),
		'rml_header2': fields.text('RML Internal Header', required=True,readonly=True, states={'draft':[('readonly',False)]}),
		'rml_header3': fields.text('RML Internal Header for Landscape Reports', required=True,readonly=True, states={'draft':[('readonly',False)]}),
		'rml_footer': fields.text('Report Footer', help="Footer text displayed at the bottom of all reports.",readonly=True, states={'draft':[('readonly',False)]}),
		'rml_footer_readonly': fields.related('rml_footer', type='text', string='Report Footer', readonly=True),
		'custom_footer': fields.boolean('Custom Footer', help="Check this to define the report footer manually.  Otherwise it will be filled in automatically.",readonly=True, states={'draft':[('readonly',False)]}),
		'logo': fields.related('partner_id', 'image', string="Logo", type="binary",readonly=True, states={'draft':[('readonly',False)]}),
		'logo_web': fields.function(_get_logo_web, string="Logo Web", type="binary", store={
			'res.company': (lambda s, c, u, i, x: i, ['partner_id'], 10),
			'res.partner': (_get_companies_from_partner, ['image'], 10),
		}),
		'currency_id': fields.many2one('res.currency', 'Currency', required=True,readonly=True, states={'draft':[('readonly',False)]}),
		'currency_ids': fields.one2many('res.currency', 'company_id', 'Currency',readonly=True, states={'draft':[('readonly',False)]}),
		'user_ids': fields.many2many('res.users', 'res_company_users_rel', 'cid', 'user_id', 'Accepted Users',readonly=True, states={'draft':[('readonly',False)]}),
		'account_no':fields.char('Account No.', size=64,readonly=True, states={'draft':[('readonly',False)]}),
		'street': fields.function(_get_address_data, fnct_inv=_set_address_data, size=128, type='char', string="Street", multi='address',readonly=True, states={'draft':[('readonly',False)]}),
		'street2': fields.function(_get_address_data, fnct_inv=_set_address_data, size=128, type='char', string="Street2", multi='address',readonly=True, states={'draft':[('readonly',False)]}),
		'zip': fields.function(_get_address_data, fnct_inv=_set_address_data, size=24, type='char', string="Zip", multi='address',readonly=True, states={'draft':[('readonly',False)]}),
		'city': fields.many2one('res.city','CITY',readonly=True, states={'draft':[('readonly',False)]}),
		'state_id': fields.many2one('res.country.state','State',readonly=True, states={'draft':[('readonly',False)]}),
		'bank_ids': fields.one2many('res.partner.bank','company_id', 'Bank Accounts', help='Bank accounts related to this company',readonly=True, states={'draft':[('readonly',False)]}),
		'country_id': fields.many2one('res.country','Country',readonly=True, states={'draft':[('readonly',False)]}),
		'email': fields.function(_get_address_data, fnct_inv=_set_address_data, size=64, type='char', string="Email", multi='address',readonly=True, states={'draft':[('readonly',False)]}),
		'phone': fields.function(_get_address_data, fnct_inv=_set_address_data, size=64, type='char', string="Phone", multi='address',readonly=True, states={'draft':[('readonly',False)]}),
		'fax': fields.function(_get_address_data, fnct_inv=_set_address_data, size=64, type='char', string="Fax", multi='address',readonly=True, states={'draft':[('readonly',False)]}),
		'website': fields.related('partner_id', 'website', string="Website", type="char", size=64,readonly=True, states={'draft':[('readonly',False)]}),
		'vat': fields.related('partner_id', 'vat', string="Tax ID", type="char", size=32,readonly=True, states={'draft':[('readonly',False)]}),
		'company_registry': fields.char('Company Registry', size=64,readonly=True, states={'draft':[('readonly',False)]}),
		'paper_format': fields.selection([('a4', 'A4'), ('us_letter', 'US Letter')], "Paper Format", required=True,readonly=True, states={'draft':[('readonly',False)]}),
		
		### Code Added by Sangeetha ###
		
		'code': fields.char('Code', size=4, required=True, store=True,readonly=True, states={'draft':[('readonly',False)]}),
		'tin_no': fields.char('TIN NO', size=128,readonly=True, states={'draft':[('readonly',False)]}),
		'vat_no': fields.char('VAT NO', size=128,readonly=True, states={'draft':[('readonly',False)]}),
		'cst_no': fields.char('CST NO', size=128,readonly=True, states={'draft':[('readonly',False)]}),
		'cin_no': fields.char('CIN NO', size=128,readonly=True, states={'draft':[('readonly',False)]}),
		'active':fields.boolean('Active'),
		'creation_date':fields.datetime('Creation Date',readonly=True),
		'same_as_del_add':fields.boolean('Same',readonly=True, states={'draft':[('readonly',False)]}),
		'bill_street': fields.char(size=128, string="Street",readonly=True, states={'draft':[('readonly',False)]}),
		'bill_street2': fields.char(size=128, string="Street2",readonly=True, states={'draft':[('readonly',False)]}),
		'bill_zip': fields.char(size=24, string="ZIP",readonly=True, states={'draft':[('readonly',False)]}),
		'bill_city': fields.many2one('res.city','CITY',readonly=True, states={'draft':[('readonly',False)]}),
		'bill_state_id': fields.many2one('res.country.state','State',readonly=True, states={'draft':[('readonly',False)]}),
		'bill_country_id': fields.many2one('res.country','Country',readonly=True, states={'draft':[('readonly',False)]}),
		'bill_phone': fields.char(size=64, type='char', string="Phone",readonly=True, states={'draft':[('readonly',False)]}),
		'bill_fax': fields.char(size=64, type='char', string="Fax",readonly=True, states={'draft':[('readonly',False)]}),
		'bill_email': fields.char(size=64, type='char', string="Email",readonly=True, states={'draft':[('readonly',False)]}),
		'bill_website': fields.related('partner_id', 'website', string="Website", type="char", size=64,readonly=True, states={'draft':[('readonly',False)]}),
		'state': fields.selection([('draft','Draft'),('waiting', 'WFA'), ('approved', 'Approved'),('reject','Rejected'),('cancel','Canceled')], "Status", readonly=True),
		'division': fields.char('Division', size=250,readonly=True, states={'draft':[('readonly',False)]}),
		#~ #notes
		'notes': fields.text('Notes'),	
		'remark': fields.text('Approve/Reject',readonly=False),
		'modify': fields.function(_get_modify, string='Modify', method=True, type='char', size=3),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'updated_date': fields.datetime('Last Update Date',readonly=True),
		'updated_by': fields.many2one('res.users','Last Updated By',readonly=True),		
		'cancel_remark': fields.text('Cancel Remarks'),			
				
	}
	_sql_constraints = [
		('name_uniq', 'unique (name)', 'The Name must be unique.Please enter valid Name in Name field!'),
		('code_uniq', 'unique (code)', 'The Code must be unique.Please enter valid Code in Code field!'),
	]
	
		
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
		b = datetime.now()		
		d_time = b.strftime('%m/%d/%Y %H:%M:%S')				
		self.write(cr, uid, ids, {'state': 'waiting','conf_user_id': uid, 'confirm_date': d_time})
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
		if rec.remark:
			self.write(cr, uid, ids, {'state': 'reject','rej_user_id': uid, 'reject_date': d_time})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
		return True

	#email validation
	def  _validate_email(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])	
		if rec.email==False:
			return True
		else:
			if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", rec.email) != None:
				return True
			else:
				raise osv.except_osv('Invalid Email', 'Please enter a valid email address')		
				
	#email validation
	def  _validate_bill_email(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])	
		if rec.bill_email==False:
			return True
		else:
			if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", rec.bill_email) != None:
				return True
			else:
				raise osv.except_osv('Invalid Email', 'Please enter a valid email address')		
	
	#validate mobile number

	def _validate_phone(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.phone:
			if len(str(rec.phone)) in (10,11,12) and rec.phone.isdigit() == True:
				return True
			else:
				return False
		return True	
		
	#validate mobile number

	def _validate_bill_phone(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.bill_phone:
			if len(str(rec.bill_phone)) in (10,11,12) and rec.bill_phone.isdigit() == True:
				return True
			else:
				return False
		return True
		
	#check website		
		
	def _check_website(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.website != False:
			if re.match('www.(?:www)?(?:[\w-]{2,255}(?:\.\w{2,6}){1,2})(?:/[\w&%?#-]{1,300})?',rec.website):
				return True
			else:
				return False
		return True
		
	#check zip
	def _check_zip(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.zip:
			if len(str(rec.zip)) in (5,6,7,8) and rec.zip.isdigit() == True:
				return True
		else:
			return True
		return False
		
	#check tin		
	def _check_tin(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.tin_no:
			if len(str(rec.tin_no)) == 11 and rec.tin_no.isdigit() == True:
				return True
		else:
			return True
		return False
		
#check CST		
	def _check_cst(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.cst_no:
			if len(str(rec.cst_no)) == 11 and rec.cst_no.isdigit() == True:
				return True
		else:
			return True
		return False
		
	#check Vat		
	def _check_vat(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.vat_no:
			if len(str(rec.vat_no)) == 15:
				return True
		else:
			return True
		return False		
				
	#approve date and user	
	def approve_company(self, cr, uid, ids, context=None):
		b = datetime.now()		
		d_time = b.strftime('%m/%d/%Y %H:%M:%S')			
		return self.write(cr, uid, ids, {'state':'approved','app_user_id': uid, 'approve_date': d_time})
		
	#edited date and user	

	def edit_company(self, cr, uid, ids, context=None):
		b = datetime.now()		
		d_time = b.strftime('%m/%d/%Y %H:%M:%S')			
		return self.write(cr, uid, ids, {'state':'waiting','rej_user_id': uid, 'reject_date': d_time})
		
	def onchange_billing_address(self, cr, uid, ids, same_as_del_add, street,street2,city,state_id,country_id,zip,phone,fax,email,context=None):
		value = {'bill_street':'','bill_street2':'','bill_zip':'',
						'bill_city':'','bill_state_id':'','bill_country_id':''}
		if same_as_del_add == True:
			value = {

					'bill_street':street,
					'bill_street2':street2,
					'bill_city':city,
					'bill_state_id':state_id,
					'bill_country_id':country_id,
					'bill_zip':zip,
					'bill_phone':phone,
					'bill_fax':fax,
					'bill_email':email
					
					}
		return {'value': value}
	
	def onchange_footer(self, cr, uid, ids, custom_footer, phone, fax, email, website, vat, company_registry, bank_ids, context=None):
		if custom_footer:
			return {}

		# first line (notice that missing elements are filtered out before the join)
		res = ' | '.join(filter(bool, [
			phone			and '%s: %s' % (_('Phone'), phone),
			fax			  and '%s: %s' % (_('Fax'), fax),
			email			and '%s: %s' % (_('Email'), email),
			website		  and '%s: %s' % (_('Website'), website),
			vat			  and '%s: %s' % (_('TIN'), vat),
			company_registry and '%s: %s' % (_('Reg'), company_registry),
		]))
		# second line: bank accounts
		res_partner_bank = self.pool.get('res.partner.bank')
		account_data = self.resolve_2many_commands(cr, uid, 'bank_ids', bank_ids, context=context)
		account_names = res_partner_bank._prepare_name_get(cr, uid, account_data, context=context)
		if account_names:
			title = _('Bank Accounts') if len(account_names) > 1 else _('Bank Account')
			res += '\n%s: %s' % (title, ', '.join(name for id, name in account_names))

		return {'value': {'rml_footer': res, 'rml_footer_readonly': res}}

	def on_change_country(self, cr, uid, ids, country_id, context=None):
		currency_id = self._get_euro(cr, uid, context=context)
		if country_id:
			currency_id = self.pool.get('res.country').browse(cr, uid, country_id, context=context).currency_id.id
		return {'value': {'currency_id': currency_id}}

	def _search(self, cr, uid, args, offset=0, limit=None, order=None,
			context=None, count=False, access_rights_uid=None):
		if context is None:
			context = {}
		if context.get('user_preference'):
			# We browse as superuser. Otherwise, the user would be able to
			# select only the currently visible companies (according to rules,
			# which are probably to allow to see the child companies) even if
			# she belongs to some other companies.
			user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
			cmp_ids = list(set([user.company_id.id] + [cmp.id for cmp in user.company_ids]))
			return cmp_ids
		return super(res_company, self)._search(cr, uid, args, offset=offset, limit=limit, order=order,
			context=context, count=count, access_rights_uid=access_rights_uid)

	def _company_default_get(self, cr, uid, object=False, field=False, context=None):
		"""
		Check if the object for this company have a default value
		"""
		if not context:
			context = {}
		proxy = self.pool.get('multi_company.default')
		args = [
			('object_id.model', '=', object),
			('field_id', '=', field),
		]

		ids = proxy.search(cr, uid, args, context=context)
		user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
		for rule in proxy.browse(cr, uid, ids, context):
			if eval(rule.expression, {'context': context, 'user': user}):
				return rule.company_dest_id.id
		return user.company_id.id

	@tools.ormcache()
	def _get_company_children(self, cr, uid=None, company=None):
		if not company:
			return []
		ids =  self.search(cr, uid, [('parent_id','child_of',[company])])
		return ids

	def _get_partner_hierarchy(self, cr, uid, company_id, context=None):
		if company_id:
			parent_id = self.browse(cr, uid, company_id)['parent_id']
			if parent_id:
				return self._get_partner_hierarchy(cr, uid, parent_id.id, context)
			else:
				return self._get_partner_descendance(cr, uid, company_id, [], context)
		return []

	def _get_partner_descendance(self, cr, uid, company_id, descendance, context=None):
		descendance.append(self.browse(cr, uid, company_id).partner_id.id)
		for child_id in self._get_company_children(cr, uid, company_id):
			if child_id != company_id:
				descendance = self._get_partner_descendance(cr, uid, child_id, descendance)
		return descendance

	#
	# This function restart the cache on the _get_company_children method
	#
	def cache_restart(self, cr):
		self._get_company_children.clear_cache(self)

	def create(self, cr, uid, vals, context=None):
		if not vals.get('name', False) or vals.get('partner_id', False):
			self.cache_restart(cr)
			return super(res_company, self).create(cr, uid, vals, context=context)
		obj_partner = self.pool.get('res.partner')
		partner_id = obj_partner.create(cr, uid, {'name': vals['name'], 'is_company':True, 'image': vals.get('logo', False)}, context=context)
		vals.update({'partner_id': partner_id})
		self.cache_restart(cr)
		company_id = super(res_company, self).create(cr, uid, vals, context=context)
		obj_partner.write(cr, uid, [partner_id], {'company_id': company_id}, context=context)
		return company_id

	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_by':uid})
		return super(res_company, self).write(cr, uid, ids, vals, context)

	def _get_euro(self, cr, uid, context=None):
		rate_obj = self.pool.get('res.currency.rate')
		rate_id = rate_obj.search(cr, uid, [('rate', '=', 1)], context=context)
		return rate_id and rate_obj.browse(cr, uid, rate_id[0], context=context).currency_id.id or False

	def _get_logo(self, cr, uid, ids):
		return open(os.path.join( tools.config['root_path'], 'addons', 'base', 'res', 'res_company_logo.png'), 'rb') .read().encode('base64')

	_header = """
<header>
<pageTemplate>
	<frame id="first" x1="28.0" y1="28.0" width="%s" height="%s"/>
	<stylesheet>
	   <!-- Set here the default font to use for all <para> tags -->
	   <paraStyle name='Normal' fontName="DejaVu Sans"/>
	</stylesheet>
	<pageGraphics>
		<fill color="black"/>
		<stroke color="black"/>
		<setFont name="DejaVu Sans" size="8"/>
		<drawString x="%s" y="%s"> [[ formatLang(time.strftime("%%Y-%%m-%%d"), date=True) ]]  [[ time.strftime("%%H:%%M") ]]</drawString>
		<setFont name="DejaVu Sans Bold" size="10"/>
		<drawCentredString x="%s" y="%s">[[ company.partner_id.name ]]</drawCentredString>
		<stroke color="#000000"/>
		<lines>%s</lines>
		<!-- Set here the default font to use for all <drawString> tags -->
		<!-- don't forget to change the 2 other occurence of <setFont> above if needed --> 
		<setFont name="DejaVu Sans" size="8"/>
	</pageGraphics>
</pageTemplate>
</header>"""

	_header2 = _header % (539, 772, "1.0cm", "28.3cm", "11.1cm", "28.3cm", "1.0cm 28.1cm 20.1cm 28.1cm")

	_header3 = _header % (786, 525, 25, 555, 440, 555, "25 550 818 550")

	def _get_header(self,cr,uid,ids):
		try :
			header_file = tools.file_open(os.path.join('base', 'report', 'corporate_rml_header.rml'))
			try:
				return header_file.read()
			finally:
				header_file.close()
		except:
			return self._header_a4

	_header_main = """
<header>
	<pageTemplate>
		<frame id="first" x1="1.3cm" y1="3.0cm" height="%s" width="19.0cm"/>
		 <stylesheet>
			<!-- Set here the default font to use for all <para> tags -->
			<paraStyle name='Normal' fontName="DejaVu Sans"/>
			<paraStyle name="main_footer" fontSize="8.0" alignment="CENTER"/>
			<paraStyle name="main_header" fontSize="8.0" leading="10" alignment="LEFT" spaceBefore="0.0" spaceAfter="0.0"/>
		 </stylesheet>
		<pageGraphics>
			<!-- Set here the default font to use for all <drawString> tags -->
			<setFont name="DejaVu Sans" size="8"/>
			<!-- You Logo - Change X,Y,Width and Height -->
			<image x="1.3cm" y="%s" height="40.0" >[[ company.logo or removeParentNode('image') ]]</image>
			<fill color="black"/>
			<stroke color="black"/>

			<!-- page header -->
			<lines>1.3cm %s 20cm %s</lines>
			<drawRightString x="20cm" y="%s">[[ company.rml_header1 ]]</drawRightString>
			<drawString x="1.3cm" y="%s">[[ company.partner_id.name ]]</drawString>
			<place x="1.3cm" y="%s" height="1.8cm" width="15.0cm">
				<para style="main_header">[[ display_address(company.partner_id) or  '' ]]</para>
			</place>
			<drawString x="1.3cm" y="%s">Phone:</drawString>
			<drawRightString x="7cm" y="%s">[[ company.partner_id.phone or '' ]]</drawRightString>
			<drawString x="1.3cm" y="%s">Mail:</drawString>
			<drawRightString x="7cm" y="%s">[[ company.partner_id.email or '' ]]</drawRightString>
			<lines>1.3cm %s 7cm %s</lines>

			<!-- left margin -->
			<rotate degrees="90"/>
			<fill color="grey"/>
			<drawString x="2.65cm" y="-0.4cm">generated by OpenERP.com</drawString>
			<fill color="black"/>
			<rotate degrees="-90"/>

			<!--page bottom-->
			<lines>1.2cm 2.65cm 19.9cm 2.65cm</lines>
			<place x="1.3cm" y="0cm" height="2.55cm" width="19.0cm">
				<para style="main_footer">[[ company.rml_footer ]]</para>
				<para style="main_footer">Contact : [[ user.name ]] - Page: <pageNumber/></para>
			</place>
		</pageGraphics>
	</pageTemplate>
</header>"""

	_header_a4 = _header_main % ('21.7cm', '27.7cm', '27.7cm', '27.7cm', '27.8cm', '27.3cm', '25.3cm', '25.0cm', '25.0cm', '24.6cm', '24.6cm', '24.5cm', '24.5cm')
	_header_letter = _header_main % ('20cm', '26.0cm', '26.0cm', '26.0cm', '26.1cm', '25.6cm', '23.6cm', '23.3cm', '23.3cm', '22.9cm', '22.9cm', '22.8cm', '22.8cm')

	def onchange_paper_format(self, cr, uid, ids, paper_format, context=None):
		if paper_format == 'us_letter':
			return {'value': {'rml_header': self._header_letter}}
		return {'value': {'rml_header': self._header_a4}}

	_defaults = {
		'currency_id': _get_euro,
		'paper_format': 'a4',
		'rml_header':_get_header,
		'rml_header2': _header2,
		'rml_header3': _header3,
		'logo':_get_logo,
		'modify': 'no',
		'active' : 'True',
		'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'state': 'draft',
		
	}

	_constraints = [
		(osv.osv._check_recursion, 'Error! You can not create recursive companies.', ['parent_id']),
		(_validate_email, 'Enter a correct Email in the Email Field!!', ['email']),
		(_validate_bill_email, 'Enter a correct Email in the Bill Email Field!!', ['bill_email']),
		(_check_website,'Enter a orrect  Website in Website Field!',['Website']),
		#~ (_validate_phone, 'Enter a correct Phone Number in the Phone Field!!', ['phone']),
		(_validate_bill_phone, 'Enter a correct Phone Number in the Bill Phone Field!!', ['bill_phone']),
		#~ (_check_zip,'Enter a correct ZIP code in ZIP field!',['ZIP']),
		(_check_tin,'Enter a Correct TIN number in TIN field!',['TIN']),
		(_check_cst,'Enter a correct CST number in CST field!',['CST']),
		(_check_vat,'Enter a Correct VAT number in VAT field!',['VAT']),
	]

res_company()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:





