import time
from report import report_sxw
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime, date
import locale
import ast


class grn_register_report(report_sxw.rml_parse):
	
	_name = 'report.grn.register.report'
	_inherit='stock.picking'   

	def __init__(self, cr, uid, name, context=None):
		if context is None:
			context = {}
		super(grn_register_report, self).__init__(cr, uid, name, context=context)
		self.query = ""
		self.period_sql = ""
		self.localcontext.update( {
			'time': time,
			'get_filter': self._get_filter,
			'get_start_date':self._get_start_date,
			'get_end_date':self._get_end_date,
			'get_data':self.get_data,
			'locale':locale,
		})
		self.context = context
		
	def get_data(self,form):
		res = {}
		
		where_sql = []
		po_partner = []
		gen_partner = []
		inward_type = []
		product=[]
		
		if form['supplier']:
			for ids1 in form['supplier']:
				po_partner.append("po_grn.supplier_id = %s"%(ids1))
				
		if form['supplier']:
			for ids1 in form['supplier']:
				gen_partner.append("gen_grn.supplier_id = %s"%(ids1))
		
		if form['product']:
			for ids2 in form['product']:
				product.append("grn_line.product_id = %s"%(ids2))
		
		
		if form['inward_type']:
			inward = form['inward_type']
			
		
			inward_type.append("grn_line.inward_type = '%s'"%(inward[0]))		
				
		
		if inward_type:
			inward_type = ' and '+' or '.join(inward_type)
			
		else:
			inward_type = ''
		
				
		if where_sql:
			where_sql = ' and '+' or '.join(where_sql)
		else:
			where_sql=''
			
		if po_partner:
			po_partner = 'and ('+' or '.join(po_partner)
			po_partner =  po_partner+')'
		else:
			po_partner = ''
			
		if gen_partner:
			gen_partner = 'and ('+' or '.join(gen_partner)
			gen_partner =  gen_partner+')'
		else:
			gen_partner = ''
			
		if product:
			product = 'and ('+' or '.join(product)
			product =  product+')'
		else:
			product = ''
		
		if form['status'] == 'approved':
			grn_state = 'done'
		elif form['status'] == 'cancelled':
			grn_state = 'cancel'
		elif form['status'] == 'inv':
			grn_state = 'inv',''
		else:
			grn_state = 'done','confirmed','inv'
		
		self.cr.execute('''
		
			  (SELECT 
			  po_grn.id AS grn_id,
			  to_char(po_grn.grn_date,'dd/mm/yyyy') AS grn_date,
			  po_grn.grn_date AS grn_datee,
			  po_grn.name AS grn_number,
			  po_grn.po_so_remark AS remarks,
			  po_grn.amount_total As grn_total,
			  po_grn.dc_no AS dc_no,
			  to_char(po_grn.dc_date,'dd/mm/yyyy') AS dc_date,			   
			  po_grn.created_by AS created_by,
			  part.name AS part_name,
			  part.street as str1,
			  ct.name as city,
			  part.zip as zip,
			  st.name as state,
			  coun.name as country,
			  prd.name_template AS product_name,
			  grn_line.po_grn_qty AS qty,
			  uom.name AS uom,	  
			  grn_line.id AS line_id,
			  grn_line.price_unit As cost_price,
			  grn_line.kg_discount_per as discount,
			  inw.name AS inward_type,
			  po_grn.amount_total as grn_total
			  
			  FROM  kg_po_grn po_grn

			  left JOIN res_partner part ON (part.id=po_grn.supplier_id)
			  left join res_country_state st on(st.id=part.state_id)
			  left join res_city ct on(ct.id=part.city)
			  left join res_country as coun on(coun.id=part.country_id)
			  left JOIN po_grn_line grn_line ON (grn_line.po_grn_id=po_grn.id)
			  left JOIN kg_inwardmaster inw ON (inw.id = grn_line.inward_type)
			  left JOIN product_uom uom ON (uom.id=grn_line.uom_id)
			  left JOIN product_product prd ON (prd.id=grn_line.product_id)
			  
			  where po_grn.type = %s and po_grn.state in %s and po_grn.grn_date >=%s and po_grn.grn_date <=%s'''+ po_partner + product + inward_type +'''
			  order by po_grn.name)
			   
			   UNION
			   
			   
			   (SELECT 
				  gen_grn.id AS grn_id,
				  to_char(gen_grn.grn_date,'dd/mm/yyyy') AS grn_date,
				  gen_grn.grn_date AS grn_datee,
				  gen_grn.name AS grn_number,
				  gen_grn.remark AS remarks,
				  gen_grn.amount_total As grn_total,
				  gen_grn.dc_no AS dc_no,
				  to_char(gen_grn.dc_date,'dd/mm/yyyy') AS dc_date,			   
				  gen_grn.created_by AS created_by,
				  part.name AS part_name,
				  part.street as str1,
				  ct.name as city,
				  part.zip as zip,
				  st.name as state,
				  coun.name as country,
				  prd.name_template AS product_name,
				  grn_line.grn_qty AS qty,
				  uom.name AS uom, 
				  grn_line.id AS line_id,
				  grn_line.price_unit As cost_price,
				  grn_line.kg_discount_per as discount,
				  inw.name AS inward_type,
				  gen_grn.amount_total as grn_total
				  
				  
				  FROM  kg_general_grn gen_grn

				  left JOIN res_partner part ON (part.id=gen_grn.supplier_id)
				  left join res_country_state st on(st.id=part.state_id)
				  left join res_city ct on(ct.id=part.city)
				  left join res_country as coun on(coun.id=part.country_id)
				  left JOIN kg_general_grn_line grn_line ON (grn_line.grn_id=gen_grn.id)
				  left JOIN kg_inwardmaster inw ON (inw.id = grn_line.inward_type)
				  left JOIN product_uom uom ON (uom.id=grn_line.uom_id)
				  left JOIN product_product prd ON (prd.id=grn_line.product_id)
				  

				  where gen_grn.type = %s and gen_grn.state in %s and gen_grn.grn_date >=%s and gen_grn.grn_date <=%s'''+ gen_partner + product + inward_type +'''
				  order by gen_grn.name)
			   
	
			   
			   ''',('in', grn_state, form['date_from'],form['date_to'],'in', grn_state, form['date_from'],form['date_to']))
		
		data=self.cr.dictfetchall()
		
		data.sort(key=lambda data: data['grn_number'])
		# GRN NO and Supplier should be blank if a GRN have more than one line
		new_data = []
		count = 0
		total_value = 0.0
		line_value = 0.0
		for pos1, item in enumerate(data):
			delete_items = []
			
			if item['grn_total'] != '':
				total_value += item['grn_total']
			item['total'] = total_value
			item['line_total'] = item['qty'] * item ['cost_price']
			line_value += item['line_total']
			item['grand_total'] = line_value
			grn_date = item['grn_datee']
			fmt = '%Y-%m-%d'
			from_date = grn_date    
			to_date = date.today()
			to_date = str(to_date)
			d1 = datetime.strptime(from_date, fmt)
			d2 = datetime.strptime(to_date, fmt)
			daysDiff = str((d2-d1).days)
			item['pending_days'] = daysDiff
			self.cr.execute(""" select taxes_id from po_grn_tax where order_id = %s """ %(item['line_id']))
			po_tax_data = self.cr.dictfetchall()
			
			
			self.cr.execute(""" select taxes_id from po_gen_grn_tax where order_id = %s """ %(item['line_id']))
			gen_tax_data = self.cr.dictfetchall()
			
			
			if po_tax_data:
				if len(po_tax_data) !=1:				
					tax_name = []
					for tax in po_tax_data:
						tax_rec = self.pool.get('account.tax').browse(self.cr, self.uid, tax['taxes_id'])
						name = tax_rec.name
						tax_name.append(name)
						tax = (''.join('' + item + '\n' for item in tax_name))
						po_tax = ''.join(tax)
						item['tax'] = po_tax
				else:
					taxes = po_tax_data[0]
					if taxes:
						tax_rec = self.pool.get('account.tax').browse(self.cr, self.uid, taxes['taxes_id'])	
						po_tax = tax_rec.name
						item['tax'] = po_tax
			
			if gen_tax_data:
				if len(gen_tax_data) !=1:				
					tax_name = []
					for tax in gen_tax_data:
						tax_rec = self.pool.get('account.tax').browse(self.cr, self.uid, tax['taxes_id'])
						name = tax_rec.name
						tax_name.append(name)
						tax = (''.join('' + item + '\n' for item in tax_name))
						po_tax = ''.join(tax)
						item['tax'] = po_tax
				else:
					taxes = gen_tax_data[0]
					if taxes:
						tax_rec = self.pool.get('account.tax').browse(self.cr, self.uid, taxes['taxes_id'])	
						po_tax = tax_rec.name
						item['tax'] = po_tax
					
			po_grn_id = self.pool.get('kg.po.grn').search(self.cr, self.uid, [('id','=',item['grn_id'])])
			
			if po_grn_id:
			
				po_grn_rec = self.pool.get('kg.po.grn').browse(self.cr, self.uid, po_grn_id[0])
				
				
				if po_grn_rec:
					item['po_no'] = po_grn_rec.order_no
					item['po_date'] = po_grn_rec.order_date
					
					order_no =po_grn_rec.order_no
					if po_grn_rec.so_id.gp_id:
						item['gate_no'] = po_grn_rec.so_id.gp_id.name 
						item['gate_date'] = po_grn_rec.so_id.gp_id.date
						
					elif order_no[0] == 'G':
						item['gate_no'] = po_grn_rec.order_no
						item['gate_date'] = po_grn_rec.order_date	
					else: 
						item['gate_no'] = ''
						item['gate_date'] = ''
					
			for pos2, item2 in enumerate(data):
				if not pos1 == pos2:
					if item['grn_id'] == item2['grn_id'] and item['part_name'] == item2['part_name']:
						
						
						
												
						if count == 0:
							new_data.append(item)
							count = count + 1
						item2_2 = item2
						
						item2_2['pending_days'] = 0
						
						new_data.append(item2_2)
						delete_items.append(item2)
				else:
					print "Few GRN have one line"
			
					
					
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
  

report_sxw.report_sxw('report.grn.register.report', 'stock.picking', 
			'addons/kg_reports/warehouse/report/grn_register_report.rml', 
			parser=grn_register_report, header = False)
