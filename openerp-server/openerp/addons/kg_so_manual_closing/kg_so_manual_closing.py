from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from datetime import date
import openerp.addons.decimal_precision as dp
from datetime import datetime

a = datetime.now()
dt_time = a.strftime('%m/%d/%Y %H:%M:%S')

class kg_so_manual_closing(osv.osv):

	_name = "kg.so.manual.closing"
	_description = "SO Manual Closing Module"
	_order = "trans_date desc"
	
	_columns = {
		
		'c_date': fields.date('Created Date', readonly=True),
		'name': fields.char('No', size=128,select=True,readonly=True),
		'trans_date': fields.date('As On Date', readonly=True, states={'draft':[('readonly',False)]},select=True, required=True),						
		'partner_id': fields.many2one('res.partner', 'Supplier',required=True, select=True,
					domain=[('supplier', '=', True),('sup_state','=','approved')], readonly=True, states={'draft':[('readonly',False)]}),
		'line_ids':fields.one2many('kg.so.manual.closing.line', 'header_id', 'Transaction Line',readonly=True, states={'draft':[('readonly',False)]}),
		'remark': fields.text('Remarks', readonly=True, states={'confirm':[('readonly',False)],'approved':[('readonly',False)]}),		
		'state': fields.selection([('draft','Draft'),('confirm','WFA'),('approved','Approved'),
				('reject','Rejected'),('cancel','Cancelled')],'Status', readonly=True,track_visibility='onchange',select=True),
		'orderby_no': fields.integer('Order By',readonly=True),
		'active': fields.boolean('Active'),
		'total': fields.float('Total Amount', readonly=True),
		'sos_id':fields.many2one('kg.service.order','SO No',domain="[('state','=','approved')]",readonly=False, states={'approved':[('readonly',True)]}),
		
		# Entry Info
		
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),		
		'date': fields.datetime('Created Date', readonly=True)	,
		'user_id': fields.many2one('res.users','Created By', readonly=True),	
		'approve_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Approved By', readonly=True),
		'confirm_date': fields.datetime('Confirmed Date', readonly=True),
		'conf_user_id': fields.many2one('res.users', 'Confirmed By', readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'can_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'update_date': fields.datetime('Last Updated Date', readonly=True),
		'update_user_id': fields.many2one('res.users', 'Last Updated By', readonly=True),
		'cancel_remark': fields.text('Cancel Remarks'),				
		'notes': fields.text('Notes'),
		
		
	}
	
	_defaults = {
	
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg_so_manual_closing', context=c),			
		'trans_date' : fields.date.context_today,
		'date':fields.datetime.now,		
		'state': 'draft',		
		'active': True,
		'user_id': lambda obj, cr, uid, context: uid,
		'c_date' : fields.date.context_today,
		
	}

	def _future_date_check(self,cr,uid,ids,contaxt=None):
		rec = self.browse(cr,uid,ids[0])
		today = date.today()
		today = str(today)
		today = datetime.strptime(today, '%Y-%m-%d')
		trans_date = rec.trans_date
		trans_date = str(trans_date)
		trans_date = datetime.strptime(trans_date, '%Y-%m-%d')
		if trans_date > today:
			return False
		return True		
	
	def _check_line_entry(self, cr, uid, ids, context=None):
		entry = self.browse(cr,uid,ids[0])
		if not entry.line_ids:
			return False
		else:
			for line in entry.line_ids:
				if line.unit_price == 0 or line.quantity == 0:
					return False
		return True
	
	_constraints = [        
              
        #(_check_line_entry, 'System not allow to save empty transaction and zero qty .!!',['price']),
        (_future_date_check, 'System not allow to save with future date. !!',['price']),
        
       ]
	
	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(kg_so_manual_closing, self).write(cr, uid, ids, vals, context)
	
	def load_item(self,cr,uid,ids,context=None):		
		rec =  self.browse(cr,uid,ids[0])
		
		supplier = []
		if rec.line_ids:
			del_sql = """ delete from kg_so_manual_closing_line where header_id=%s """ %(ids[0])
			cr.execute(del_sql)
		if rec.partner_id:
			supplier.append("so.partner_id = '%s'"%(rec.partner_id.id))
		if supplier:
			supplier = 'and ('+' or '.join(supplier)
			supplier =  supplier+')'
		else:
			supplier = ''
		
		sql = """ select *,sol.id as id,so.partner_id as partner_id from kg_service_order_line sol join kg_service_order so on (so.id = sol.service_id) where sol.service_flag='t' and sol.pending_qty > 0 and so.date >='"""+rec.trans_date+"""'"""+ supplier +""" """
		
		cr.execute(sql)
		data = cr.dictfetchall()
		for item in data:
			vals = {
				'sos_id':item['service_id'],
				'sos_line_id':item['id'],
				'product_id':item['product_id'],
				'partner_id':item['partner_id'],
				'uom_id':item['product_uom'],
				'quantity':item['pending_qty'],
				'unit_price':item['price_unit'],
				'total':(item['pending_qty'] or 0) * (item['price_unit'] or 0),
				'header_id':rec.id,
				'close_state':'open'
				}				
				
			if ids:
				self.write(cr,uid,ids[0],{'line_ids':[(0,0,vals)]})
	
		return True	

	def entry_confirm(self,cr,uid,ids,context=None):		
		rec = self.browse(cr,uid,ids[0])
		if rec.line_ids:
			cr.execute(''' select count(*) from kg_so_manual_closing where state !='draft' ''')
			data = cr.fetchone()
			order_by = data[0] + 1	
			seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.so.manual.closing')])
			seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
			cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,rec.trans_date))
			seq_name = cr.fetchone();	
			self.write(cr, uid, ids, {
						'state': 'confirm',
						'conf_user_id': uid,
						'confirm_date': dt_time,
						'orderby_no':order_by,
						'name' : seq_name[0]
						})
		else:
			raise osv.except_osv(_('Warning !!'),
				_('Please add the Line items!!'))						
					
		return True

	def entry_approve(self,cr,uid,ids,context=None):
		so_line_obj = self.pool.get('kg.service.order.line')		
		so_obj = self.pool.get('kg.service.order')
		rec =  self.browse(cr,uid,ids[0])
		for line in rec.line_ids:
			if line.close_state == 'close':
				so_line_obj.write(cr,uid,line.sos_line_id.id, {'state':'cancel'})
				so_record = so_obj.browse(cr,uid,line.sos_id.id)
				so_line_record = so_line_obj.browse(cr,uid,line.sos_line_id.id)
				line_total = so_line_record.price_subtotal
				so_total = so_record.amount_total
				amount_total = so_total - line_total
				line_untax = line.total
				so_untax = so_record.amount_untaxed
				amount_untaxed = so_untax - line_untax
				if so_record.amount_tax > 0:
					line_tax = so_line_record.price_subtotal - (line.total - (so_line_record.kg_discount + so_line_record.kg_discount_per_value))  
					so_tax = so_record.amount_tax
					amount_tax = so_tax - line_tax
				else:
					amount_tax = 0
				
				if so_record.discount > 0:
					line_discount = (so_line_record.kg_discount + so_line_record.kg_discount_per_value)
					so_discount = so_record.discount
					discount = so_discount - line_discount
				else:
					discount = 0	
			
				sql = """ update kg_service_order set amount_total=%s,amount_untaxed = %s,amount_tax = %s,discount = %s where id = %s"""%((round(amount_total,0)),(round(amount_untaxed,0)),(round(amount_tax,0)),(round(discount,0)),line.sos_id.id)
				cr.execute(sql)
						
		self.write(cr, uid, ids, {
				'state': 'approved',
				'app_user_id': uid,
				'approve_date': dt_time})

		return True

	def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.remark:
			self.write(cr, uid, ids, {
						'state': 'reject',
						'rej_user_id': uid,
						'reject_date': dt_time})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
				
		return True

	def entry_cancel(self,cr,uid,ids,context=None):
		## Don't allow to cancel if this id linked with other transaction or master
		rec = self.browse(cr,uid,ids[0])
		if rec.cancel_remark:
			self.write(cr, uid, ids, {
						'state': 'cancel',
						'can_user_id': uid,
						'cancel_date': dt_time})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
				
		return True

	def entry_draft(self,cr,uid,ids,context=None):
		# While change state corresponding back updated to be done
		self.write(cr, uid, ids, {'state': 'draft'})
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
	
