import math
import re
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
import netsvc
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from itertools import groupby

class kg_gate_pass(osv.osv):

	_name = "kg.gate.pass"
	_description = "KG Gate Pass"
	_order = "date desc"

	_columns = {
		
		'name': fields.char('Gate Pass No', size=128, readonly=True),
		'dep_id': fields.many2one('kg.depmaster','Source Location', select=True,readonly=True, states={'draft':[('readonly',False)]},domain="[('state','=','approved')]"),
		'date': fields.date('Gate Pass Date',readonly=True, states={'draft':[('readonly',False)]},required=True),
		'return_date': fields.date('Expected Return Date',readonly=True, states={'draft':[('readonly',False)]}),
		'partner_id': fields.many2one('res.partner', 'Supplier',readonly=True, states={'draft':[('readonly',False)]},domain="[('supplier','=',True),('sup_state','=','approved')]"),
		'gate_line': fields.one2many('kg.gate.pass.line', 'gate_id', 'Gate Pass Line',readonly=True, states={'draft':[('readonly',False)]}),
		'out_type': fields.selection([('g-return', 'G-Return'),('service', 'Service'), ('replacement', 'Replacement'), ('rejection', 'Rejection'), ('transfer', 'Transfer')],'Gate Pass Type',readonly=True, states={'draft':[('readonly',False)]},domain="[('state','=','approved')]"),
		'origin': fields.many2one('kg.service.indent', 'Origin', readonly=True),
		'note': fields.text('Remarks',readonly=False, states={'confirmed':[('readonly',False)],'done':[('readonly',False)]}),
		'state': fields.selection([('draft', 'Draft'), ('confirmed', 'WFA'), ('done', 'Delivered'), ('cancel', 'Cancelled'), ('reject', 'Rejected')], 'Out Status',readonly=True),
		'in_state': fields.selection([('pending', 'Pending'), ('partial', 'Partial'), ('done', 'Received'), ('cancel', 'Cancelled')], 'In Status',readonly=True),
		'si_indent_ids':fields.many2many('kg.service.indent.line','s_indent_gp_entry' , 'si_id', 'gp_id', 'Service Indent Lines',
			domain="[('service_id.state','=','approved'), '&', ('pending_qty','>','0')]", 
			readonly=True, states={'draft': [('readonly', False)]}),
		'indent_flag': fields.boolean('Indent'),
		'transport':fields.char('Transport', size=128,readonly=True, states={'draft':[('readonly',False)]}),
		'taken_by':fields.char('Taken By', size=128,readonly=True, states={'draft':[('readonly',False)]}),
		'received_by':fields.char('Received By', size=128,readonly=True, states={'draft':[('readonly',False)]}),
		'project':fields.char('Project',size=100,readonly=True,states={'draft':[('readonly',False)]}),
		'division':fields.char('Division',size=100,readonly=True,states={'draft':[('readonly',False)]}),
		'confirm_flag':fields.boolean('Confirm Flag'),
		'approve_flag':fields.boolean('Expiry Flag'),
		'mode': fields.selection([('direct', 'Direct'), ('frm_indent', 'From Indent'), ('from_grn', 'From GRN')], 'Entry Mode',required=True,readonly=True, states={'draft':[('readonly',False)]}),
		'gp_type': fields.selection([('from_so', 'From SI'), ('direct', 'Direct')], 'GP Type',readonly=True),
		'remark': fields.text('Remarks'),
		
		# Entry Info
		
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),		
		'user_id': fields.many2one('res.users', 'Created By',readonly=True),
		'creation_date':fields.datetime('Created Date',readonly=True),
		'confirmed_by' : fields.many2one('res.users', 'Confirmed By', readonly=True,select=True),
		'confirmed_date':fields.datetime('Confirmed Date',readonly=True),
		'reject_date': fields.datetime('Reject Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'approved_by' : fields.many2one('res.users', 'Approved By', readonly=True,select=True),
		'approved_date':fields.datetime('Approved Date',readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'update_date': fields.datetime('Last Updated Date', readonly=True),
		'update_user_id': fields.many2one('res.users', 'Last Updated By', readonly=True),
		'active': fields.boolean('Active'),
		'remark': fields.text('Approve/Reject',readonly=False),
		'cancel_remark': fields.text('Cancel Remarks'),				
		'notes': fields.text('Notes'),
		'closing_state':fields.boolean('Gatepass closiing state'),
		
	}
	
	_defaults = {
	
		'creation_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'date' : fields.date.context_today,
		'state':'draft',
		'active': True,
		'closing_state': False,
		'name': '',
		'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.gate.pass', context=c),
		'in_state': 'pending',
		'indent_flag': False,
		'gp_type':'from_so',
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
			if mail_form_rec.sch_type == 'transaction':
				if mail_form_rec.doc_name.model == 'kg.gate.pass':
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
		
	def gp_sechedular_email_ids(self,cr,uid,ids,reg_register,context = None):
		email_from = []
		email_to = []
		email_cc = []
		val = {'email_from':'','email_to':'','email_cc':''}
		ir_model = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		mail_form_ids = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		for ids in mail_form_ids:
			mail_form_rec = self.pool.get('kg.mail.settings').browse(cr,uid,ids)
			if mail_form_rec.sch_type == 'scheduler':
				s = mail_form_rec.sch_name
				s = s.lower()
				if s == reg_register:
					email_sub = mail_form_rec.subject
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
		
	def ogp_sechedular_email_ids(self,cr,uid,ids,context = None):
		email_from = []
		email_to = []
		email_cc = []
		val = {'email_from':'','email_to':'','email_cc':''}
		ir_model = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		mail_form_ids = self.pool.get('kg.mail.settings').search(cr,uid,[('active','=',True)])
		for ids in mail_form_ids:
			mail_form_rec = self.pool.get('kg.mail.settings').browse(cr,uid,ids)
			if mail_form_rec.sch_type == 'scheduler':
				s = mail_form_rec.sch_name
				s = s.lower()
				if s == 'open gate pass register':
					email_sub = mail_form_rec.subject
					email_from.append(mail_form_rec.name)
					mail_line_id = self.pool.get('kg.mail.settings.line').search(cr,uid,[('line_entry','=',ids)])
					for mail_id in mail_line_id:
						mail_line_rec = self.pool.get('kg.mail.settings.line').browse(cr,uid,mail_id)
						if mail_line_rec.to_address:
							email_to.append(mail_line_rec.mail_id)
						if mail_line_rec.cc_address:
							email_cc.append(mail_line_rec.mail_id)
		val['email_from'] = email_from
		val['email_to'] = email_to
		val['email_cc'] = email_cc
		return val	
	
	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id':uid})
		return super(kg_gate_pass, self).write(cr, uid, ids, vals, context)
	
	def cancel_entry(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		if not rec.cancel_remark:
			raise osv.except_osv(_('Cancel remark is must !!'),
				_('Enter Cancel remark in cancel remark field !!'))
		self.write(cr, uid,ids,{'state' : 'cancel',
								'cancel_user_id': uid,
								'cancel_date': time.strftime("%Y-%m-%d %H:%M:%S"),
								})
												
	def reject_entry(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		if not rec.remark:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
		self.write(cr, uid,ids,{'state' : 'cancel',
								'rej_user_id': uid,
								'reject_date': time.strftime("%Y-%m-%d %H:%M:%S"),
								})
												
	def confirm_entry(self, cr, uid, ids, context=None):	
		entry = self.browse(cr,uid,ids[0])
		if entry.gate_line:
			pass 
		else:
			raise osv.except_osv(_('Warning!'),
			_('You cannot save Empty Gate pass'))	
			
		seq_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','kg.gate.pass')])
		seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_id[0])
		cr.execute("""select generatesequenceno(%s,'%s','%s') """%(seq_id[0],seq_rec.code,entry.date))
		seq_name = cr.fetchone();
		if entry.mode == 'frm_indent':
			for line in entry.gate_line:
				if line.qty > line.indent_qty:
					raise osv.except_osv(_('Warning!'),
							_('You cannot increase qty more than indent qty'))	
		if entry.out_type == 'g-return':
			self.write(cr,uid,ids[0],{'state':'confirmed','name':'GR'+seq_name[0],'confirmed_by':uid,
						'confirm_flag':True,'confirmed_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		if entry.out_type == 'service':
			self.write(cr,uid,ids[0],{'state':'confirmed','name':'SR'+seq_name[0],'confirmed_by':uid,
						'confirm_flag':True,'confirmed_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		elif entry.out_type == 'replacement':
			self.write(cr,uid,ids[0],{'state':'confirmed','name':'R'+seq_name[0],'confirmed_by':uid,
						'confirm_flag':True,'confirmed_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		elif entry.out_type == 'rejection':
			self.write(cr,uid,ids[0],{'state':'confirmed','name':'REJ'+seq_name[0],'confirmed_by':uid,
						'confirm_flag':True,'confirmed_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		elif entry.out_type == 'transfer':
			self.write(cr,uid,ids[0],{'state':'confirmed','name':'TR'+seq_name[0],'confirmed_by':uid,
						'confirm_flag':True,'confirmed_date':time.strftime('%Y-%m-%d %H:%M:%S')})
		return True
		
	def approve_entry(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		rec_1 = self.pool.get("kg.gate.pass.line").browse(cr,uid,ids[0])
		stock_move_obj=self.pool.get('stock.move')
		location = rec.dep_id.main_location.location_type
		for i in rec.gate_line:
			uom_id = i.uom
			brand = i.brand_id
			quantity = i.qty
			product = i.product_id
			if product.stockable == 'yes':
				pending_qty_val , val_id= 0 , 0
				if location == 'main':
					sql = """ select pending_qty,id from stock_production_lot where pending_qty > %d and product_id = %d limit 1 """%(quantity,product)
					cr.execute(sql)
					data = cr.dictfetchall()
					for i in data:
						pending_qty_val = int(i['pending_qty'])
						val_id = i['id']
					final_qty_val = pending_qty_val - quantity
					sql1 = """ update  stock_production_lot set pending_qty = %d  where id = %d """%(final_qty_val,val_id)
					cr.execute(sql1)
					stock_move_obj.create(cr,uid,
						{
						'gp_id': rec.id,
						'gp_line_id': rec.gate_line[0].id,
						'product_id': product.id,
						'brand_id':brand.id,
						'name':product.name,
						'product_qty': quantity,
						'stock_uom':uom_id.id,
						'location_id': rec.dep_id.stock_location.id,
						'location_dest_id': 8,
						'product_uom': uom_id.id,
						'move_type': 'out',
						'state': 'done',
						
						})
		if rec.mode == 'frm_indent':
			for line in rec.gate_line:
				indent_pen_qty = line.indent_qty - line.qty
				gp_qty = line.qty
				old_indent_pen_qty = line.si_line_id.pending_qty
				new_pen_qty = old_indent_pen_qty - gp_qty
				line.si_line_id.write({'gate_pending_qty':new_pen_qty})
		else:
			pass
		rec.write({'state': 'done','approved_by':uid,'approve_flag':True,'approved_date':time.strftime('%Y-%m-%d %H:%M:%S')})	
		return True
		
	def gate_pass_print(self, cr, uid, ids, context=None):
		wf_service = netsvc.LocalService("workflow")
		wf_service.trg_validate(uid, 'kg.gate.pass', ids[0], 'send_rfq', cr)
		datas = {
				 'model': 'kg.gate.pass',
				 'ids': ids,
				 'form': self.read(cr, uid, ids[0], context=context),
		}
		return {'type': 'ir.actions.report.xml', 'report_name': 'gate.pass.report', 'datas': datas, 'nodestroy': True}

	def create_gp_line(self,cr,uid,ids,context=False):
				
		indent_line_obj = self.pool.get('kg.service.indent.line')
		gp_line_obj = self.pool.get('kg.gate.pass.line')
		prod_obj = self.pool.get('product.product')		
		user_obj = self.pool.get('res.users')
		line_ids = []			   
		res={}
		res['line_ids'] = []
		res['indent_flag'] = True
		obj =  self.browse(cr,uid,ids[0])
		user_rec = obj.user_id
		user = user_rec.id
		if obj.gate_line:
			for line in obj.gate_line:
				line.si_line_id.write({'line_state' : 'noprocess'})			
			line_ids = map(lambda x:x.id,obj.gate_line)
			gp_line_obj.unlink(cr,uid,line_ids)
		if obj.si_indent_ids:
			indent_line_ids = map(lambda x:x.id,obj.si_indent_ids)
			indent_line_browse = indent_line_obj.browse(cr,uid,indent_line_ids)
			indent_line_browse = sorted(indent_line_browse, key=lambda k: k.product_id.id)
			groups = []
			for key, group in groupby(indent_line_browse, (lambda x: x.product_id.id)  ):
				for key,group in groupby(group,lambda x: x.brand_id.id):
					groups.append(map(lambda r:r,group))
			for key,group in enumerate(groups):
				qty = sum(map(lambda x:float(x.qty),group))
				pending_qty = sum(map(lambda x:float(x.pending_qty),group)) #TODO: qty
				indent_line_ids = map(lambda x:x.id,group)
				if len(indent_line_ids) > 1:
					flag = True
				else:
					flag = False
				prod_browse = group[0].product_id
				brand_id = group[0].brand_id			
				uom = group[0].uom.id or False
				depindent_id= group[0].id
				qty = pending_qty
				remark = group[0].note
				serial_no = group[0].serial_no.id
				ser_no = group[0].ser_no
					
				vals = {
			
				'product_id':prod_browse.id,
				'brand_id':brand_id.id,
				'uom':uom,
				'qty':qty,
				'indent_qty':qty,
				'grn_pending_qty':qty,				
				'so_pending_qty':qty,						
				'si_line_id':depindent_id,				
				'group_flag': flag,
				'note':remark,
				'ser_no':ser_no,
				'serial_no':serial_no,
				}
				
				if pending_qty == 0:				
					indent_line_obj.write(cr,uid,depindent_id,{'line_state' : 'process'})
				
				if ids:
					self.write(cr,uid,ids[0],{'gate_line':[(0,0,vals)]})
								
		self.write(cr,uid,ids,res)			
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
		
	def update_product_group(self,cr,uid,ids,line,context=None):		
		pi_rec = self.browse(cr, uid, ids[0])
		line_obj = self.pool.get('purchase.requisition.line')
		dep_line_obj = self.pool.get('kg.depindent.line')
		product_obj = self.pool.get('product.product')
		cr.execute(""" select depindent_line_id from kg_depindent_pi_line where pi_id = %s """ %(str(ids[0])))
		data = cr.dictfetchall()
		val = [d['depindent_line_id'] for d in data if 'depindent_line_id' in d] 
		product_id = line.product_id.id
		product_record = product_obj.browse(cr, uid, product_id)
		list_line = dep_line_obj.search(cr,uid,[('id', 'in', val), ('product_id', '=', product_id)],context=context)
		depindent_line_id=line.depindent_line_id
		pi_qty = line.product_qty
		
		for i in list_line:
			bro_record = dep_line_obj.browse(cr, uid,i)
			orig_depindent_qty = bro_record.pending_qty
			po_uom_qty = bro_record.po_qty
			pi_used_qty = pi_qty
			uom = bro_record.uom.id
			po_uom = bro_record.po_uom.id
			if uom != po_uom:					
				if pi_used_qty <= po_uom_qty:
					pending_po_depindent_qty =  po_uom_qty - pi_used_qty
					pending_stock_depindent_qty = orig_depindent_qty - (pi_used_qty * product_record.po_uom_coeff)
					sql = """ update kg_depindent_line set po_qty=%s, pending_qty=%s where id = %s"""%(pending_po_depindent_qty,
						pending_stock_depindent_qty,bro_record.id)
					cr.execute(sql)
					#dep_line_obj.write(cr,uid, bro_record.id, {'line_state' : 'noprocess'})
					break
				else:
					remain_qty = pi_used_qty - po_uom_qty
					pi_qty = remain_qty
					pending_po_depindent_qty =  0.0
					pending_stock_depindent_qty = 0.0
					sql = """ update kg_depindent_line set po_qty=%s, pending_qty=%s where id = %s"""%(pending_po_depindent_qty,
						pending_stock_depindent_qty,bro_record.id)
					cr.execute(sql)
					#dep_line_obj.write(cr,uid, bro_record.id, {'line_state' : 'noprocess'})
					if remain_qty < 0:
						break			
			else:
				if pi_used_qty <= po_uom_qty:
					pending_po_depindent_qty =  po_uom_qty - pi_used_qty
					pending_stock_depindent_qty = po_uom_qty - pi_used_qty 
					sql = """ update kg_depindent_line set po_qty=%s, pending_qty=%s where id = %s"""%(pending_po_depindent_qty,
						pending_stock_depindent_qty,bro_record.id)
					cr.execute(sql)
					#dep_line_obj.write(cr,uid, bro_record.id, {'line_state' : 'noprocess'})
					break
				else:
					remain_qty = pi_used_qty - po_uom_qty
					pi_qty = remain_qty
					pending_po_depindent_qty =  0.0
					pending_stock_depindent_qty = 0.0
					sql = """ update kg_depindent_line set po_qty=%s, pending_qty=%s where id = %s"""%(pending_po_depindent_qty,
						pending_stock_depindent_qty,bro_record.id)
					cr.execute(sql)
					#dep_line_obj.write(cr,uid, bro_record.id, {'line_state' : 'noprocess'})
					if remain_qty < 0:
						break		
		return True
	
	def gate_pass_register_scheduler(self,cr,uid,ids=0,context = None):
		cr.execute(""" SELECT current_database();""")
		db = cr.dictfetchall()
		if db[0]['current_database'] == 'Empereal-KGDS':
			db[0]['current_database'] = 'Empereal-KGDS'
		elif db[0]['current_database'] == 'FSL':
			db[0]['current_database'] = 'FSL'
		elif db[0]['current_database'] == 'IIM':
			db[0]['current_database'] = 'IIM'
		elif db[0]['current_database'] == 'IIM_HOSTEL':
			db[0]['current_database'] = 'IIM Hostel'
		elif db[0]['current_database'] == 'KGISL-SD':
			db[0]['current_database'] = 'KGISL-SD'
		elif db[0]['current_database'] == 'CHIL':
			db[0]['current_database'] = 'CHIL'
		elif db[0]['current_database'] == 'KGCAS':
			db[0]['current_database'] = 'KGCAS'
		elif db[0]['current_database'] == 'KGISL':
			db[0]['current_database'] = 'KGISL'
		elif db[0]['current_database'] == 'KITE':
			db[0]['current_database'] = 'KITE'
		elif db[0]['current_database'] == 'TRUST':
			db[0]['current_database'] = 'TRUST'
		else:
			db[0]['current_database'] = 'Others'
			
		line_rec = self.pool.get('kg.gate.pass').search(cr, uid, [('state','=','done'),('approved_date','=',time.strftime('%Y-%m-%d'))])

		if line_rec:	
			cr.execute("""select all_daily_auto_scheduler_mails('Gate Pass Register')""")
			data = cr.fetchall();
			cr.execute("""select  trim(TO_CHAR(sum(kg_gate_pass_line.qty * kg_service_order_line.price_unit)::float, '999G999G99G999G99G99G990D99')) as sum
							from kg_gate_pass
							left join kg_gate_pass_line on kg_gate_pass_line.gate_id = kg_gate_pass.id
							left join kg_service_order_line on kg_service_order_line.soindent_line_id=kg_gate_pass_line.si_line_id
							where to_char(kg_gate_pass.date,'dd-mm-yyyy') = '%s' and 
							kg_gate_pass.state in ('done') """%(time.strftime('%d-%m-%Y')))
							
			total_sum = cr.dictfetchall();
			db = db[0]['current_database'].encode('utf-8')
			total_sum = str(total_sum[0]['sum'])
			if total_sum == 'None':
				total_sum = '0.00'
			else:
				total_sum = total_sum
			vals = self.gp_sechedular_email_ids(cr,uid,ids,reg_register = 'gate pass register',context = context)
			if (not vals['email_to']) and (not vals['email_cc']):
				pass
			else:
				ir_mail_server = self.pool.get('ir.mail_server')
				msg = ir_mail_server.build_email(
						email_from = vals['email_from'][0],
						email_to = vals['email_to'],
						subject = "ERP Gate Pass Register Details for "+db +' as on '+time.strftime('%d-%m-%Y'),
						body = data[0][0],
						email_cc = vals['email_cc'],
						object_id = ids and ('%s-%s' % (ids, 'purchase.order')),
						subtype = 'html',
						subtype_alternative = 'plain')
				res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=1, context=context)
		else:
			pass		
				
		return True
	
	def open_gate_pass_register_scheduler(self,cr,uid,ids=0,context = None):
		cr.execute(""" SELECT current_database();""")
		db = cr.dictfetchall()
		if db[0]['current_database'] == 'Empereal-KGDS':
			db[0]['current_database'] = 'Empereal-KGDS'
		elif db[0]['current_database'] == 'FSL':
			db[0]['current_database'] = 'FSL'
		elif db[0]['current_database'] == 'IIM':
			db[0]['current_database'] = 'IIM'
		elif db[0]['current_database'] == 'IIM_HOSTEL':
			db[0]['current_database'] = 'IIM Hostel'
		elif db[0]['current_database'] == 'KGISL-SD':
			db[0]['current_database'] = 'KGISL-SD'
		elif db[0]['current_database'] == 'CHIL':
			db[0]['current_database'] = 'CHIL'
		elif db[0]['current_database'] == 'KGCAS':
			db[0]['current_database'] = 'KGCAS'
		elif db[0]['current_database'] == 'KGISL':
			db[0]['current_database'] = 'KGISL'
		elif db[0]['current_database'] == 'KITE':
			db[0]['current_database'] = 'KITE'
		elif db[0]['current_database'] == 'TRUST':
			db[0]['current_database'] = 'TRUST'
		else:
			db[0]['current_database'] = 'Others'
			
		line_rec = self.pool.get('kg.gate.pass').search(cr, uid, [('state','=','done'),('in_state','!=','done'),('approved_date','<=',time.strftime('%Y-%m-%d'))])
		
		if line_rec:
			
			cr.execute("""select all_daily_auto_scheduler_mails('Open Gate Pass Register')""")
			data = cr.fetchall();
			vals = self.ogp_sechedular_email_ids(cr,uid,ids,context = context)
			db = db[0]['current_database'].encode('utf-8')
			if (not vals['email_to']) and (not vals['email_cc']):
				pass
			else:
				ir_mail_server = self.pool.get('ir.mail_server')
				msg = ir_mail_server.build_email(
						email_from = vals['email_from'][0],
						email_to = vals['email_to'],
						subject = "ERP Open Gate Pass Details for "+ db +' as on '+time.strftime('%d-%m-%Y'),
						body = data[0][0],
						email_cc = vals['email_cc'],
						object_id = ids and ('%s-%s' % (ids, 'purchase.order')),
						subtype = 'html',
						subtype_alternative = 'plain')
				res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=1, context=context)
		else:
			pass		
				
		return True
	
kg_gate_pass()

class kg_gate_pass_line(osv.osv):
	
	_name = "kg.gate.pass.line"
	_description = "Gate Pass Line"
	
	
	_columns = {

	'gate_id': fields.many2one('kg.gate.pass', 'Gate Pass', ondelete='cascade',),
	'product_id': fields.many2one('product.product', 'Item Name',domain="[('state','=','approved')]"),
	'brand_id': fields.many2one('kg.brand.master', 'Brand Name',domain="[('state','=','approved')]"),
	'uom': fields.many2one('product.uom', 'UOM',domain="[('dummy_state','=','approved')]"),
	'qty': fields.float('Quantity'),
	'indent_qty': fields.float('Indent Qty'),
	'grn_pending_qty': fields.float('GRN pending Qty'),
	'so_pending_qty': fields.float('SO pending Qty'),
	'note': fields.text('Remarks'),
	'si_line_id':fields.many2one('kg.service.indent.line', 'Service Indent Line'),
	'group_flag':fields.boolean('Group By'),
	'ser_no':fields.char('Serial No', size=128),
	'so_flag':fields.boolean('SO Flag'),
	'serial_no':fields.many2one('stock.production.lot','Serial No',domain="[('product_id','=',product_id)]"),	
	'mode': fields.selection([('direct', 'Direct'), ('frm_indent', 'From Indent'),('from_grn', 'From GRN')], 'Mode'),
	
	}
	
	def onchange_uom(self, cr, uid, ids,product_id):
		if product_id:
			pro_rec = self.pool.get('product.product').browse(cr, uid,product_id)
			uom = pro_rec.uom_po_id.id
			return {'value': {'uom': uom}}
		else:
			return {'value': {'uom': False}}
	
	def onchange_pending_qty(self, cr, uid, ids,qty,grn_pending_qty,so_pending_qty):
		value = {'grn_pending_qty': '','so_pending_qty':''}
		value = {'grn_pending_qty': qty,'so_pending_qty': qty}
		return {'value': value}
		
	def default_get(self, cr, uid, fields, context=None):
		print"contextcontextcontext",context
		
		return context
		
kg_gate_pass_line()
