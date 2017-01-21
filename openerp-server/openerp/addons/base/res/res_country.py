from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.osv import fields, osv
import time
from datetime import date
from datetime import datetime
a = datetime.now()
dt_time = a.strftime('%m/%d/%Y %H:%M:%S')

def location_name_search(self, cr, user, name='', args=None, operator='ilike',
						 context=None, limit=100):
	if not args:
		args = []

	ids = []
	if len(name) == 2:
		ids = self.search(cr, user, [('code', 'ilike', name)] + args,
						  limit=limit, context=context)

	search_domain = [('name', operator, name)]
	if ids: search_domain.append(('id', 'not in', ids))
	ids.extend(self.search(cr, user, search_domain + args,
						   limit=limit, context=context))

	locations = self.name_get(cr, user, ids, context)
	return sorted(locations, key=lambda (id, name): ids.index(id))

class Country(osv.osv):
	_name = 'res.country'
	_description = 'Country'
		
		#modify function
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
					as sam  """ %('res_country'))
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
		'name': fields.char('Name', size=64,
			help='The full name of the country.', required=True, translate=True,readonly=True, states={'draft':[('readonly',False)]}),
		'code': fields.char('Code', size=4,required=True,
			help='The ISO country code in two chars.\n'
			'You can use this field for quick search.',readonly=True, states={'draft':[('readonly',False)]}),
		'address_format': fields.text('Address Format', help="""You can state here the usual format to use for the \
addresses belonging to this country.\n\nYou can use the python-style string patern with all the field of the address \
(for example, use '%(street)s' to display the field 'street') plus
			\n%(state_name)s: the name of the state
			\n%(state_code)s: the code of the state
			\n%(country_name)s: the name of the country
			\n%(country_code)s: the code of the country"""),
		'currency_id': fields.many2one('res.currency', 'Currency',readonly=True, states={'draft':[('readonly',False)]}),
		'active': fields.boolean('Active'),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'user_id': fields.many2one('res.users', 'Created By', readonly=True),
		'creation_date':fields.datetime('Creation Date',readonly=True),
		'approve_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Apprved By', readonly=True),
		'confirm_date': fields.datetime('Confirm Date', readonly=True),
		'conf_user_id': fields.many2one('res.users', 'Confirmed By', readonly=True),
		'reject_date': fields.datetime('Reject Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'state': fields.selection([('draft','Draft'),('confirmed','WFA'),('approved','Approved'),('reject','Rejected'),('cancel','Cancelled')],'Status', readonly=True),
		#notes
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
		('name_uniq', 'unique (name)',
			'The name of the country must be unique !'),
		('code_uniq', 'unique (code)',
			'The code of the country must be unique !')
	]
	_defaults = {
	
		'address_format': "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s",
		'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'res.country', context=c),
		'active': True,
		'state': 'draft',
		'user_id': lambda obj, cr, uid, context: uid,
		'modify': 'no',
		'name': 'India',
		
	}
	_order='name'

	name_search = location_name_search
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
		
	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_by':uid})
		return super(Country, self).write(cr, uid, ids, vals, context)
			
	def entry_confirm(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'confirmed','conf_user_id': uid, 'confirm_date': dt_time})
		return True

	def entry_approve(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'approved','app_user_id': uid, 'approve_date': dt_time})
		return True

	def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.remark:
			self.write(cr, uid, ids, {'state': 'reject','rej_user_id': uid, 'reject_date': dt_time})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
		return True
	

	def create(self, cursor, user, vals, context=None):
		if vals.get('code'):
			vals['code'] = vals['code'].upper()
		return super(Country, self).create(cursor, user, vals,
				context=context)
				
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


class CountryState(osv.osv):
	_description="Country state"
	_name = 'res.country.state'
	

		
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
					as sam  """ %('res_country_state'))
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
		
		'country_id': fields.many2one('res.country', 'Country',
			required=True,readonly=True, states={'draft':[('readonly',False)]}),
		'name': fields.char('Name', size=64, required=True, 
							help='Administrative divisions of a country. E.g. Fed. State, Departement, Canton',readonly=True, states={'draft':[('readonly',False)]}),
		'code': fields.char('Code', size=4,readonly=True, states={'draft':[('readonly',False)]},
			help='The state code in max. three chars.', required=True),
		 'creation_date':fields.datetime('Creation Date',readonly=True),
		'active': fields.boolean('Active'),
		'notes': fields.text('Notes'),
		'remark': fields.text('Approve/Reject',readonly=False),
		'cancel_remark': fields.text('Cancel Remarks'),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'user_id': fields.many2one('res.users', 'Created By', readonly=True),
		'approve_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Approved By', readonly=True),
		'confirm_date': fields.datetime('Confirm Date', readonly=True),
		'conf_user_id': fields.many2one('res.users', 'Confirmed By', readonly=True),
		'reject_date': fields.datetime('Reject Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'state': fields.selection([('draft','Draft'),('confirmed','WFA'),('approved','Approved'),('reject','Rejected'),('cancel','Cancelled')],'Status', readonly=True),
		'modify': fields.function(_get_modify, string='Modify', method=True, type='char', size=3),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'updated_date': fields.datetime('Last Update Date',readonly=True),
		'updated_by': fields.many2one('res.users','Last Updated By',readonly=True),		
		
	}
	
	_sql_constraints = [
	
		('name_uniq', 'unique (name)',
			'The name of the state must be unique !'),
		('code_uniq', 'unique (code)',
			'The code of the state must be unique !'),
		
	]	
	_order = 'code'
	
	_defaults = {
	   
		'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'active':True,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'res.country.state', context=c),
		'state': 'draft',
		'user_id': lambda obj, cr, uid, context: uid,
		'modify': 'no',
		
	}
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
		
	name_search = location_name_search
	
	def entry_confirm(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'confirmed','conf_user_id': uid, 'confirm_date': dt_time})
		return True

	def entry_approve(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'approved','app_user_id': uid, 'approve_date': dt_time})
		return True
	

		
	def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.remark:
			self.write(cr, uid, ids, {'state': 'reject','rej_user_id': uid, 'reject_date': dt_time})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
		return True
	

		
	def write(self, cr, uid, ids, vals, context=None):	  
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(CountryState, self).write(cr, uid, ids, vals, context)
		
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
				
