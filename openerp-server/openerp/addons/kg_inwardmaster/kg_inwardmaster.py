from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import re
from operator import itemgetter
from itertools import groupby
from datetime import datetime
a = datetime.now()
dt_time = a.strftime('%m/%d/%Y %H:%M:%S')
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class kg_inwardmaster(osv.osv):
	
		
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
					as sam  """ %('kg_inwardmaster'))
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

	_name = "kg.inwardmaster"
	_description = "Inward Master"
	_columns = {
		
		'name': fields.char('Name', size=128, required=True, select=True,readonly=False,states={'approved':[('readonly',True)]}),
		'code':fields.char('Code',size=4),
		'creation_date':fields.datetime('Created Date',readonly=True),
		'bill': fields.boolean('Bill Indication',readonly=False,states={'approved':[('readonly',True)]}),
		'return': fields.boolean('Return Indication',readonly=False,states={'approved':[('readonly',True)]}),
		'valid': fields.boolean('Valid Indication',readonly=False,states={'approved':[('readonly',True)]}),
		'active': fields.boolean('Active'),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'user_id': fields.many2one('res.users', 'Created By', readonly=True),
		'approve_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Approved By', readonly=True),
		'confirm_date': fields.datetime('Confirmed Date', readonly=True),
		'conf_user_id': fields.many2one('res.users', 'Confirmed By', readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'state': fields.selection([('draft','Draft'),('confirm','WFA'),('approved','Approved'),
				('reject','Rejected'),('cancel','Canceled')],'Status', readonly=True),
		#notes
		'notes': fields.text('Notes'),
		'remark': fields.text('Approve/Reject',readonly=False),
		'modify': fields.function(_get_modify, string='Modify', method=True, type='char', size=3,store=True),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'updated_date': fields.datetime('Last Updated Date',readonly=True),
		'updated_by': fields.many2one('res.users','Last Updated By',readonly=True),		
		'cancel_remark': fields.text('Cancel Remarks'),				
		
	}
	
	_sql_constraints = [
		('name', 'unique(name)', 'Inward Type must be unique!'),
		('code', 'unique(code)', 'Code must be unique!'),
	]
	
	_defaults = {
	
		'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.segment', context=c),
		'active': True,
		'state': 'draft',
		'modify': 'no',
		'user_id': lambda obj, cr, uid, context: uid,
	
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
	
	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_by':uid})
		return super(kg_inwardmaster, self).write(cr, uid, ids, vals, context)
		
	def create(self, cr, uid, vals, context=None): 
		v_name = None 
		if vals.get('name'): 
			v_name = vals['name'].strip() 
			vals['name'] = v_name.capitalize() 
		
			
		result = super(kg_inwardmaster,self).create(cr, uid, vals, context=context) 
		return result
#ENTRY CONFIRM
	def entry_confirm(self,cr,uid,ids,context=None):
		b = datetime.now()		
		d_time = b.strftime('%m/%d/%Y %H:%M:%S')				
		self.write(cr, uid, ids, {'state': 'confirm','conf_user_id': uid, 'confirm_date': d_time})
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
	

	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []		
		for rec in self.browse(cr,uid,ids):	
			if rec.state != 'draft':			
				raise osv.except_osv(_('Warning!'),
						_('You can not delete this entry !!'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		
		
		
	def auto_dep_indent(self, cr, uid, ids=0, context=None):
		product_obj = self.pool.get('product.product')
		product_ids = """ select id from product_product where flag_minqty_rule = 't'  and state = 'approved' """
		cr.execute(product_ids)	
		product_data = cr.dictfetchall()
		for i in list(product_data):
			value = i['id']
			product_id_val = self.pool.get('product.product').browse(cr, uid, value)
			lot_sql = """ select sum(pending_qty) from stock_production_lot where product_id = %d group by product_id """%(value)
			cr.execute(lot_sql)
			lot_data = cr.dictfetchall()
			if lot_data:
				for i in list(lot_data):
					stock_remain = i['sum']
			else:
				stock_remain = 0
			min_sql = """ select minimum_qty from product_product where id = %d """%(value)
			cr.execute(min_sql)
			min_qty_val_data = cr.dictfetchall()
			for i in list(min_qty_val_data):
				min_qty_val = i['minimum_qty']
				min_qty_val = min_qty_val+1
			depindent_pending = """ select sum(pending_qty) from kg_depindent_line where product_id = %d """%(value)
			cr.execute(depindent_pending)
			depindent_pending_qty = cr.dictfetchall()
			if depindent_pending_qty:
				for i in list(depindent_pending_qty):
					depindent_p_qty = i['sum']
					if depindent_p_qty == None:
						depindent_p_qty = 0
			else:
				depindent_p_qty = 0			
			purchase_pending = """ select sum(pending_qty) from purchase_requisition_line where product_id = %d and indent_state = 't' """%(value)
			cr.execute(purchase_pending)
			purchase_pending_qty = cr.dictfetchall()
			if purchase_pending_qty:
				for i in list(purchase_pending_qty):
					purchase_p_qty = i['sum']
					if purchase_p_qty == None:
						purchase_p_qty = 0					
			else:
				purchase_p_qty = 0			
			order_pending = """ select sum(pending_qty) from purchase_order_line where product_id = %d and indent_state = 't' """%(value)
			cr.execute(order_pending)
			order_pending_qty = cr.dictfetchall()
			if order_pending_qty:
				for i in list(order_pending_qty):
					order_p_qty = i['sum']
					if order_p_qty == None:
						order_p_qty = 0						
			else:
				order_p_qty = 0		
			total_indent_pending_qty = int(depindent_p_qty) + int(purchase_p_qty) + int(order_p_qty)
			remain_stock_value = int(stock_remain) + int(total_indent_pending_qty)
			if int(remain_stock_value) < int(min_qty_val):
				reorder_sql = """ select reorder_qty from product_product where id = %d """%(value)
				cr.execute(reorder_sql)
				reorder_qty = cr.dictfetchall()
				for i in list(reorder_qty):
					reorder_qty_val = i['reorder_qty']
					kg_depindent_id=self.pool.get('kg.depindent')
					kg_depindent_line=self.pool.get('kg.depindent.line')
					seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.depindent')])
					seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
					cr.execute("""select generatesequenceno(%s,'%s',now()::date) """%(seq_id[0],seq_rec.code))
					seq_name = cr.fetchone();
					indent_ids = kg_depindent_id.create(cr,uid,
					{
					'dep_name':72,
					'indent_type':'production',
					'state':'approved',
					'name': seq_name[0],				
					'dest_location_id': 277,					
					'src_location_id': 47					
					})
					kg_depindent_line.create(cr,uid,
					{
					'indent_id':indent_ids,
					'product_id':value,
					'uom':product_id_val.uom_po_id.id,
					'po_uom':product_id_val.uom_po_id.id,
					'qty':reorder_qty_val,
					'issue_pending_qty':reorder_qty_val,
					'pending_qty':reorder_qty_val,
					'po_qty':reorder_qty_val,
					})
					
				
		return
		
		
	def user_entry_count(self, cr, uid, ids=0, context=None):
		cr.execute("""SELECT all_daily_scheduler_mails('Daily Userwise Summary List')""") 
		data = cr.fetchall(); 
		if data[0][0] is None: 
			return False		 
		if data[0][0] is not None:	 
			maildet = (str(data[0])).rsplit('~'); 
			cont = data[0][0].partition('UNWANTED.')		 
			email_from = 'erpmail@kgcloud.org' 
			email_to = ["dineshkumar.k@kggroup.com"] 
			email_cc = ["dineshkumar.k@kggroup.com"] 
			ir_mail_server = self.pool.get('ir.mail_server')	 
			ir_mail_server = self.pool.get('ir.mail_server')	 
			msg = ir_mail_server.build_email( 
				email_from = email_from, 
				email_to = email_to, 
				subject = 'Ellen ERP User Entry Count',		 
				body = cont[0], 
				email_cc = email_cc, 
				subtype = 'html', 
				subtype_alternative = 'plain') 
			res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=1, context=context) 
		else: 
			pass 		
		return True
		
		
	
kg_inwardmaster()
