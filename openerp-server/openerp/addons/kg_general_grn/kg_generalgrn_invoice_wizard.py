# -*- coding: utf-8 -*-
##############################################################################
#
#	OpenERP, Open Source Management Solution
#	Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU Affero General Public License as
#	published by the Free Software Foundation, either version 3 of the
#	License, or (at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU Affero General Public License for more details.
#
#	You should have received a copy of the GNU Affero General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv

from openerp.tools.translate import _

class kg_generalgrn_invoice_wizard(osv.osv_memory):
	
	_name = "kg.generalgrn.invoice.wizard"
	
	
	
	def _get_journal(self, cr, uid, context=None):
		res = self._get_journal_id(cr, uid, context=context)
		if res:
			return res[0][0]
		return False

	def _get_journal_id(self, cr, uid, context=None):
		if context is None:
			context = {}

		model = context.get('active_model')
		print "model.................",model
		if not model or 'kg.general.grn' not in model:
			return []

		model_pool = self.pool.get(model)
		
		print "model_pool...............",model_pool
		journal_obj = self.pool.get('account.journal')
		res_ids = context and context.get('active_ids', [])
		vals = []
		browse_picking = model_pool.browse(cr, uid, res_ids, context=context)

		for pick in browse_picking:
			if not pick.grn_line:
				continue
			src_usage = 'supplier'
			type = pick.type
			if type == 'in' and src_usage == 'supplier':
				journal_type = 'purchase'
			elif type == 'in' and src_usage == 'customer':
				journal_type = 'sale_refund'
			else:
				journal_type = 'sale'

			value = journal_obj.search(cr, uid, [('type', '=',journal_type )])
			for jr_type in journal_obj.browse(cr, uid, value, context=context):
				t1 = jr_type.id,jr_type.name
				if t1 not in vals:
					vals.append(t1)
		return vals
	


	def _get_picking_order(self, cr, uid, context=None):
		if context is None:
			context = {}
		print "context.....................",context
		model = context.get('active_model')
		active_id = context.get('active_id')
		pick_rec = self.pool.get('kg.general.grn').browse(cr,uid,active_id)
		if pick_rec.amount_total and pick_rec.type == 'in':
			res = pick_rec.amount_total
		else:
			res = 0
		return res
		
	
	_columns = {
	    
	    'journal_id': fields.selection(_get_journal_id, 'Destination Journal',required=True),
		'sup_inv_date': fields.date('Supplier Invoice date',required=True),
		'sup_inv_no': fields.char('Supplier Invoice No',char=128, required=True),
		'invoice_date': fields.date('Invoiced date',readonly=True),
		'supp_bill_amt':fields.float('Supplier Bill Amount',required=True),
		'grn_total_amt': fields.float('GRN Amount')
	}	
	
	_defaults = {
	
	'invoice_date':fields.date.context_today,
	'journal_id' : _get_journal,
	'grn_total_amt':_get_picking_order,
	
	}

	def onchange_supp_bill_amt(self,cr,uid,ids,supp_bill_amt,grn_total_amt,context=None):
		value = {'supp_bill_amt': ''}
		if supp_bill_amt != grn_total_amt:
			if grn_total_amt > supp_bill_amt:
				amt = grn_total_amt - supp_bill_amt
				raise osv.except_osv(_('Warning!'),_('GRN amount and supplier bill amount are not same, supplier bill amount is lesser than grn amt with difference amount %s Rs. !!' %(amt)))
			elif grn_total_amt < supp_bill_amt:
				amt = supp_bill_amt - grn_total_amt
				raise osv.except_osv(_('Warning!'),_('GRN amount and supplier bill amount are not same, supplier bill amount is higher than grn amt with difference amount %s Rs. !!' %(amt)))
		else:
			value = {'supp_bill_amt': supp_bill_amt}
		return value
	
	def open_invoice(self, cr, uid, ids, context=None):
		print "open_invoice FROM KGGGGGGGGGGGGG", ids
		if context is None:
			context = {}
		invoice_ids = []
		data_pool = self.pool.get('ir.model.data')
		res = self.create_invoice(cr, uid, ids, context=context)
		invoice_ids += res.values()
		inv_type = context.get('inv_type', False)
		action_model = False
		action = {}
		if not invoice_ids:
			raise osv.except_osv(_('Error!'), _('Please create Invoices.'))
		if inv_type == "out_invoice":
			action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree1")
		elif inv_type == "in_invoice":
			action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree2")
		elif inv_type == "out_refund":
			action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree3")
		elif inv_type == "in_refund":
			action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree4")
		if action_model:
			action_pool = self.pool.get(action_model)
			action = action_pool.read(cr, uid, action_id, context=context)
			action['domain'] = "[('id','in', ["+','.join(map(str,invoice_ids))+"])]"
		return action
		
	def create_invoice(self, cr, uid, ids, context=None):
		print "create_invoice FROM KGGGGGGGGGGGG", ids
		if context is None:
			context = {}
		picking_pool = self.pool.get('kg.general.grn')
		onshipdata_obj = self.read(cr, uid, ids, ['journal_id', 'group', 'invoice_date','sup_inv_date','sup_inv_no'])
		if context.get('new_picking', False):
			onshipdata_obj['id'] = onshipdata_obj.new_picking
			onshipdata_obj[ids] = onshipdata_obj.new_picking
		context['date_inv'] = onshipdata_obj[0]['invoice_date']
		context['sup_inv_no'] = onshipdata_obj[0]['sup_inv_no']
		context['sup_inv_date'] = onshipdata_obj[0]['sup_inv_date']
		
		active_ids = context.get('active_ids', [])
		active_picking = picking_pool.browse(cr, uid, context.get('active_id',False), context=context)
		print "active_picking ----------------------------->>>>>", active_picking
		inv_type = picking_pool._get_invoice_type(active_picking)
		context['inv_type'] = inv_type
		if isinstance(onshipdata_obj[0]['journal_id'], tuple):
			onshipdata_obj[0]['journal_id'] = onshipdata_obj[0]['journal_id'][0]
		res = picking_pool.action_invoice_create(cr, uid, active_ids,
			  journal_id = onshipdata_obj[0]['journal_id'],
			  type = inv_type,
			  context=context)
		active_picking.write({'state': 'inv','invoice_flag':False})
		return res

kg_generalgrn_invoice_wizard()

