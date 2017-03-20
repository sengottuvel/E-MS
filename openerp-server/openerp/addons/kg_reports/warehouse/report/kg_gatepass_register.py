from kg_purchase_order import JasperDataParser
from jasper_reports import jasper_report
import pooler
from datetime import date
from datetime import datetime
from datetime import timedelta
import base64
import netsvc
from osv import osv, fields
from tools.translate import _
from osv.orm import browse_record, browse_null
import os
import re
from HTMLParser import HTMLParser

class kg_gatepass_register(JasperDataParser.JasperDataParser):
	def __init__(self, cr, uid, ids, data, context):
		super(kg_gatepass_register, self).__init__(cr, uid, ids, data, context)

	def generate_data_source(self, cr, uid, ids, data, context):
		return 'records'

	def generate_ids(self, cr, uid, ids, data, context):
		return {}

	def generate_properties(self, cr, uid, ids, data, context):
		return {}
		
	def generate_parameters(self, cr, uid, ids, data, context):
		val={}
	
		
		user_id = self.pool.get('res.users').browse(self.cr,self.uid,uid)
		user_rec = user_id.login
		
		val['from_date']=''
		val['to_date']=''
		val['status'] = ''
		val['out_type'] = ''
		val['product_name'] = 'All'
		val['supplier_name'] = 'All'
		val['department_name'] = 'All'
	

	
		frm_rec = data['form']['date_from']
		user_name = user_rec
		current_time = datetime.now()
		ist_time = current_time + timedelta(minutes = 330)
		crt_time = ist_time.strftime('%d/%m/%Y %H:%M:%S')	
		t_rec = data['form']['date_to']
		to_date =  t_rec.encode('utf-8')
		from_date =  frm_rec.encode('utf-8')
		t_d1 = datetime.strptime(to_date,'%Y-%m-%d')
		t_d2 = datetime.strftime(t_d1, '%Y-%m-%d')
		t_d5 = datetime.strftime(t_d1, '%d/%m/%Y')
		t_d3 = datetime.strptime(from_date,'%Y-%m-%d')
		t_d4 = datetime.strftime(t_d3, '%Y-%m-%d')
		t_d6 = datetime.strftime(t_d3, '%d/%m/%Y')
		
		
		
		
		if data['form']['product']:
			product_id = data['form']['product']
			product_rec = self.pool.get('product.product').browse(self.cr,self.uid,product_id[0])
			val['product'] = product_rec.id
			val['product_name'] = product_rec.name
		
		
		if data['form']['supplier']:
			supplier_id = data['form']['supplier']
			sup_rec = self.pool.get('res.partner').browse(self.cr,self.uid,supplier_id[0])
			val['supplier_id'] = sup_rec.id
			val['supplier_name'] = sup_rec.name	
			
			
		if data['form']['dep_id']:
			dep_id = data['form']['dep_id']
			dep_rec = self.pool.get('kg.depmaster').browse(self.cr,self.uid,dep_id[0])
			val['department'] = dep_rec.id
			val['department_name'] = dep_rec.dep_name

		if data['form']['status']:
			if data['form']['status'] == 'confirmed':
				val['status'] = 'confirmed'
				val['status_name'] = 'Confirmed'
			if data['form']['status'] == 'done':
				val['status'] = 'done'
				val['status_name'] = 'Delivered'
			if data['form']['status'] == 'close':
				val['status'] = 'close'
				val['status_name'] = 'Closed'
			if data['form']['status'] == 'cancel':
				val['status'] = 'cancel'
				val['status_name'] = 'Cancelled'
			if data['form']['status'] == 'pending':
				val['status'] = 'pending'
				val['status_name'] = 'Pending'
			if data['form']['status'] == 'open':
				val['status'] = 'open'
				val['status_name'] = 'Open'
		else:
			val['status_name'] = 'All'
			
		if data['form']['out_type']:
			if data['form']['out_type'] == 'g-return':
				val['out_type'] = 'g-return'
				val['out_type'] = 'G-Return'
			if data['form']['out_type'] == 'service':
				val['out_type'] = 'service'
				val['out_type'] = 'Service'
			if data['form']['out_type'] == 'replacement':
				val['out_type'] = 'replacement'
				val['out_type'] = 'Replacement'
			if data['form']['out_type'] == 'rejection':
				val['out_type'] = 'rejection'
				val['out_type'] = 'Rejection'
			if data['form']['out_type'] == 'transfer':
				val['out_type'] = 'transfer'
				val['out_type'] = 'Transfer'
		else:
			val['out_type'] = ''
		
		val['m_from_date'] = t_d4
		val['m_to_date'] = t_d2
		val['p_from_date'] = t_d6
		val['p_to_date'] = t_d5
		
		val['user_name'] = user_name
		
		
		return val


	def generate_records(self, cr, uid, ids, data, context):
		pool= pooler.get_pool(cr.dbname)
		return {}

jasper_report.report_jasper('report.jasper_kg_gatepass_register', 'res.users', parser=kg_gatepass_register)
