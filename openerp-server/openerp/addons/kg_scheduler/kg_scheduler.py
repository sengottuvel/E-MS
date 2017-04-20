from dateutil.relativedelta import relativedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import datetime
import calendar
import time


class kg_scheduler(osv.osv):

	_name = "kg.scheduler"	
	_description = "scheduler"
	
		
	def dead_stock_register_scheduler(self,cr,uid,ids=0,context = None):
		cr.execute(""" SELECT current_database();""")
		db = cr.dictfetchall()
		if db[0]['current_database'] == 'foundry_local':
			db[0]['current_database'] = 'foundry_local'
		else:
			db[0]['current_database'] = 'Others'
		cr.execute("""select non_moveable_stock_mails('Unused Stock Register')""")
		data = cr.fetchall();
		cr.execute("""SELECT to_date(to_char(now()::date - interval '1 month', 'YYYY/MM/DD'), 'YYYY/MM/DD') as last_dt""")
		last_dt = cr.fetchall();
		cr.execute("""select * from stock_production_lot	where 
		to_char(write_date,'yyyy-mm-dd') <= '%s' and pending_qty = product_qty and pending_qty > 0"""%(last_dt[0]))
		data1 = cr.fetchall();
		if data1:	
			cr.execute("""select sum(tot_name),to_char(sum(tot_name),'999G999G99G999G99G99G990D99') as cost from (select product_product.name_template,product_uom.name,stock_production_lot.pending_qty,
					stock_production_lot.grn_no,stock_production_lot.price_unit,(stock_production_lot.price_unit * stock_production_lot.pending_qty) as tot_name
					
					from stock_production_lot
					
					left join product_product on product_product.id = stock_production_lot.product_id
					left join product_uom on product_uom.id = stock_production_lot.product_uom
					where 
					to_char(stock_production_lot.write_date,'yyyy-mm-dd') <= '%s' and stock_production_lot.pending_qty = stock_production_lot.product_qty and stock_production_lot.pending_qty > 0
					order by stock_production_lot.date,stock_production_lot.grn_no) as p    """%(last_dt[0]))
			total_sum = cr.dictfetchall();
			db = db[0]['current_database'].encode('utf-8')
			total = total_sum[0]['sum'] or ''
			vals = self.sechedular_email_ids(cr,uid,ids,reg_string = 'dead stock',context = context)
			if (not vals['email_to']) and (not vals['email_cc']):
				pass
			else:
				
				if total :
					subject = "ERP Foundry - Non-Movable stock (for last 30 days) Details for "+db+' as on ' + time.strftime('%d-%m-%Y') + '. Total Values : Rs. ' +  str(total_sum[0]['cost']) + ' /- '
				
				else:
					subject = "ERP Foundry - Non-Movable stock (for last 30 days) Details for "+db+' as on ' + time.strftime('%d-%m-%Y') + '.'
				
				
				ir_mail_server = self.pool.get('ir.mail_server')
				msg = ir_mail_server.build_email(
						email_from = vals['email_from'][0],
						email_to = vals['email_to'],
						subject = subject,
						body = data[0][0],
						email_cc = vals['email_cc'],
						object_id = ids and ('%s-%s' % (ids, 'kg.general.grn')),
						subtype = 'html',
						subtype_alternative = 'plain')
				res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=2, context=context)
		return True
		
	def sechedular_email_ids(self,cr,uid,ids,reg_string,context = None):
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
				if s == reg_string:
					email_sub = mail_form_rec.subject
					email_from.append(mail_form_rec.name)
					mail_line_id = self.pool.get('ch.mail.settings.line').search(cr,uid,[('header_id','=',ids)])
					for mail_id in mail_line_id:
						mail_line_rec = self.pool.get('ch.mail.settings.line').browse(cr,uid,mail_id)
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
		
		
	def open_gate_pass_mail(self, cr, uid, ids=0, context=None):
		cr.execute("""select ROW_NUMBER() OVER(ORDER BY kg_gate_pass_line.id) sl_no,
			product_product.name_template,product_uom.name,kg_gate_pass_line.grn_pending_qty,current_date - kg_gate_pass.date,
			kg_gate_pass_line.grn_pending_qty * kg_service_order_line.price_unit,res_partner.name,kg_gate_pass.out_type,
			kg_gate_pass.name,to_char(kg_gate_pass.date,'dd/mm/yyyy'),kg_gate_pass_line.qty,kg_gate_pass_line.qty - kg_gate_pass_line.grn_pending_qty,
			kg_gate_pass.note
			from kg_gate_pass
			left join kg_gate_pass_line on kg_gate_pass_line.gate_id = kg_gate_pass.id
			left join product_product on product_product.id = kg_gate_pass_line.product_id
			left join product_uom on product_uom.id = kg_gate_pass_line.uom
			left join kg_service_order_line on kg_service_order_line.soindent_line_id=kg_gate_pass_line.si_line_id
			left join res_partner on res_partner.id = kg_gate_pass.partner_id
			where kg_gate_pass.state in ('done') and kg_gate_pass_line.grn_pending_qty > 0 and  
			to_char(kg_gate_pass.approved_date,'yyyy-mm-dd') <= to_char((select current_date-7 limit 1),'yyyy-mm-dd') 
			and 
			kg_gate_pass.out_type in ('service') or to_char(kg_gate_pass.return_date,'yyyy-mm-dd') <= to_char((select current_date limit 1),'yyyy-mm-dd')
			and kg_gate_pass.out_type in ('replacement')
			

			 order by to_char(kg_gate_pass.date,'dd/mm/yyyy'),kg_gate_pass.date,kg_gate_pass.name;""")	
		data1 = cr.fetchall();
		if data1:
			cr.execute("""SELECT open_gate_pass_mail('Open Gate Pass Register')""") 
			data = cr.fetchall();
			if data[0][0] is None:
				return False
			if data[0][0] is not None:	
				maildet = (str(data[0])).rsplit('~');
				cont = data[0][0].partition('UNWANTED.')		
				email_from = maildet[1]	
				if maildet[2]:	
					email_to = [maildet[2]]
				else:
					email_to = ['']			
				if maildet[3]:
					email_cc = [maildet[3]]	
				else:
					email_cc = ['']		
				ir_mail_server = self.pool.get('ir.mail_server')
				if maildet[4] != '':
					msg = ir_mail_server.build_email(
						email_from = email_from,
						email_to = email_to,
						subject = maildet[4],
						body = cont[0],
						email_cc = email_cc,
						object_id = ids and ('%s-%s' % (ids, 'kg.mail.settings')),
						subtype = 'html',
						subtype_alternative = 'plain')
					res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=2, context=context)
				else:
					pass
		return True	
		
		
	def daily_inward_register_mail(self, cr, uid, ids=0, context=None):
		cr.execute("""SELECT daily_inward_register('Daily Inward Register')""") 
		data = cr.fetchall();
		cr.execute("""select * from stock_production_lot where date >= (select current_date)""")
		data1 = cr.fetchall();
		if data1:
			if data[0][0] is None:
				return False
			if data[0][0] is not None:	
				maildet = (str(data[0])).rsplit('~');
				cont = data[0][0].partition('UNWANTED.')		
				email_from = maildet[1]	
				if maildet[2]:	
					email_to = [maildet[2]]
				else:
					email_to = ['']			
				if maildet[3]:
					email_cc = [maildet[3]]	
				else:
					email_cc = ['']		
				ir_mail_server = self.pool.get('ir.mail_server')
				if maildet[4] != '':
					msg = ir_mail_server.build_email(
						email_from = email_from,
						email_to = email_to,
						subject = maildet[4],
						body = cont[0],
						email_cc = email_cc,
						object_id = ids and ('%s-%s' % (ids, 'kg.mail.settings')),
						subtype = 'html',
						subtype_alternative = 'plain')
					res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=2, context=context)
				else:
					pass
		return True			
		
		
	def daily_purchase_order_mail(self, cr, uid, ids=0, context=None):
		cr.execute("""SELECT daily_purchase_order('Purchase Order')""") 
		data = cr.fetchall();
		if data[0][0] is None:
			return False
		if data[0][0] is not None:	
			maildet = (str(data[0])).rsplit('~');
			cont = data[0][0].partition('UNWANTED.')		
			email_from = maildet[1]	
			if maildet[2]:	
				email_to = [maildet[2]]
			else:
				email_to = ['']			
			if maildet[3]:
				email_cc = [maildet[3]]	
			else:
				email_cc = ['']		
			ir_mail_server = self.pool.get('ir.mail_server')
			if maildet[4] != '':
				msg = ir_mail_server.build_email(
					email_from = email_from,
					email_to = email_to,
					subject = maildet[4],
					body = cont[0],
					email_cc = email_cc,
					object_id = ids and ('%s-%s' % (ids, 'kg.mail.settings')),
					subtype = 'html',
					subtype_alternative = 'plain')
				res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=2, context=context)
			else:
				pass
		return True		
		
		
	def auto_purchase_indent(self, cr, uid, ids=0, context=None):
		flag =0
		product_obj = self.pool.get('product.product')
		product_ids = """ select id from product_product where flag_minqty_rule = 't'  and state = 'approved' """
		cr.execute(product_ids)	
		product_data = cr.dictfetchall()
		for i in list(product_data):
			value = i['id']
			product_id_val = self.pool.get('product.product').browse(cr, uid, value)
			lot_sql = """select COALESCE((select sum(pending_qty) from stock_production_lot where product_id=%s),0) + 
COALESCE((select sum(pending_qty) from kg_depindent_line where product_id =%s),0) +
COALESCE((select sum(pending_qty) from purchase_requisition_line where product_id=%s),0) +
COALESCE((select sum(pending_qty) from purchase_order_line where product_id =%s),0) - 
COALESCE((select minimum_qty from product_product where id=%s),0)
as result"""%(value,value,value,value,value)
			cr.execute(lot_sql)
			lot_data = cr.dictfetchall()
			if lot_data[0]['result'] < 0:
				flag =1		
		if flag ==1:
			kg_purchase_id=self.pool.get('purchase.requisition')
			kg_purchase_line_id=self.pool.get('purchase.requisition.line')
			exp_date_sql= """ select current_date+7 as date """
			cr.execute(exp_date_sql)
			exp_date = cr.dictfetchall()
			indent_ids = kg_purchase_id.create(cr,uid,
					{
					'dep_name':72,
					'indent_type':'direct',
					'entry_mode':'auto',
					'state':'draft',
					'pi_flag':True,
					'notes':'This indent for full-fill the minimum stock level of inventory ',
					'expected_date':exp_date[0]['date'],
					})
			for j in list(product_data):
				value1 = j['id']
				product_id_val = self.pool.get('product.product').browse(cr, uid, value1)
				lot_sq = """select COALESCE((select sum(pending_qty) from stock_production_lot where product_id=%s),0) + 
	COALESCE((select sum(pending_qty) from kg_depindent_line where product_id =%s),0) +
	COALESCE((select sum(pending_qty) from purchase_requisition_line where product_id=%s),0) +
	COALESCE((select sum(pending_qty) from purchase_order_line where product_id =%s),0) - 
	COALESCE((select minimum_qty from product_product where id=%s),0)
	as result"""%(value1,value1,value1,value1,value1)
				cr.execute(lot_sq)
				lot_dat = cr.dictfetchall()
				if lot_dat[0]['result'] < 0:
					cr.execute("""select reorder_qty from product_product where id =%s"""%(value1)) 
					reorder_qty = cr.dictfetchall()
					cr.execute("""select sum(pending_qty) from stock_production_lot where product_id=%s"""%(value1)) 
					curr_qty = cr.dictfetchall()
					cur_date_sql= """ select current_date"""
					cr.execute(cur_date_sql)
					cur_date = cr.dictfetchall()
					kg_purchase_line_id.create(cr,uid,
						{
						'requisition_id':indent_ids,
						'product_id':value1,
						'product_uom_id':product_id_val.uom_po_id.id,
						'product_qty':reorder_qty[0]['reorder_qty'],
						'pending_qty':reorder_qty[0]['reorder_qty'],
						'expected_date':exp_date[0]['date'],
						'stock_qty':curr_qty[0]['sum'] or 0,
						'line_state':'noprocess',
						'name':'PILINE',
						'indent_state':'t',
						'line_date':cur_date[0]['date'],
						'note':'This indent for full-fill the minimum stock level of inventory ',
						})
		return	
		
		
	def minimum_stock_alert(self, cr, uid, ids=0, context=None):
		cr.execute("""SELECT minimum_stock_alert('Minimum Stock')""") 
		data = cr.fetchall();
		cr.execute("""select * from (

select name_template,
COALESCE((select sum(pending_qty) from stock_production_lot where product_id =pp.id
 group by product_id,product_uom),0.00) as current_stock,minimum_qty from product_product as pp where flag_minqty_rule ='t' and active='t'
) as a 
where minimum_qty > current_stock""")
		data1 = cr.fetchall();
		if data1:
			if data[0][0] is None:
				return False
			if data[0][0] is not None:	
				maildet = (str(data[0])).rsplit('~');
				cont = data[0][0].partition('UNWANTED.')		
				email_from = maildet[1]	
				if maildet[2]:	
					email_to = [maildet[2]]
				else:
					email_to = ['']			
				if maildet[3]:
					email_cc = [maildet[3]]	
				else:
					email_cc = ['']		
				ir_mail_server = self.pool.get('ir.mail_server')
				if maildet[4] != '':
					msg = ir_mail_server.build_email(
						email_from = email_from,
						email_to = email_to,
						subject = maildet[4],
						body = cont[0],
						email_cc = email_cc,
						object_id = ids and ('%s-%s' % (ids, 'kg.mail.settings')),
						subtype = 'html',
						subtype_alternative = 'plain')
					res = ir_mail_server.send_email(cr, uid, msg,mail_server_id=2, context=context)
				else:
					pass
		return True				
