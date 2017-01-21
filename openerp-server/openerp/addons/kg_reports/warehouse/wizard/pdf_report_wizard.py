import time
from lxml import etree
from osv import fields, osv
from tools.translate import _
import pooler
import logging
import netsvc
logger = logging.getLogger('server')
import datetime
from datetime import datetime
from datetime import date
today = date.today()

class wiz_standards(osv.osv_memory):
		
	_name = 'wiz.standards'
	
	
	_columns = {
	
		## Basic Info
						
		'from_date': fields.date("Start Date", required=True),
		'to_date': fields.date("End Date", required=True),
		'crt_date': fields.datetime('Creation Date', readonly=True),
		'user_id': fields.many2one('res.users', 'Created By',readonly=True),				
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'flag_footer': fields.boolean('Footer Info', helps='If False footer details should not print')
		
		## If any filter it should be many2many only. Don't use many2one filter unless it's must	
		
		
		
	}
	
	_defaults = {
		
		'from_date': time.strftime('%Y-%m-%d'),
		'to_date': time.strftime('%Y-%m-%d'),
		'crt_date': fields.datetime.now,
		'user_id': lambda obj, cr, uid, context: uid,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'wiz.standards', context=c),
		'flag_footer': True,
	}
	
	def _future_date_validation(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if  rec.to_date > str(today) or rec.from_date > str(today):
			raise osv.except_osv('Invalid Action', 'Future Dates are not allowed')  
		return True
	   
	def _start_end_date_validation(self, cr, uid, ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.from_date > rec.to_date:
			raise osv.except_osv('Invalid Action', 'Start date is greater than End date')  
		return True
		
 
	_constraints = [
	
		(_future_date_validation,'Future Dates are not allowed', ['']),
		(_start_end_date_validation, 'Start date is greater than End date', ['']),
	  ]
	
		
wiz_standards()