kg_so_manual_closing()


class kg_so_manual_closing_line(osv.osv):
	
	_name = "kg.so.manual.closing.line"
	_description = "SO Manual Closing Line"
	
	_columns = {
		
		'header_id': fields.many2one('kg.so.manual.closing','Transaction',ondelete='cascade',select=True),
		'product_id': fields.many2one('product.product', 'Item Name', required=True),
		'uom_id': fields.many2one('product.uom', 'UOM', required=True),
		'quantity': fields.float('Quantity', required=True),
		'unit_price': fields.float('Unit Price', required=True),
		'tax_ids': fields.many2many('account.tax','so_close_taxes', 'line_id','tax_id', 'Taxes'),
		'total': fields.float('Total'),
		'remark': fields.text('Remark'),
		'discount': fields.float('Discount(%)'),
		'sos_id':fields.many2one('kg.service.order', 'SO NO'),
		'sos_line_id':fields.many2one('kg.service.order.line', 'SO Line'),
		'version':fields.char('Version'),
		'dep_project_name':fields.char('Dept/Project Name',readonly=False),
		'remark': fields.text('Remark'),
		'close_state': fields.selection([('open','Open'),('close','Close')],'Closing state',readonly=False),
		'partner_id': fields.many2one('res.partner', 'Supplier', select=True,
					domain=[('supplier', '=', True)], readonly=True),
					
	}	
	
kg_so_manual_closing_line()
