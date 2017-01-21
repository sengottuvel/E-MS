from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from datetime import date
import openerp.addons.decimal_precision as dp
from datetime import datetime

a = datetime.now()
dt_time = a.strftime('%m/%d/%Y %H:%M:%S')

class kg_depindent_manual_closing(osv.osv):

	_name = "kg.depindent.manual.closing"
	_description = "Department Indent Manual Closing Module"
	_order = "trans_date desc"
	
	_columns = {

		'date': fields.datetime('Created Date', readonly=True)	,
		'c_date': fields.date('Created Date', readonly=True),
		'user_id': fields.many2one('res.users','Created By', readonly=True),		
		'department_id': fields.many2one('kg.depmaster','Department'),		
		'name': fields.char('No', size=128,select=True,readonly=True),
		'trans_date': fields.date('As On Date', readonly=True, states={'draft':[('readonly',False)]},
											select=True, required=True),						

		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),		
		'line_ids':fields.one2many('kg.depindent.manual.closing.line', 'header_id', 'Transaction Line',readonly=True, states={'draft':[('readonly',False)]}),
		'remark': fields.text('Remarks', readonly=True, states={'draft':[('readonly',False)]}),		
		'state': fields.selection([('draft','Draft'),('confirm','WFA'),('approved','Approved'),
				('reject','Rejected'),('cancel','Cancelled')],'Status', readonly=True,track_visibility='onchange',select=True),
		'approve_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Approved By', readonly=True),
		'confirm_date': fields.datetime('Confirmed Date', readonly=True),
		'conf_user_id': fields.many2one('res.users', 'Confirmed By', readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'can_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'orderby_no': fields.integer('Order By',readonly=True),
		'active': fields.boolean('Active'),
		'total': fields.float('Total Amount', readonly=True),
		'depindent_id':fields.many2one('kg.depindent','DI No',required=True,domain="[('state','=','approved')]",readonly=False, states={'approved':[('readonly',True)]}),
		'update_date': fields.datetime('Last Updated Date', readonly=True),
		'update_user_id': fields.many2one('res.users', 'Last Updated By', readonly=True),
		'cancel_remark': fields.text('Cancel Remarks'),				
		'notes': fields.text('Notes'),
		
	}
	
	_defaults = {
	
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg_depindent_manual_closing', context=c),			
		'trans_date' : fields.date.context_today,
		'c_date' : fields.date.context_today,
		'date':fields.datetime.now,		
		'state': 'draft',		
		'active': True,
		'user_id': lambda obj, cr, uid, context: uid,
		
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
              
        (_future_date_check, 'System not allow to save with future date. !!',['price']),
        
       ]

	
	def load_item(self,cr,uid,ids,context=None):		
		rec =  self.browse(cr,uid,ids[0])
		supplier = []
		if rec.line_ids:
			del_sql = """ delete from kg_depindent_manual_closing_line where header_id=%s """ %(ids[0])
			cr.execute(del_sql)
		sql = """ select indent_id,id,product_id,uom,brand_id,qty,pending_qty from kg_depindent_line where pending_qty > 0 and issue_pending_qty > 0 and line_state != 'process' and indent_id = %s""" %(rec.depindent_id.id)
		cr.execute(sql)
		data = cr.dictfetchall()
		for item in data:
			vals = {
				'depindent_id':item['indent_id'],
				'depindent_line_id':item['id'],
				'product_id':item['product_id'],
				'brand_id':item['brand_id'],
				
				'uom_id':item['uom'],
				'quantity':item['qty'],
				'pen_qty':item['pending_qty'],
			
				'header_id':rec.id,
				'close_state':'open'
				}				
				
			if ids:
				self.write(cr,uid,ids[0],{'line_ids':[(0,0,vals)]})
		
	
		return True	


	def entry_confirm(self,cr,uid,ids,context=None):
		rec =  self.browse(cr,uid,ids[0])
		if rec.line_ids:

			di_line_obj = self.pool.get('kg.depindent.line')		
			pi_line_obj = self.pool.get('purchase.requisition.line')		
			pi_obj = self.pool.get('purchase.requisition')		
			di_obj = self.pool.get('kg.depindent')
			for line in rec.line_ids:
				if line.close_state == 'close':
					pi_line_id = pi_line_obj.search(cr,uid,[('depindent_line_id','=',line.depindent_line_id.id),('line_state','=','noprocess')])
					if pi_line_id:
						raise osv.except_osv(
						_('You cannot close this indent'),
						_('Because it was refered in Purchase Indent  %s.' %(pi_line_id[0].requisition_id.name)))
					else:
					
						pass
			
			cr.execute(''' select count(*) from kg_depindent_manual_closing where state !='draft' ''')
			data = cr.fetchone()
			order_by = data[0] + 1	
			di_name = ''		
			if not rec.name:
						
				di_no = self.pool.get('ir.sequence').get(cr, uid, 'kg.depindent.manual.closing') or ''
				di_no_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.depindent.manual.closing')])
				di_rec = self.pool.get('ir.sequence').browse(cr,uid,di_no_id[0])
				cr.execute("""select generatesequenceno(%s,'%s','%s') """%(di_no_id[0],di_rec.code,rec.trans_date))
				di_name = cr.fetchone();	
				self.write(cr,uid,ids,{'name':str(di_name[0])})				
						
						
			self.write(cr, uid, ids, {
						'state': 'confirm',
						'conf_user_id': uid,
						'confirm_date': dt_time,
						
						
						})
		else:
			raise osv.except_osv(_('Warning !!'),
				_('Please add the Line items!!'))	
				
		return True

	def entry_approve(self,cr,uid,ids,context=None):
		rec =  self.browse(cr,uid,ids[0])
		di_line_obj = self.pool.get('kg.depindent.line')		
		pi_line_obj = self.pool.get('purchase.requisition.line')		
		pi_obj = self.pool.get('purchase.requisition')		
		di_obj = self.pool.get('kg.depindent')
		
		for line in rec.line_ids:
			if line.close_state == 'close':
				pi_line_id = pi_line_obj.search(cr,uid,[('depindent_line_id','=',line.depindent_line_id.id),('dep_id.state','not in',('approved','cancel'))])
				if pi_line_id:
					pi_line_browse = pi_line_obj.browse(cr,uid,pi_line_id[0])	
					raise osv.except_osv(
					_('You cannot close this indent'),
					_('Because it was refered in Purchase Indent  %s.' %(pi_line_browse.requisition_id.name)))
				else:
				
					pend_qty = line.depindent_line_id.pending_qty
					issue_qty = line.depindent_line_id.qty - line.depindent_line_id.pending_qty
					di_line_obj.write(cr,uid,line.depindent_line_id.id,{'pending_qty':0,'issue_pending_qty':issue_qty})
							
				
						
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
	
kg_depindent_manual_closing()


class kg_depindent_manual_closing_line(osv.osv):
	
	_name = "kg.depindent.manual.closing.line"
	_description = "Department Indent Manual Closing Line"
	
	_columns = {
		
		'header_id': fields.many2one('kg.depindent.manual.closing','Transaction',ondelete='cascade',select=True),
		'product_id': fields.many2one('product.product', 'Item Name', required=True),
		'brand_id':fields.many2one('kg.brand.master','Brand Name'),
		'uom_id': fields.many2one('product.uom', 'UOM', required=True),
		'quantity': fields.float('Quantity', required=True),
		'pen_qty': fields.float('Pending Quantity'),
		
		'remark': fields.text('Remark'),
		'discount': fields.float('Discount(%)'),
		'depindent_id':fields.many2one('kg.depindent', 'DI NO'),
		'depindent_line_id':fields.many2one('kg.depindent.line', 'DP Line'),
		'version':fields.char('Version'),
		'dep_project_name':fields.char('Dept/Project Name',readonly=False),
		'remark': fields.text('Remark'),
		'close_state': fields.selection([('open','Open'),('close','Close')],'Closing state',readonly=False),
		
	}	
	
kg_depindent_manual_closing_line()
