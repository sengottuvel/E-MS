import math
import re
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
import openerp.addons.decimal_precision as dp
import netsvc
import datetime

class kg_item_ledger(osv.osv):

	_name = "kg.item.ledger"
	_description = "Item Ledger View"

	
	_columns = {
		'product_id':fields.many2one('product.product','Item Name',required=True),
		'uom_id': fields.many2one('product.uom', 'UOM', required=True),
		
		'close_ledger_line':fields.one2many('kg.close.item.ledger.line','close_ledger_id','Close Ledger Line'),
		
		
		'out_ledger_line':fields.one2many('kg.out.item.ledger.line','out_ledger_id','Out Ledger Line'),
		'out_qty':fields.integer('Issue Qty',readonly=True),
		'out_value':fields.integer('Issue Value',readonly=True),
		
		'receipt_ledger_line':fields.one2many('kg.receipt.item.ledger.line','receipt_ledger_id','Receipt Ledger Line'),
		'grn_qty':fields.integer('Receipt Qty',readonly=True),
		'grn_value':fields.integer('Receipt Value',readonly=True),
		'date':fields.date('Date'),
		
		
		'total':fields.date('Total As On',readonly=True),
		'receipt_qty':fields.integer('Receipt Qty',readonly=True),
		'issue_qty':fields.integer('Issue Qty',readonly=True),
		'closing_qty':fields.integer('Closing Qty',readonly=True),
		'closing_value':fields.float('Closing Value',readonly=True),
		'dep_name':fields.many2one('stock.location', 'Location',domain=[('usage','=','internal')],required=True)
		
		
	}
	
	_defaults = {
	
		'date':fields.date.context_today
		
	}
	
	
	def create(self, cr, uid, data, context=None):
		v_name = None 
		
		
		if data['product_id']:
			prod_uom = self.pool.get('product.template').browse(cr, uid, data['product_id'], context=context)
			data['uom_id'] = prod_uom.uom_id.id
		return super(kg_item_ledger, self).create(cr, uid, data, context)
	
	
	def onchange_product_uom(self, cr, uid, ids, product_id, uom_id, context=None):
			
		value = {'uom_id': ''}
		if product_id:		  
			prod_uom = self.pool.get('product.template').browse(cr, uid, product_id, context=context)
			value = {'uom_id':prod_uom.uom_id.id}
		return {'value': value}
		
	def item_load(self, cr, uid, ids, context=None):
		ledger_rec = self.browse(cr, uid, ids[0])
		
		
		dep_id = ledger_rec.dep_name.id
		ledger_date = "'"+ledger_rec.date+"'"
		
		
		
		#### Close Details ####
		move_obj = self.pool.get('stock.move')
		close_ledger_line_obj = self.pool.get('kg.close.item.ledger.line')
		product_id = ledger_rec.product_id.id
		last_ids = close_ledger_line_obj.search(cr, uid, [('close_ledger_id','=',ledger_rec.id)])
		if last_ids:
			for i in last_ids:
				close_ledger_line_obj.unlink(cr, uid, i, context=context)
				
				
		location_rec = self.pool.get('stock.location').browse(cr,uid,dep_id)
		
		if location_rec.location_type == 'main':
			lo_type = 'in'
		else:
			lo_type = 'out'
			
		
		close_ledger_sql = """ select  product_id as product_id, sum(product_qty) as in_qty from stock_move 
				where product_id=%s and state='done' and move_type = '%s' and date <=%s  group by product_id 
				"""%(product_id,lo_type,ledger_date)
		cr.execute(close_ledger_sql)
		ledger_close_data = cr.dictfetchall()
		
		cl_qty = 0
		cl_value = 0
		if ledger_close_data:
		
		
			for item in ledger_close_data:
				in_qty = item['in_qty']
				
				if lo_type == 'out':
				
					#picking_rec = self.pool.get('stock.picking').browse(cr, uid, item['picking_id'])
					
					ledger_close_sql = """ select src_id as src_id,product_id as product_id,sum(product_qty) as product_qty from stock_move 
							where product_id=%s and move_type='cons' and state='done' and date <=%s group by src_id,product_id """%(product_id,ledger_date)
					cr.execute(ledger_close_sql)
					out_data = cr.dictfetchall()
					src_id = 0
					cons_id = 0
					cons_qty = 0
					if out_data:
						out_qty = [d['product_qty'] for d in out_data if 'product_qty' in d]
						
						for out in out_qty:
							cons_qty += out
						
						close_qty = in_qty - cons_qty
						src_id = [s['src_id'] for s in out_data if 'src_id' in s]
					else:
						close_qty = in_qty	
						
					item['close_qty'] = close_qty
					cons_id = src_id
					
					####
					total = 0
					value=0
					qty=0
					if item['close_qty']:
						price = 0
						if out_data:
							for out in out_data:
								
								
								cons_src_id = out['src_id']
								con_qty = out['product_qty']
								
								
								
								
								
								
								out_move_id=move_obj.search(cr,uid,[('product_id','=',product_id),('move_type','=','out'),
								('id','=',cons_src_id),('state','=','done')])
								if out_move_id:
									out_move_rec=move_obj.browse(cr,uid,out_move_id[0])
									pro_name=out_move_rec.product_id.name
									close_qtty = out_move_rec.product_qty - con_qty
									out_price = close_qtty * out_move_rec.price_unit
									price += out_price
							
						else:
							move_id=move_obj.search(cr,uid,[('product_id','=',product_id),('move_type','=','out'),
							('state','=','done')])
							if move_id:
								total = 0
								value=0
								qty=0
								for j in move_id:
									move_rec=move_obj.browse(cr,uid,j)
									pro_name=move_rec.product_id.name
									move_product_qty =move_rec.product_qty
									pro_price=move_rec.price_unit
									
									
									if pro_price:
										out_price=move_product_qty * pro_price
									else:
										out_price = 0
								
									price += out_price
								
						value += price
					item['closing_value'] = value
							
					if close_qty > 0:	
						close_ledger_line_obj.create(cr,uid,
							{   
							   
								'close_ledger_id':ids[0],
								'date':ledger_date,
								
								'qty': close_qty,
								'tot_amt':item['closing_value'],
								
								
							})
						cl_qty += close_qty
						cl_value += value
						
						
				else:
					out_sql = """ select product_id,sum(product_qty) from stock_move where product_id=%s and move_type='out' and state='done' and date <=%s and location_id != 254 group by product_id """%(product_id,ledger_date)
					cr.execute(out_sql)			
					out_data = cr.dictfetchall()
					if out_data:
						out_qty = [d['sum'] for d in out_data if 'sum' in d]
						op_qty = in_qty - out_qty[0]
					else:
						op_qty = in_qty		
						
					item['close_qty'] = op_qty
					close_qty = item['close_qty']
					
					#####
					if item['close_qty']:
						spl_obj=self.pool.get('stock.production.lot')
						spl_id=spl_obj.search(cr,uid,[('product_id','=',product_id),('lot_type','=','in')])
								
						
						value=0
						qty=0
						for j in spl_id:
							spl_rec=spl_obj.browse(cr,uid,j)
							pro_name=spl_rec.product_id.name
							pend_qty=spl_rec.pending_qty
							product_qty =spl_rec.product_qty
							pro_price = spl_rec.price_unit
							if pend_qty > 0:
								pro_qty = pend_qty
								price=pro_qty*pro_price
							else:
								price = 0	
							
							
							value += price
						item['closing_value'] =value
						
						if close_qty > 0:	
							close_ledger_line_obj.create(cr,uid,
								{   
								   
									'close_ledger_id':ids[0],
									'date':ledger_date,
									
									'qty': close_qty,
									'tot_amt':item['closing_value'],
									
									
								})
							cl_qty += close_qty
							cl_value += value	
				
		#### Issue Details ####
				
				
		out_ledger_line_obj = self.pool.get('kg.out.item.ledger.line')
		product_id = ledger_rec.product_id.id
		
		
		out_last_ids = out_ledger_line_obj.search(cr, uid, [('out_ledger_id','=',ledger_rec.id)])
		if out_last_ids:
			for i in out_last_ids:
				out_ledger_line_obj.unlink(cr, uid, i, context=context)
		
		out_ledger_sql = """ select id, picking_id,name, date, product_id, product_qty, price_unit, stock_rate, state, move_type from stock_move 
				where product_id=%s and state='done' and move_type='out' and date <=%s order by date """%(product_id,ledger_date)
		cr.execute(out_ledger_sql)
		ledger_out_data = cr.dictfetchall()
		issue_qty = 0
		issue_value = 0
		if ledger_out_data:
			for item1 in ledger_out_data:
				
				picking_rec = self.pool.get('stock.picking').browse(cr, uid, item1['picking_id'])
				
				date = item1['date']
				pro_qty = item1['product_qty']
				pro_rate = item1['price_unit']
				pro_amt = pro_qty * pro_rate
				out_ledger_line_obj.create(cr,uid,
					{   
					   
						'out_ledger_id':ids[0],
						'date':date,
						'qty': pro_qty,
						'unit_price': pro_rate,
						'tot_amt':pro_amt,
						'particulars':picking_rec.name
						
					})
				issue_qty += pro_qty
				issue_value += pro_amt
				
				
					
					
		#### Receipt Details ####
		
		receipt_ledger_line_obj = self.pool.get('kg.receipt.item.ledger.line')
		product_id = ledger_rec.product_id.id
		
		rep_last_ids = receipt_ledger_line_obj.search(cr, uid, [('receipt_ledger_id','=',ledger_rec.id)])
		if rep_last_ids:
			for i in rep_last_ids:
				receipt_ledger_line_obj.unlink(cr, uid, i, context=context)
		
		receipt_ledger_sql =""" select id, picking_id,general_grn_id,po_grn_id,name, date, product_id, product_qty, price_unit, stock_rate, state, move_type from stock_move 
				where product_id=%s and state='done' and move_type='in' and date <=%s order by date """%(product_id,ledger_date)
		cr.execute(receipt_ledger_sql)
		ledger_receipt_data = cr.dictfetchall()
		
		receipt_qty = 0
		receipt_value = 0
		if ledger_receipt_data:
			for item3 in ledger_receipt_data:
				
				if item3['general_grn_id']:
					picking_rec = self.pool.get('kg.general.grn.line').browse(cr, uid, item3['general_grn_id'])
					picking_rec = picking_rec.grn_id
					grn_no = picking_rec.name
					supplier = picking_rec.supplier_id.id
				
				elif item3['po_grn_id']:
					picking_rec = self.pool.get('kg.po.grn').browse(cr, uid, item3['po_grn_id'])
					grn_no = picking_rec.name
					supplier = picking_rec.supplier_id.id
				else:	
				
					grn_no = ''
					supplier = False
				
				date = item3['date']
				pro_qty = item3['product_qty'] or 0.00
				pro_rate = item3['price_unit'] or 0.00
				pro_amt = pro_qty * pro_rate
				receipt_ledger_line_obj.create(cr,uid,
					{   
					   
						'receipt_ledger_id':ids[0],
						'date':date,
						'qty': pro_qty,
						'unit_price': pro_rate,
						'tot_amt':pro_amt,
						'particulars':grn_no,
						'supplier_id':supplier,
						
					})
				receipt_qty += pro_qty
				receipt_value += pro_amt
				
		
		self.write(cr, uid, ids, {'receipt_qty':receipt_qty})
		self.write(cr, uid, ids, {'issue_qty':issue_qty})
		self.write(cr, uid, ids, {'closing_qty':cl_qty})
		self.write(cr, uid, ids, {'total':ledger_date})
		self.write(cr, uid, ids, {'closing_value':cl_value})
		
		
		
		self.write(cr, uid, ids, {'grn_qty':receipt_qty})
		self.write(cr, uid, ids, {'grn_value':receipt_value})
		
		self.write(cr, uid, ids, {'out_qty':issue_qty})
		self.write(cr, uid, ids, {'out_value':issue_value})
		
	
		
		
					
					
				
				
		
			
		return True
		
	
	

