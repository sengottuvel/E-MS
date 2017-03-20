
import time
from report import report_sxw
from reportlab.pdfbase.pdfmetrics import stringWidth
import locale
from datetime import datetime, date
import ast


class kg_purchase_invoice_register(report_sxw.rml_parse):
	
	_name = 'kg.purchase.invoice.register'
	

	def __init__(self, cr, uid, name, context=None):
		if context is None:
			context = {}
		super(kg_purchase_invoice_register, self).__init__(cr, uid, name, context=context)
		self.query = ""
		self.period_sql = ""
		self.localcontext.update( {
			'time': time,
			'get_filter': self._get_filter,
			'get_start_date':self._get_start_date,
			'get_end_date':self._get_end_date,
			'get_data':self.get_data,
			'locale':locale,
			#'get_data_line':self.get_data_line,

		})
		self.context = context
		
	def get_data(self,form):
		
		res = {}
		where_sql = []
		payment = []
		payment1 = []
		supplier = []
		invoice = []
		voucher = []
		direct = []
		
		data_new = []	   
		
		state1 = 'done'
		state2 = 'done'
		state3 = 'done'
		state4 = 'done'
	
				
		if form['payment_type']:
			direct_payment = form['payment_type']
			payment.append("pg.payment_type ='%s'"%(form['payment_type']))
			payment1.append("pi.payment_type ='%s'"%(form['payment_type']))
		
		else:
			direct_payment = 'credit'
		
		if payment:
			payment = 'and ('+' or '.join(payment)
			payment =  payment+')'
		else:
			payment = ''
						
		if payment1:
			payment1 = 'and ('+' or '.join(payment1)
			payment1 =  payment1+')'
		else:
			payment1 = ''
			
			
			
		if form['invoice_id'] or form['invoice_id1']:
			state1 = 'approved'
			for ids1 in form['invoice_id']:
				invoice.append("pi.id = %s"%(ids1))
				
				
			for ids1 in form['invoice_id1']:
				invoice.append("pi.id = %s"%(ids1))	
			
					
		if invoice:
			invoice = 'and ('+' or '.join(invoice)
			invoice =  invoice+')'
		else:
			invoice = ''	
			
		if form['voucher_id']:
			
			for ids1 in form['voucher_id']:
				voucher.append("pi.id = %s"%(ids1))	
				state3 = 'approved'	
		if voucher:
			voucher = 'and ('+' or '.join(voucher)
			voucher =  voucher+')'
		else:
			
			voucher = ''	
		
	
		if (not invoice) and (not voucher) and (not direct):
			
			state1= 'approved'
			state3= 'approved'
			state4= 'approved'
		

				   	
		self.cr.execute('''
		
			  SELECT

				distinct pi.id AS pi_id,
				res.name AS su_name,
				pi.name AS inv_no,
			
				pi.grn_type AS grn_type,
				pi.po_so_name AS po_so_name,
				pi.po_so_date AS po_so_date,
				
				pi.po_id AS po_id,
				pi.po_id AS po_id,
				pi.service_order_id AS so_id,
				pi.remarks AS remark,
				to_char(pi.invoice_date,'dd/mm/yyyy') AS inv_date,
				pi.sup_invoice_no AS sup_inv_no,
				to_char(pi.sup_invoice_date,'dd/mm/yyyy') AS sup_inv_date,
				pi.sup_invoice_date AS sup_inv_date1,
				po.name AS po_no,
				to_char(po.date_order,'dd/mm/yyyy') AS po_date,
				so.name AS so_no,
				to_char(so.date,'dd/mm/yyyy') AS so_date,
				pm.name AS payment,
				pg.payment_type as payment_type,
				pi.net_amt as total		   

				FROM  kg_purchase_invoice pi		  
				JOIN res_partner res ON (res.id=pi.supplier_id)
				left join res_city city on(city.id=res.city)
				left join res_country_state state on(state.id=res.state_id)
				left join purchase_order po on(po.id=pi.po_id)
				left join kg_service_order so on(so.id=pi.service_order_id)
				left join kg_payment_master pm on(pm.id=pi.payment_id)

				left join kg_po_grn pg on (pg.id = (select grn_id from purchase_invoice_grn_ids where invoice_id = pi.id limit 1))
				where pi.state=%s and pi.approved_date::date >=%s and pi.approved_date::date <=%s  ''' + payment + invoice + '''
				
				
				union
				
			SELECT

				distinct pi.id AS pi_id,
				res.name AS su_name,
				pi.name AS inv_no,
				
				pi.grn_type AS grn_type,
				pi.po_so_name AS po_so_name,
				pi.po_so_date AS po_so_date,
				pi.po_id AS po_id,
				pi.po_id AS po_id,
				pi.service_order_id AS so_id,
				pi.remarks AS remark,
				to_char(pi.invoice_date,'dd/mm/yyyy') AS inv_date,
				pi.sup_invoice_no AS sup_inv_no,
				to_char(pi.sup_invoice_date,'dd/mm/yyyy') AS sup_inv_date,
				pi.sup_invoice_date AS sup_inv_date1,
				po.name AS po_no,
				to_char(po.date_order,'dd/mm/yyyy') AS po_date,
				so.name AS so_no,
				to_char(so.date,'dd/mm/yyyy') AS so_date,
				pm.name AS payment,
				pg.payment_type as payment_type,
				pi.net_amt as total		   

				FROM  kg_purchase_invoice pi		  
				JOIN res_partner res ON (res.id=pi.supplier_id)
				left join res_city city on(city.id=res.city)
				left join res_country_state state on(state.id=res.state_id)
				left join purchase_order po on(po.id=pi.po_id)
				left join kg_service_order so on(so.id=pi.service_order_id)
				left join kg_payment_master pm on(pm.id=pi.payment_id)

				left join kg_general_grn pg on (pg.id = (select grn_id from purchase_invoice_general_grn_ids where invoice_id = pi.id limit 1))

					 where pi.state=%s and pi.approved_date::date >=%s and pi.approved_date::date <=%s  ''' + payment + invoice +  '''
			
			  union
				
			SELECT

				distinct pi.id AS pi_id,
				res.name AS su_name,
				pi.name AS inv_no,
				
				pi.grn_type AS grn_type,
				pi.po_so_name AS po_so_name,
				pi.po_so_date AS po_so_date,
				pi.po_id AS po_id,
				pi.po_id AS po_id,
				pi.service_order_id AS so_id,
				pi.remarks AS remark,
				to_char(pi.invoice_date,'dd/mm/yyyy') AS inv_date,
				pi.sup_invoice_no AS sup_inv_no,
				to_char(pi.sup_invoice_date,'dd/mm/yyyy') AS sup_inv_date,
				pi.sup_invoice_date AS sup_inv_date1,
				po.name AS po_no,
				to_char(po.date_order,'dd/mm/yyyy') AS po_date,
				so.name AS so_no,
				to_char(so.date,'dd/mm/yyyy') AS so_date,
				pm.name AS payment,
				pg.payment_type as payment_type,
				pi.net_amt as total		   

				FROM  kg_purchase_invoice pi		  
				JOIN res_partner res ON (res.id=pi.supplier_id)
				left join res_city city on(city.id=res.city)
				left join res_country_state state on(state.id=res.state_id)
				left join purchase_order po on(po.id=pi.po_id)
				left join kg_service_order so on(so.id=pi.service_order_id)
				left join kg_payment_master pm on(pm.id=pi.payment_id)

				left join kg_service_invoice pg on (pg.id = (select service_id from service_invoice_grn_ids where invoice_id = pi.id limit 1))

					 where pi.state=%s and pi.approved_date::date >=%s and pi.approved_date::date <=%s  ''' + payment + invoice + '''
			  
				union
				
				select distinct pi.id AS pi_id,
					pi.narration AS su_name,
					pi.name AS inv_no,
					
					pi.dummy_field AS grn_type,
					pi.dummy_field AS po_so_name,
					pi.dummy_field AS po_so_date,
					pi.dummy_int AS po_id,
					pi.dummy_int AS po_id,
					pi.dummy_int AS so_id,
					pi.dummy_field AS remark,
					to_char(pi.date,'dd/mm/yyyy') AS inv_date,
					pi.dummy_field AS sup_inv_no,
					pi.dummy_field AS sup_inv_date,
					pi.date AS sup_inv_date1,
					pi.dummy_field AS po_no,
					pi.dummy_field AS po_date,
					pi.dummy_field AS so_no,
					pi.dummy_field AS so_date,
					pi.dummy_field AS payment,
					pi.payment_type as payment_type,
					pi.amount as total		   

					FROM  kg_cash_voucher pi		  
					
					where pi.state=%s and pi.approved_date::date >=%s and pi.approved_date::date <=%s  ''' + payment1 + voucher + '''
				

			  
			  '''
			  
			  
			  
			  
			 ,(state1,form['date_from'],form['date_to'],state1 ,form['date_from'],form['date_to'],state1,form['date_from'],form['date_to'],state3,form['date_from'],form['date_to']))
			  
			   
		data=self.cr.dictfetchall()
		print "-------------------------data---------------------",data
		data.sort(key=lambda data: (data['sup_inv_date1']),reverse=False)
		gt_total = 0.0		
		if data:
			for item in data:
				if item['payment_type']:
					if item['grn_type'] == 'from_po_grn':
						item['po_so_no'] = item['po_so_name']
						item['po_so_date'] = item['po_so_date']
					
					elif item['grn_type'] == 'others':
						item['po_so_no'] = item['po_so_name']
						item['po_so_date'] = item['po_so_date']
					
					else:   
						item['po_so_no'] = ''
						item['po_so_date'] = ''
					gt_total += item['total']
					item['gt_tot'] = gt_total   
					data_new.append(item) 
						  
				else:
					pass	
		data = data_new			 
		return data
		
		
	def _get_filter(self, data):
		if data.get('form', False) and data['form'].get('filter', False):
			if data['form']['filter'] == 'filter_date':
				return _('Date')
			
		return _('No Filter')
		
	def _get_start_date(self, data):
		if data.get('form', False) and data['form'].get('date_from', False):
			return data['form']['date_from']
		return ''
		
	def _get_end_date(self, data):
		if data.get('form', False) and data['form'].get('date_to', False):
			return data['form']['date_to']
		return ''		  
  

report_sxw.report_sxw('report.kg.purchase.invoice.register', 'kg.purchase.invoice', 
			'addons/kg_reports/purchase/report/kg_purchase_invoice_register.rml', 
			parser=kg_purchase_invoice_register, header = False)
