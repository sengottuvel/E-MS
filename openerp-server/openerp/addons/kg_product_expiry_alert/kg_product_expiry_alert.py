from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import re
import datetime 
import dateutil.relativedelta
from operator import itemgetter
from itertools import groupby

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)
from datetime import timedelta 

class kg_product_expiry_alert(osv.osv):

	_name = "kg.product.expiry.alert"
	_description = "Product Expiry Alert"
	
	
	_columns = {
		'created_by':fields.many2one('res.users','Created By'),
		'line_ids' : fields.one2many('kg.product.expiry.alert.line','pro_id','GRN',readonly=True),
		'date':fields.date('Date'),
	}
	
	def load_product(self, cr, uid, ids,context=None):
		expiry_ids = self.browse(cr, uid, ids[0])
		pi_obj = self.pool.get('kg.product.expiry.alert.line')
		line_ids = []	
		if expiry_ids.line_ids:
			line_ids = map(lambda x:x.id,expiry_ids.line_ids)
			pi_obj.unlink(cr,uid,line_ids)
		ex_date = datetime.datetime.now() + timedelta(days=15)			
		fut_date=ex_date.strftime('%Y-%m-%d')
		cr.execute("""select grn_no,product_id,product_uom,price_unit,expiry_date,product_qty,pending_qty,batch_no,po_uom from stock_production_lot where pending_qty >0 and product_id in (select id from product_product where flag_expiry_alert='t') and expiry_date >= '%s' and expiry_date <'%s' order by expiry_date"""%(expiry_ids.date,fut_date))
		data = cr.dictfetchall();
		for i in data:
			pi_obj.create(cr,uid,
							{

							'pro_id':expiry_ids.id,
							'product_id':i['product_id'],
							'uom_id':i['po_uom'],
							'qty':i['pending_qty'],
							'ex_date':i['expiry_date'],
							'batch':i['batch_no'],
							'price':i['price_unit'],
							'grn_no':i['grn_no'],
							})
		return data
	
	
	def mail(self, cr, uid, ids=0,context=None):		
		cr.execute("""select grn_no,product_id,product_uom,price_unit,expiry_date,product_qty,pending_qty,batch_no,po_uom from stock_production_lot where pending_qty >0 and product_id in (select id from product_product where flag_expiry_alert='t') and expiry_date >= (select current_date) and expiry_date <(select current_date+15) order by expiry_date""")	
		data1 = cr.fetchall();
		if data1:
			cr.execute("""select expiry_alert_mail('Expiry Alert')""")
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
		

	_defaults = {
		'date': lambda * a: time.strftime('%Y-%m-%d'),
		'created_by': lambda obj, cr, uid, context: uid,
		
	}
	
		
	
		
		
kg_product_expiry_alert()

class kg_product_expiry_alert_line(osv.osv):
	
	_name = "kg.product.expiry.alert.line"
	
	_columns = {
	'pro_id':fields.many2one('kg.product.expiry.alert','GRN'),
	'product_id':fields.many2one('product.product','Product'),
	'uom_id':fields.many2one('product.uom','UOM'),
	'qty':fields.float('Qty'),
	'ex_date':fields.date('Expiry Date'),
	'batch': fields.char('Batch'),
	'price':fields.float('Price'),
	'grn_no':fields.char('GRN Number'),
	}
	
	
kg_product_expiry_alert_line()

