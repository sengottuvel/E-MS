import math
import re
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
import openerp.addons.decimal_precision as dp
import netsvc
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import datetime
import calendar

class kg_mail_settings(osv.osv):
	_name = "kg.mail.settings"
	_description = "Mail General Settings"

	_columns = {
		'creation_time':fields.date('Creation Date',readonly=True),
		'created_by':fields.many2one('res.users', 'Created By',readonly=True),
		'active':fields.boolean('Active',readonly=False),
		'doc_name': fields.many2one('ir.model','Document Name',readonly=True, states={'draft':[('readonly',False)]}),
		'name':fields.char('From Email-ID',required = True,readonly=True, states={'draft':[('readonly',False)]}),
		'line_ids':fields.one2many('ch.mail.settings.line','header_id',readonly=False),
		'state': fields.selection([('draft', 'To Submit'),('confirm', 'To Approve'),('validate', 'Approved')],
						'Status', readonly=True, track_visibility='onchange'),
		'expiry_date':fields.datetime('Expiry Date'),
		'sch_name': fields.char('Scheduler Name', size=128, readonly=True, states={'draft':[('readonly',False)]}),
		'subject': fields.char('Subject', size=128, readonly=True, states={'draft':[('readonly',False)]}),
		'sch_interval': fields.selection([('daily','Daily'),('15_days','15 Days Once'),('monthly','Monthly'),('yearly','Yearly')],'Interval',readonly=True, states={'draft':[('readonly',False)]}),
		'sch_type': fields.selection([('transaction','Transaction Mail'),('scheduler','Scheduler Mail')],'Mail Type', required=True, readonly=True, states={'draft':[('readonly',False)]}),
		
	}
	
	_defaults = {
		'creation_time': lambda * a: time.strftime('%Y-%m-%d'),
		'state':'draft',
		'active':True,
		'created_by': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
		'name':'erpmail@kgcloud.org',
	}
	 
	def approve_entry(self, cr, uid, ids,context=None):		
		self.write(cr,uid,ids,{'state':'validate'})
		return True
		
	def confirm_entry(self, cr, uid, ids, context=None):
		entry = self.browse(cr,uid,ids[0])
		entry_obj = self.pool.get('kg.mail.settings')
		doc_name = entry.doc_name.id
		entry_id=entry.id
		"""	
		duplicate_ids= entry_obj.search(cr, uid, [('id' ,'!=', entry_id),('doc_name','=',doc_name)])
		if duplicate_ids:
			dup_rec = entry_obj.browse(cr,uid,duplicate_ids[0])
			today_date = datetime.datetime.today()
			dup_rec.write({'active': False})
			dup_rec.write({'expiry_date':today_date})"""
		self.write(cr,uid,ids,{'state':'confirm'})	
		return True
					
	def draft_entry(self, cr, uid, ids, context=None):
		self.write(cr, uid, ids, {'state': 'draft'})
		return True
	
	def _check_entry_line(self, cr, uid, ids, context=None):
		entry = self.browse(cr,uid,ids[0])
		if not entry.line_ids :
			return False
		else:
			return True


	def unlink(self, cr, uid, ids, context=None):
		unlink_ids = []				
		grn_rec = self.browse(cr, uid, ids[0])
		if grn_rec.state != 'draft':
			raise osv.except_osv(_('Invalid action !'), _('System not allow to delete !!'))
		else:
			unlink_ids.append(grn_rec.id)
			
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)

	def _to_mail_address(self,cr,uid,ids,context =None):
		grn_rec = self.browse(cr, uid, ids[0])
		to_add = []
		for line in grn_rec.line_ids:
			if line.to_address:
				to_add.append(line.mail_id)
		if not to_add:
			raise osv.except_osv(_('Warning!'), _('Atleast One TO mail ID should be given!!'))
		return True
			
	_constraints = [        
              
        (_to_mail_address, 'Atleast One TO mail ID should be given!!',['To Address']),
        
       ]
       
	
kg_mail_settings()

class ch_mail_settings_line(osv.osv):
	_name = "ch.mail.settings.line"
	_columns = {
			
			'header_id':fields.many2one('kg.mail.settings','Line Entry'),
			'mail_id':fields.char('Email ID'),
			'to_address':fields.boolean('TO'),
			'cc_address':fields.boolean('CC'),
			'status':fields.boolean('Status',invisible=True)
			
			}
ch_mail_settings_line()