class res_city(osv.osv):
	_name = 'res.city'
	_description = 'city'
	
	
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
					as sam  """ %('res_city'))
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
	
		'country_id': fields.many2one('res.country','Country',required=True,readonly=True, states={'draft':[('readonly',False)]}),
		'state_id': fields.many2one('res.country.state','State',readonly=True, states={'draft':[('readonly',False)]}),
		'name':fields.char('Name',size=125, required=True,readonly=True, states={'draft':[('readonly',False)]}),
		'creation_date':fields.datetime('Creation Date',readonly=True),
		'active': fields.boolean('Active'),
		'notes': fields.text('Notes'),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'user_id': fields.many2one('res.users', 'Created By', readonly=True),
		'approve_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Approved By', readonly=True),
		'confirm_date': fields.datetime('Confirm Date', readonly=True),
		'conf_user_id': fields.many2one('res.users', 'Confirmed By', readonly=True),
		'reject_date': fields.datetime('Reject Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'state': fields.selection([('draft','Draft'),('confirmed','WFA'),('approved','Approved'),('reject','Rejected'),('cancel','Cancelled')],'Status', readonly=True),
		'remark': fields.text('Approve/Reject',readonly=False),
		'modify': fields.function(_get_modify, string='Modify', method=True, type='char', size=3),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'updated_date': fields.datetime('Last Update Date',readonly=True),
		'updated_by': fields.many2one('res.users','Last Updated By',readonly=True),		
		'cancel_remark': fields.text('Cancel Remarks'),			
	}
	
	_sql_constraints = [
	
		('name_uniq', 'unique (name)',
			'The name of the city must be unique !'),
		
	]
	
	_defaults = {
	   
		'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'active':True,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'res.city', context=c),
		'state': 'draft',
		'user_id': lambda obj, cr, uid, context: uid,
		'modify': 'no',
		
	}
	
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
	
	def create(self, cursor, user, vals, context=None):
		if vals.get('name'):
			vals['name'] = vals['name'].capitalize()
	   
		return super(res_city, self).create(cursor, user, vals,
				context=context)

	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_by':uid})
		return super(res_city, self).write(cr, uid, ids, vals, context)

		return super(res_city, self).write(cursor, user, ids, vals,
				context=context)
				
	def entry_confirm(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'confirmed','conf_user_id': uid, 'confirm_date': dt_time})
		return True

	def entry_approve(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'approved','app_user_id': uid, 'approve_date': dt_time})
		return True
	

	def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.remark:
			self.write(cr, uid, ids, {'state': 'reject','rej_user_id': uid, 'reject_date': dt_time})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
		return True
	

	def write(self, cr, uid, ids, vals, context=None):	  
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(res_city, self).write(cr, uid, ids, vals, context)
		
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
				
				
res_city()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

