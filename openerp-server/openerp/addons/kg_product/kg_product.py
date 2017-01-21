import math
import re
from _common import rounding
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
from operator import itemgetter
from itertools import groupby
a = datetime.now()
dt_time = a.strftime('%m/%d/%Y %H:%M:%S')
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

UOM_CONVERSATION = [
    ('one_dimension','One Dimension'),('two_dimension','Two Dimension')
]


class kg_product(osv.osv):
	
	_name = "product.product"
	_inherit = "product.product"
	_columns = {
	
		'capital': fields.boolean('Capital Goods'),
		'abc': fields.boolean('ABC Analysis'),
		'po_uom_coeff': fields.float('PO Coeff', required=True, help="One Purchase Unit of Measure = Value of(PO Coeff)UOM"),
		'product_type': fields.selection([('raw_material','Raw Materials'),('consu', 'Consumables'),('manufacturing','Manufacturing'),('spares_pump','Spares - Pump'),('spares_motor','Spares - Motor'),('semi_finshed','Semi Finshed'),('insulator','Insulator'),('spares_packing','Spares - Packing'),('spares_winding','Spares - Winding'),('service_items','Service Items')], 'Product Type',required=True),
		'approve_date': fields.datetime('Approved Date', readonly=True),
		'app_user_id': fields.many2one('res.users', 'Approved By', readonly=True),
		'confirm_date': fields.datetime('Confirmed Date', readonly=True),
		'conf_user_id': fields.many2one('res.users', 'Confirmed By', readonly=True),
		'reject_date': fields.datetime('Rejected Date', readonly=True),
		'rej_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'cancel_date': fields.datetime('Cancelled Date', readonly=True),
		'cancel_user_id': fields.many2one('res.users', 'Cancelled By', readonly=True),
		'od': fields.float('OD'),
		'breadth': fields.float('Breadth'),
		'length': fields.float('Length'),
		'thickness': fields.float('Thickness'),
		'weight': fields.float('Weight'),
		'po_uom_in_kgs': fields.float('PO UOM in kgs'),
		'uom_conversation_factor': fields.selection(UOM_CONVERSATION,'UOM Conversation Factor',required=False),
		'coupling_type': fields.selection([('rss','RSS'),('sw','SW')],'Coupling Type'),
		'service_factor': fields.float('Service Factor'),
		'power_kw': fields.float('Power in KW'),
		'speed_in_rpm': fields.float('Speed In RPM'),
		'max_bore': fields.float('MAX Bore'),
		'coupling_size': fields.float('Coupling Size'),
		'spacer_length': fields.float('Spacer Length'),
		'mechanical_type': fields.char('Type'),
		'operating_condition': fields.char('Operating Condition'),
		'face_combination': fields.char('Face Combination'),
		'api_plan': fields.char('API Plan'),
		'gland_placement': fields.char('Gland Placement'),
		'gland_plate': fields.selection([('w_gland_plate','With Gland Plate'),('wo_gland_plate','Without Gland Plate')],'Gland Plate'),
		'sleeve_dia': fields.char('Sleeve dia(MM)'),
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'stockable': fields.selection([('yes','Yes'),('no','No')],'Stockable Item',required=True),
		
	}
	
	_defaults = {
	
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'kg.segment', context=c),
		'po_uom_coeff' : 1.0,
		'crt_date':fields.datetime.now,	
		'user_id': lambda obj, cr, uid, context: uid,
		'uom_conversation_factor': 'one_dimension',
		'stockable': 'yes',
		
	}
	
	def entry_confirm(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'confirm','conf_user_id': uid, 'confirm_date': dt_time})   
		return True

	def entry_approve(self,cr,uid,ids,context=None):
		rec = self.browse(cr, uid, ids[0])
		access_obj = self.pool.get('kg.accessories.master')
		ch_access_obj = self.pool.get('ch.kg.accessories.master')
		if rec.is_accessories == True:
			ac_id = access_obj.search(cr,uid,[('product_id','=',rec.id)])
			if ac_id:
				old_obj = access_obj.search(cr,uid,[('product_id','=',rec.id),('state','!=','reject')])
				if old_obj:
					old_rec = access_obj.browse(cr,uid,old_obj[0])
					access_obj.write(cr,uid,old_rec.id,{'name':rec.name})
				old_rej_obj = access_obj.search(cr,uid,[('product_id','=',rec.id),('state','=','reject')])
				if old_rej_obj:
					old_rej_rec = access_obj.browse(cr,uid,old_rej_obj[0])
					access_id = access_obj.create(cr,uid,{'access_type':'new',
														  'name': rec.name,
														  'entry_mode': 'auto',
														  'product_id': rec.id,
														 })
					if access_id:
						ch_access_obj.create(cr,uid,{'header_id': access_id,
													 'product_id': rec.id,
													 'qty': 1,
													 'uom_id': rec.uom_po_id.id,
													 'uom_conversation_factor':rec.uom_conversation_factor,
													 'entry_mode': 'auto',
													})			
			else:
				access_id = access_obj.create(cr,uid,{'access_type':'new',
													  'name': rec.name,
													  'entry_mode': 'auto',
													  'product_id': rec.id,
													 })
				if access_id:
					ch_access_obj.create(cr,uid,{'header_id': access_id,
												 'product_id': rec.id,
												 'qty': 1,
												 'uom_id': rec.uom_po_id.id,
												 'uom_conversation_factor':rec.uom_conversation_factor,
												 'entry_mode': 'auto',
												})			  
		self.write(cr, uid, ids, {'state': 'approved','app_user_id': uid, 'approve_date': dt_time})
		return True
		
	def entry_cancel(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.cancel_remark:
			self.write(cr, uid, ids, {'state': 'cancel','cancel_user_id': uid, 'cancel_date': dt_time})
		else:
			raise osv.except_osv(_('Cancel remark is must !!'),
				_('Enter the remarks in Cancel remarks field !!'))
		return True
		
	def entry_draft(self,cr,uid,ids,context=None):
		self.write(cr, uid, ids, {'state': 'draft'})
		return True
		
	def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.remark:
			self.write(cr, uid, ids, {'state': 'reject','rej_user_id': uid, 'reject_date': dt_time})
		else:
			raise osv.except_osv(_('Rejection remark is must !!'),
				_('Enter rejection remark in remark field !!'))
		return True
		
	def _name_validate(self, cr, uid,ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		res = True
					   
		return res 
		
	_constraints = [
		
		(_name_validate, 'product name must be unique !!', ['name']),
	   
	]	   
	
	def write(self,cr,uid,ids,vals,context={}):
		if 'tolerance_applicable' in vals:
			if vals['tolerance_applicable'] == True:
				if 'tolerance_plus' in vals:
					if vals['tolerance_plus'] <= 0.00:
						raise osv.except_osv(_('Check Tolerance(+) Value !!'),
							_('Please enter greater than zero !!'))	
					else:
						pass
				else:
					pass
			else:
				pass
		return super(kg_product, self).write(cr, uid, ids,vals, context)
	
	
kg_product()


	