kg_item_ledger()


class kg_close_item_ledger_line(osv.osv):

	_name = "kg.close.item.ledger.line"
	_description = "Item Ledger View Line"

	
	_columns = {
		'close_ledger_id':fields.many2one('kg.item.ledger','Ledger'),
		
		'date':fields.date('Date'),
		
		'qty':fields.float('Qty'),
		'tot_amt':fields.float('Amount (Rs)'),
	}
	

kg_close_item_ledger_line()



class kg_out_item_ledger_line(osv.osv):

	_name = "kg.out.item.ledger.line"
	_description = "Item Ledger View Line"

	
	_columns = {
		'out_ledger_id':fields.many2one('kg.item.ledger','Ledger'),
		
		'date':fields.date('Date'),
		'particulars':fields.char('Particulars'),
		'qty':fields.float('Qty'),
		'unit_price':fields.float('Rate/Qty (Rs)'),
		'tot_amt':fields.float('Amount (Rs)'),
	}
	

kg_out_item_ledger_line()


class kg_receipt_item_ledger_line(osv.osv):

	_name = "kg.receipt.item.ledger.line"
	_description = "Item Ledger View Line"

	
	_columns = {
		'receipt_ledger_id':fields.many2one('kg.item.ledger','Ledger'),
		'supplier_id':fields.many2one('res.partner','Supplier'),
	
		'date':fields.date('Date'),
		'particulars':fields.char('Particulars'),
		'qty':fields.float('Qty'),
		'unit_price':fields.float('Rate/Qty (Rs)'),
		'tot_amt':fields.float('Amount (Rs)'),
	}
	 

kg_receipt_item_ledger_line()


