from functools import partial
import logging
from lxml import etree
from lxml.builder import E
import time
import openerp
from openerp import SUPERUSER_ID
from openerp import pooler, tools
import openerp.exceptions
from openerp.osv import fields,osv
from openerp.osv.orm import browse_record
from openerp.tools.translate import _
from datetime import date
from datetime import datetime
import re
today = datetime.now()
a = datetime.now()
dt_time = a.strftime('%m/%d/%Y %H:%M:%S')


class kg_users(osv.osv):

	_name = "res.users"
	_inherit = "res.users"
	_description = "User Managment"
	
	_columns = {
	
	'dep_name' : fields.many2one('kg.depmaster', 'Department', required=True),
	'special_approval': fields.boolean('Special Approval'),	
	'company_ref_id': fields.many2many('res.company', 'm2m_emp_user_company', 'user_id','company_id', 'Company Mapping'),
	'crt_date': fields.datetime('Creation Date',readonly=True),
	'user_id': fields.many2one('res.users', 'Created By', readonly=True),
	'update_user_id': fields.many2one('res.users', 'Last Update By', readonly=True),
	'update_date': fields.datetime('Last Update Date', readonly=True),
	'entry_mode': fields.selection([('auto', 'Auto'), ('manual', 'Manual')], 'Entry Mode', readonly=True),
	'copy_menus':fields.boolean('Copy User'),
	'copy_user_id':fields.many2one('res.users','User'),
	'user_menu_access': fields.many2many('ir.ui.menu', 'ir_ui_menu_user_rel', 'user_id', 'menu_id', 'Access Menu', domain = [('name','!=','')]),
	'groups_id': fields.many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', 'Groups'),
	}
	
	_defaults = {
	
	'user_id': lambda obj, cr, uid, context: uid,
	'crt_date':fields.datetime.now,
	'entry_mode': 'manual',
	 }
	
	def copy_menus_user_id(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		cr.execute("""delete from ir_ui_menu_user_rel where user_id=%d"""%ids[0])
		cr.execute("""delete from res_groups_users_rel where uid=%d"""%ids[0])
		cr.execute("""select * from ir_ui_menu_user_rel where user_id=%d"""%rec.copy_user_id.id)
		data = cr.dictfetchall()
		for i in data:cr.execute("""insert into ir_ui_menu_user_rel values(%s,%s)"""%(ids[0],i['menu_id']))
		cr.execute("""select * from res_groups_users_rel where uid=%d"""%rec.copy_user_id.id)
		data1 = cr.dictfetchall()
		for j in data1:cr.execute("""insert into res_groups_users_rel values(%s,%s)"""%(ids[0],j['gid']))
		return True

	def _validate_login(self, cr, uid,ids, context=None):
		print "validation is called"
		rec = self.browse(cr,uid,ids[0])
		for i in range(len(rec.login)):
			if re.match(r'[0-9!#$%^~*{}?+=]+', rec.login[i]) or ' ' in rec.login:
				raise osv.except_osv('Invalid User Name', 'Special characters,Numbers and Spaces are not allowed for Login name')
		return True
		
	def _validate_name(self, cr, uid,ids, context=None):
		print "validation is called"
		rec = self.browse(cr,uid,ids[0])
		for i in range(len(rec.name)):
			if re.match(r'[!#@$%^~*{}?+=]+', rec.name[i]):
				raise osv.except_osv('Invalid Character', 'Special characters and Numbers are not allowed in Name')
		return True
		
	def  _validate_email(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0]) 
		if rec.email==False:
			return True
		else:
			if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", rec.email) != None:
				return True
			else:
				raise osv.except_osv('Invalid Email', 'Please enter a valid email address')  
				
	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(kg_users, self).write(cr, uid, ids, vals, context)
		
	_constraints = [
			(_validate_login, 'invalid Login name  !!', ['login']),
			(_validate_name, 'invalid Name  !!', ['name']),
			(_validate_email, 'invalid Email  !!', ['email']),
	]	
	
kg_users()
