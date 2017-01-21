
import time
from report import report_sxw
from reportlab.pdfbase.pdfmetrics import stringWidth
import locale
from datetime import datetime, date
import ast


class kg_so_register(report_sxw.rml_parse):
	
	_name = 'kg.so.register'
	

	def __init__(self, cr, uid, name, context=None):
		if context is None:
			context = {}
		super(kg_so_register, self).__init__(cr, uid, name, context=context)
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
		partner = []
		product = []
			
		if form['supplier']:
			for ids1 in form['supplier']:
				partner.append("so.partner_id = %s"%(ids1))
		
		if form['product_id']:
			for ids2 in form['product_id']:
				product.append("sol.product_id = %s"%(ids2))		
				

		if partner:
			partner = 'and ('+' or '.join(partner)
			partner =  partner+')'
			print "partner -------------------------->>>>", partner
		else:
			partner = ''
			
		if product:
			product = 'and ('+' or '.join(product)
			product =  product+')'
			print "product -------------------------->>>>", product
		else:
			product = ''
			
			
		if form['status'] == 'approved':
			so_state = 'approved'
		elif form['status'] == 'cancelled':
			so_state = 'cancel'
		else:
			so_state = 'approved'

		if not form['status'] or form['status'] == 'approved' or form['status'] == 'cancelled':		
			self.cr.execute('''
			
				  SELECT
				  so.id AS so_id,
				  so.name AS so_no,
				  to_char(so.date,'dd/mm/yyyy') AS so_date,
				  so.date AS date,
				  so.amount_total as total,
				  so.partner_address as address,
				  so.amount_tax as taxamt,
				  sol.id as sol_id,
				  sol.product_qty AS qty,
				  sol.pending_qty AS pending_qty,
				  sol.price_unit as rate,
				  sol.kg_discount_per as disc1,
				  sol.kg_disc_amt_per as disc2,		
				  so_ad.advance_amt as so_ad_amt,			  
				  uom.name AS uom,
				  pt.name AS pro_name,
				  res.name AS su_name,
				  res.street AS str1,
				  res.zip as zip,
				  city.name as city,
				  state.name as state,
				  brand.name as brand_name,
				  so.so_type as so_type
						  
							  
				  FROM  kg_service_order so
							  
				  JOIN res_partner res ON (res.id=so.partner_id)
				  left join res_city city on(city.id=res.city)
				  left join res_country_state state on(state.id=res.state_id)
				  left JOIN kg_service_order_line sol ON (sol.service_id=so.id)
				  left JOIN product_product prd ON (prd.id=sol.product_id)
				  left JOIN product_template pt ON (pt.id=prd.product_tmpl_id)
				  left JOIN product_uom uom ON (uom.id=sol.product_uom)
				  left JOIN kg_brand_master brand ON (sol.brand_id = brand.id)
				  left JOIN kg_supplier_advance so_ad ON (so_ad.so_id = so.id)

				  where so.state=%s and so.date >=%s and so.date <=%s '''+ product + partner + '''
				  order by so.date limit 10''',(so_state,form['date_from'],form['date_to']))
				  
		elif form['status'] == 'pending':
			self.cr.execute('''
			
				  SELECT
				  so.id AS so_id,
				  so.name AS so_no,
				  to_char(so.date,'dd/mm/yyyy') AS so_date,
				  so.date AS date,
				  so.amount_total as total,
				  so.partner_address as address,
				  so.amount_tax as taxamt,
				  sol.id as sol_id,
				  sol.product_qty AS qty,
				  sol.pending_qty AS pending_qty,
				  sol.price_unit as rate,
				  sol.kg_discount_per as disc1,
				  sol.kg_disc_amt_per as disc2,		
				  so_ad.advance_amt as so_ad_amt,			  
				  uom.name AS uom,
				  pt.name AS pro_name,
				  res.name AS su_name,
				  res.street AS str1,
				  res.zip as zip,
				  city.name as city,
				  state.name as state,
				  brand.name as brand_name,
				  so.so_type as so_type
						  
							  
				  FROM  kg_service_order so
							  
				  JOIN res_partner res ON (res.id=so.partner_id)
				  left join res_city city on(city.id=res.city)
				  left join res_country_state state on(state.id=res.state_id)
				  left JOIN kg_service_order_line sol ON (sol.service_id=so.id)
				  left JOIN product_product prd ON (prd.id=sol.product_id)
				  left JOIN product_template pt ON (pt.id=prd.product_tmpl_id)
				  left JOIN product_uom uom ON (uom.id=sol.product_uom)
				  left JOIN kg_brand_master brand ON (sol.brand_id = brand.id)
				  left JOIN kg_supplier_advance so_ad ON (so_ad.so_id = so.id)

				  where so.state='approved' and sol.pending_qty > 0 and so.date >=%s and so.date <=%s '''+ product + partner + '''
				  order by so.date limit 10''',(form['date_from'],form['date_to']))
			   
		data=self.cr.dictfetchall()
		#print "data ::::::::::::::=====>>>>", data
		
		if data:									
			new_data = []
			count = 0
			ad_amt = 0
			gr_total = 0
			gr_order_qty_total = 0
			gr_rec_qty_total = 0
			gr_pending_qty_total = 0
			gr_rate_total = 0
			sol_obj = self.pool.get('kg.service.order.line')
			for pos1, item1 in enumerate(data):
				
				if item1['so_type'] == 'amc':
					item1['type'] = 'AMC'
			
				elif item1['so_type'] == 'service':
					item1['type'] = 'Service'
					
				elif item1['so_type'] == 'labor':
					item1['type'] = 'Labor Only'
				
				if item1['disc1'] == None:
					
					item1['disc1'] = 0.00
				else:
					item1['disc1'] = item1['disc1']
					
				if item1['disc2'] == None:
					item1['disc2'] = 0.00
				else:
					item1['disc2'] = item1['disc2']							
				delete_items = []
				so_no = item1['so_no']
				print "po_no,,,,,,,,,,,,,,",so_no
				order_id = item1['so_id']
				so_date = item1['date']
				print "so_date,,,,,,,,,,,,,,,",so_date
				fmt = '%Y-%m-%d'
				from_date = so_date    
				to_date = date.today()
				to_date = str(to_date)
				d1 = datetime.strptime(from_date, fmt)
				d2 = datetime.strptime(to_date, fmt)
				daysDiff = str((d2-d1).days)
				print "daysDiff--------------->>", daysDiff
				item1['pending_days'] = daysDiff
				sol_rec = sol_obj.browse(self.cr, self.uid,item1['sol_id'])
				taxes = sol_rec.taxes_id
				if taxes and len(taxes) !=1:				
					tax_name = []
					for tax in taxes:
						name = tax.name
						tax_name.append(name)
						a = (', '.join('"' + item + '"' for item in tax_name))
						tax = [ item.encode('ascii') for item in ast.literal_eval(a) ]
						po_tax = ', '.join(tax)
						item1['tax'] = po_tax
				else:
					if taxes:						
						so_tax = taxes[0].name
						item1['tax'] = so_tax
				gr_total += item1['total']
				ad_amt = item1['so_ad_amt']
				gr_order_qty_total += item1['qty']
				received_qty = item1['qty'] - item1['pending_qty']
				gr_rec_qty_total += received_qty
				gr_pending_qty_total += item1['pending_qty']
				gr_rate_total += item1['rate']
				print "gr_total.........................>>>",gr_total
				
				for pos2, item2 in enumerate(data):
					if not pos1 == pos2:
						if item1['so_id'] == item2['so_id'] and item1['su_name'] == item2['su_name']:												
							if count == 0:
								new_data.append(item1)
								print "new_data.............",new_data
								count = count + 1
							item2_2 = item2
							item2_2['su_name'] = ''
							item2_2['str1'] = ''
							item2_2['zip'] = ''
							item2_2['city'] = ''
							item2_2['state'] = ''
							item2_2['so_no'] = ''
							item2_2['so_date'] = ''
							item2_2['address']=''
							item2_2['so_ad_amt']=0
							item2_2['total']=0
							item2_2['pending_days']=0
							new_data.append(item2_2)
							print "new_data2.............>",new_data
							delete_items.append(item2)
					
					else:
						print "Few PO have one line"
			item1['so_ad_amt'] = ad_amt			
			item1['gr_total'] = gr_total
			item1['gr_ordqty_total'] = gr_order_qty_total
			item1['gr_recqty_total'] = gr_rec_qty_total
			item1['gr_pendqty_total'] = gr_pending_qty_total
			item1['gr_ratetotal'] = gr_rate_total
			
		else:
			print "No Data"
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
  

report_sxw.report_sxw('report.kg.so.register', 'kg.service.order', 
			'addons/kg_reports/purchase/report/kg_so_register.rml', 
			parser=kg_so_register, header = False)
