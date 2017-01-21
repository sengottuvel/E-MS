from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import re
from operator import itemgetter
from itertools import groupby
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)
a = datetime.now()
dt_time = a.strftime('%m/%d/%Y %H:%M:%S')

class kg_cash_voucher(osv.osv):

	_name = "kg.cash.voucher"
	_description = "Cash Voucher"
	_columns = {
		
		'name': fields.char('Voucher No', size=128,readonly=True),
		'creation_date':fields.datetime('Creation Date',readonly=True),
		'date': fields.date('Date',readonly=True, states={'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'narration': fields.text('Narration',readonly=True, states={'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'paid_to': fields.char('Paid To', size=128,readonly=True,required=True, states={'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'amount': fields.float('Amount',readonly=True,required=True, states={'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'created_by': fields.many2one('res.users','Created By',readonly=True),
		'active':fields.boolean('Active',readonly=True),
		'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Waiting for Approval'), ('approved', 'Approved'), ('cancel', 'Cancelled')], 'Status',readonly=True),
		'partner_id':fields.many2one('res.partner', 'Supplier', required=False,invisible=True,readonly=True, 
                    states={'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'dummy_field': fields.char('Dummy_field', size=128,readonly=True, states={'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'dummy_int': fields.integer('Dummy Int', size=128,readonly=True, states={'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
		'payment_type': fields.selection([('cash', 'Cash'), ('credit', 'Credit')], 'Payment Type'),
		'confirmed_date': fields.datetime('Approved Date', readonly=True),
		'conf_user_id': fields.many2one('res.users', 'Apprved By', readonly=True),
		'approved_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Apprved By', readonly=True),
		
	}
	
	
	
	_defaults = {
	
	'active':True,
	'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
	'date' : fields.date.context_today,
	'state':'draft',
	'payment_type':'cash',
	'name': '',
	'created_by': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
	
	}
	
	def email_ids(self,cr,uid,ids,context = None):
		email_from = []
		email_to = []
		email_cc = []
		val = {'email_from':'','email_to':'','email_cc':''}
		ir_model = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		mail_form_ids = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		for ids in mail_form_ids:
			mail_form_rec = self.pool.get('kg.mail.settings').browse(cr,uid,ids)
			if mail_form_rec.doc_name.model == 'kg.cash.voucher':
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
	
	def confirm_entry(self, cr, uid, ids, context=None):	
		entry = self.browse(cr,uid,ids[0])
		confirmed_date = entry.confirmed_date
		voucher_name = ''
		if not entry.name:
			voucher_no = self.pool.get('ir.sequence').get(cr, uid, 'kg.cash.voucher') or ''
			voucher_no_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.cash.voucher')])
			rec = self.pool.get('ir.sequence').browse(cr,uid,voucher_no_id[0])
			cr.execute("""select generatesequenceno(%s,'%s','%s') """%(voucher_no_id[0],rec.code,entry.date))
			voucher_name = cr.fetchone();
			self.write(cr,uid,ids[0],{'state':'confirmed','name':str(voucher_name[0]),'conf_user_id':uid,'confirmed_date':dt_time})
		if entry.amount <= 0.00:
			raise osv.except_osv(_('Warning!'), _('Amount must be greater than Zero'))
		
		cr.execute("""select all_transaction_mails('Expense Entry Approval',%s)"""%(ids[0]))
		data = cr.fetchall();
		vals = self.email_ids(cr,uid,ids,context = context)
		if (not vals['email_to']) and (not vals['email_cc']):
			pass
		else:
			ir_mail_server = self.pool.get('ir.mail_server')
			msg = ir_mail_server.build_email(
					email_from = vals['email_from'][0],
					email_to = vals['email_to'],
					subject = "	Cash Expense- Waiting For Approval",
					body = data[0][0],
					email_cc = vals['email_cc'],
					object_id = ids[0] and ('%s-%s' % (ids[0], 'kg.cash.voucher')),
					subtype = 'html',
					subtype_alternative = 'plain')
			res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=1, context=context)
		return True
		
	def approve_entry(self, cr, uid, ids, context=None):	
		self.write(cr,uid,ids[0],{'state':'approved' ,'app_user_id':uid,
								  'approved_date':dt_time,})
		cr.execute("""select all_transaction_mails('Expense Entry Approval',%s)"""%(ids[0]))
		data = cr.fetchall();
		vals = self.email_ids(cr,uid,ids,context = context)
		if (not vals['email_to']) and (not vals['email_cc']):
			pass
		else:
			ir_mail_server = self.pool.get('ir.mail_server')
			msg = ir_mail_server.build_email(
					email_from = vals['email_from'][0],
					email_to = vals['email_to'],
					subject = "	Cash Expense- Approved",
					body = data[0][0],
					email_cc = vals['email_cc'],
					object_id = ids[0] and ('%s-%s' % (ids[0], 'kg.cash.voucher')),
					subtype = 'html',
					subtype_alternative = 'plain')
			res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=1, context=context)
		return True
	
	
kg_cash_voucher()
