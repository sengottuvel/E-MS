import math
import re
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from itertools import groupby
import logging
import openerp.addons.decimal_precision as dp
logger = logging.getLogger('server')


class kg_indent2_po(osv.osv):
	
	_name = "purchase.order"
	_inherit = "purchase.order"

	_columns = {
	
	'kg_poindent_lines':fields.many2many('purchase.requisition.line','kg_poindent_po_line' , 'po_order_id', 'piline_id','POIndent Lines',
			domain="[('pending_qty','>','0'), '&',('line_state','=','process'), '&',('draft_flag','=', False)]", 
			readonly=True, states={'draft': [('readonly', False)]}),
			
		}

	def update_poline(self,cr,uid,ids,context=False):
		logger.info('[KG OpenERP] Class: kg_indent2_po, Method: update_poline called...')
		"""
		Purchase order line should be created from purchase indent while click on update to PO Line button
		"""
		poindent_line_obj = self.pool.get('purchase.requisition.line')
		po_line_obj = self.pool.get('purchase.order.line')
		prod_obj = self.pool.get('product.product')
		order_line = []			   
		res={}
		rec  = self.browse(cr,uid,ids[0])
		order_line = []
		res['order_line'] = []
		res['po_flag'] = True
		obj =  self.browse(cr,uid,ids[0])
		if obj.order_line:
			order_line = map(lambda x:x.id,obj.order_line)
			
			for line in obj.order_line:
				pi_line = line.pi_line_id
				pi_line.write({'line_state' : 'process','draft_flag':False})			
			
			del_sql = """ delete from purchase_order_line where order_id=%s """ %(ids[0])
			cr.execute(del_sql)
			
			
			
		if obj.kg_poindent_lines:
			poindent_line_ids = map(lambda x:x.id,obj.kg_poindent_lines)
			poindent_line_browse = poindent_line_obj.browse(cr,uid,poindent_line_ids)
			poindent_line_browse = sorted(poindent_line_browse, key=lambda k: k.product_id.id)
			groups = []
			for key, group in groupby(poindent_line_browse, lambda x: x.product_id.id):
				for key,group in groupby(group,lambda x: x.brand_id.id):
					groups.append(map(lambda r:r,group))
			for key,group in enumerate(groups):
				qty = sum(map(lambda x:float(x.pending_qty),group)) #TODO: qty
				poindent_line_ids = map(lambda x:x.id,group)
				if len(poindent_line_ids) > 1:
					flag = True
					pi_qty = group[0].pending_qty
				else:
					flag = False
					pi_qty = 0.0
				prod_browse = group[0].product_id
				brand_id = group[0].brand_id.id			
				po_pi_id = group[0].id
				po_uom = group[0].product_uom_id.id
				remark = group[0].note
				pro_price = """ select price from ch_supplier_details where supplier_id=%s and partner_id = %s""" %(prod_browse.id,rec.partner_id.id)
				cr.execute(pro_price)
				data = cr.dictfetchall()
				if data:
					price_val = data[0]['price']
					to_price = price_val * qty
				else:
					price_val = 0.0
					to_price = 0.0
				vals = {
				
				'order_id': obj.id,
				'product_id':prod_browse.id,
				'brand_id':brand_id,
				'product_uom':po_uom,
				'product_qty':qty,
				'pending_qty':qty,
				'pi_qty':qty,
				'group_qty':pi_qty,
				'pi_line_id':po_pi_id,
				'tot_price' : to_price,
				'price_unit' : price_val,
				'group_flag': flag,
				'name':'PO',
				'line_flag':True,
				'uom_conversation_factor':prod_browse.uom_conversation_factor,
				
				}
				
				
				poindent_line_obj.write(cr,uid,po_pi_id,{'line_state' : 'process','draft_flag':True})
				if ids:
					line_id = self.pool.get('purchase.order.line').create(cr,uid,vals)
					for wo in group[0].line_ids:
						self.pool.get('ch.purchase.wo').create(cr,uid,{'header_id':line_id,'wo_id':wo.wo_id,'w_order_id':wo.w_order_id.id,'qty':wo.qty})
						
			if ids:
				if obj.order_line:
					order_line = map(lambda x:x.id,obj.order_line)
					for line_id in order_line:
						self.write(cr,uid,ids,{'order_line':[]})
		self.write(cr,uid,ids,res)
		
		return True
		
	def update_product_pending_qty(self,cr,uid,ids,line,context=None):
			
		print "update_product_pending_qty called @@@@@@@@@@@@@@@@@@@@", line
		po_rec = self.browse(cr, uid, ids[0])
		line_obj = self.pool.get('purchase.order.line')
		pi_line_obj = self.pool.get('purchase.requisition.line')
		product_obj = self.pool.get('product.product')
		cr.execute(""" select piline_id from kg_poindent_po_line where po_order_id = %s """ %(str(ids[0])))
		data = cr.dictfetchall()
		val = [d['piline_id'] for d in data if 'piline_id' in d] 
		product_id = line.product_id.id
		product_record = product_obj.browse(cr, uid, product_id)
		list_line = pi_line_obj.search(cr,uid,[('id', 'in', val), ('product_id', '=', product_id)],context=context)
		pi_line_id=line.pi_line_id
		po_qty = line.product_qty
		for i in list_line:
			bro_record = pi_line_obj.browse(cr, uid,i)
			orig_pi_qty = bro_record.pending_qty
			po_used_qty = po_qty
			if po_used_qty <= orig_pi_qty:
				pi_pending_qty =  orig_pi_qty - po_used_qty
				sql = """ update purchase_requisition_line set pending_qty=%s where id = %s"""%(pi_pending_qty,bro_record.id)
				cr.execute(sql)
				pi_line_obj.write(cr,uid, bro_record.id, {'line_state' : 'noprocess'})
				break
			
			else:
				pending_qty = bro_record.pending_qty
				remain_qty = po_used_qty - pending_qty
				pi_pending_qty = 0.0
				po_qty = remain_qty
				sql = """ update purchase_requisition_line set pending_qty=%s where id = %s"""%(pi_pending_qty,bro_record.id)
				cr.execute(sql)
				pi_line_obj.write(cr,uid, bro_record.id, {'line_state' : 'noprocess'})
				if remain_qty < 0:
					break
		
		return True
		
			
	
		
kg_indent2_po()
