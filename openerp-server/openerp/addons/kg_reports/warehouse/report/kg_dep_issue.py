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

class kg_dep_issue(JasperDataParser.JasperDataParser):
	def __init__(self, cr, uid, ids, data, context):
		super(kg_dep_issue, self).__init__(cr, uid, ids, data, context)

	def generate_data_source(self, cr, uid, ids, data, context):
		return 'records'

	def generate_ids(self, cr, uid, ids, data, context):
		return {}

	def generate_properties(self, cr, uid, ids, data, context):
		return {}
		
	def generate_parameters(self, cr, uid, ids, data, context):
		val={}
	
		user_obj = self.pool.get('res.users').search(self.cr, self.uid, [('id','=',uid)])
		user_id = self.pool.get('res.users').browse(self.cr,self.uid,user_obj[0])
		user_rec = user_id.login
		
		val['from_date']=''
		val['to_date']=''
		val['dep_id']=''
		val['product']=''
		val['t_date']=''
		val['account_id']=0
		val['company_name']=1
		val['company_add']=''
		frm_rec = data['form']['from_date']
		#~ dep_rec = data['form']['dep_id']
		#~ pro_rec = data['form']['product']
		#~ state_rec = data['form']['status']
		#~ user_name = user_rec
		current_time = datetime.now()
		ist_time = current_time + timedelta(minutes = 330)
		crt_time = ist_time.strftime('%d/%m/%Y %H:%M:%S')	
		t_rec = data['form']['to_date']
		to_date =  t_rec.encode('utf-8')
		t_d1 = datetime.strptime(to_date,'%Y-%m-%d')
		t_d2 = datetime.strftime(t_d1, '%d/%m/%Y')
		
		#~ company_id = data['form']['company_id']
		#~ company_rec = self.pool.get('res.company').browse(self.cr,self.uid,company_id[0])
		#~ company_name = company_rec.name
		#~ partner_obj = self.pool.get('res.partner').search(self.cr, self.uid, [('id','=',company_rec.partner_id.id)])
		#~ partner_rec = self.pool.get('res.partner').browse(self.cr,self.uid,partner_obj[0])
		#~ partner_st = partner_rec.street
		#~ partner_st2 = partner_rec.street2
		#~ partner_zip = partner_rec.zip
		#~ partner_add = partner_st+""+partner_st2+""+partner_zip
		
	#	account_rec = data['form']['account_id']
		
		val['from_date'] = frm_rec
		val['to_date'] = t_rec
		val['wiz_id'] = data['form']['id']
		#~ val['dep_id'] = dep_rec
		#~ val['product'] = pro_rec
		#~ if state_rec == 'approved':
			#~ val['status']= 'done'
		#~ elif state_rec == 'cancelled':
			#~ val['status'] = 'cancel'
		#~ else:
			#~ val['status'] = 'done' 
		#~ val['account_id'] = 2
		#~ val['user_name'] = user_name
		#~ val['current_time'] = crt_time
		#~ val['t_date'] = t_d2
		#~ val['company_name'] = company_name
		#~ val['company_add'] = partner_add
		
		return val


	def generate_records(self, cr, uid, ids, data, context):
		pool= pooler.get_pool(cr.dbname)
		return {}

jasper_report.report_jasper('report.jasper_kg_dep_issue_report', 'kg.department.issue', parser=kg_dep_issue)
