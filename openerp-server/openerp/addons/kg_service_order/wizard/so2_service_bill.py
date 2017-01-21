from openerp.osv import fields, osv
from openerp.tools.translate import _

class so2_service_bill(osv.osv_memory):

	def _get_journal(self, cr, uid, context=None):
		res = self._get_journal_id(cr, uid, context=context)
		if res:
			return res[0][0]
		return False

	def _get_journal_id(self, cr, uid, context=None):
		if context is None:
			context = {}

		model = context.get('active_model')
		print "model ------------->>>", model
		if not model or 'kg.service.order' not in model:
			return []

		model_pool = self.pool.get(model)
		journal_obj = self.pool.get('account.journal')
		res_ids = context and context.get('active_ids', [])
		vals = []
		so_obj = model_pool.browse(cr, uid, res_ids, context=context)

		for so in so_obj:
			if not so.service_order_line:
				continue
			#src_usage = pick.move_lines[0].location_id.usage
			#dest_usage = pick.move_lines[0].location_dest_id.usage
			#type = pick.type
			journal_type = 'purchase'			
			value = journal_obj.search(cr, uid, [('type', '=',journal_type )])
			for jr_type in journal_obj.browse(cr, uid, value, context=context):
				t1 = jr_type.id,jr_type.name
				if t1 not in vals:
					vals.append(t1)
		return vals

	_name = "so2.service.bill"
	_description = "SO Bill Creation"

	_columns = {
	
		'journal_id': fields.selection(_get_journal_id, 'Destination Journal',required=True),
		'invoice_date': fields.date('Invoice Date'),
		'sup_inv_no': fields.char('Supplier Invoice No', size=128),
		'sup_inv_date': fields.date('Supplier Invoice Date'),
	}

	_defaults = {
		'journal_id' : _get_journal,
	}

	def view_init(self, cr, uid, fields_list, context=None):
		if context is None:
			context = {}
		res = super(so2_service_bill, self).view_init(cr, uid, fields_list, context=context)
		so_obj = self.pool.get('kg.service.order')
		count = 0
		active_ids = context.get('active_ids',[])
		print "active_ids ==============>>>>",active_ids
		return res

	def open_invoice(self, cr, uid, ids, context=None):
		wizard_record = self.browse(cr, uid, ids[0])
		print "wizard_record....................>>>>>",wizard_record
		active_ids = context.get('active_ids',[])
		print "active_ids ==============>>>>",active_ids
		ser_order_obj = self.pool.get('kg.service.order')
		ser_order_rec = self.pool.get('kg.service.order').browse(cr, uid, active_ids[0])
		ser_inv_obj = self.pool.get('kg.service.invoice')
		ser_inv_line_obj = self.pool.get('kg.service.invoice.line')
		ser_inv_obj.create(cr,uid,
			{
			
			'name': self.pool.get('ir.sequence').get(cr, uid, 'kg.service.invoice'),
			'partner_id':ser_order_rec.partner_id.id,
			'partner_address':ser_order_rec.partner_address,
			'service_order_id':ser_order_rec.id,
			'service_order_date':ser_order_rec.date,
			'supplier_invoice_no':wizard_record.sup_inv_no,
			'supplier_invoice_date':wizard_record.sup_inv_date,
			'payment_mode':ser_order_rec.payment_mode.id,
			'payment_type':ser_order_rec.payment_type,
			'dep_name':ser_order_rec.dep_name.id,
			'amount_untaxed': ser_order_rec.amount_untaxed,
			'amount_tax': ser_order_rec.amount_tax,
			'amount_total': ser_order_rec.amount_total,
			'discount' : ser_order_rec.discount,
			'other_charge': ser_order_rec.other_charge,
			'dep_project': ser_order_rec.origin_project.id,#####
			'state':'approved'
			
			
			})
			
		ser_inv_ids = ser_inv_obj.search(cr, uid, [('service_order_id','=',ser_order_rec.id)])
		
		ser_order_obj.write(cr,uid,ser_order_rec.id, {'state': 'approved','button_flag':False,'so_bill':'t'})
		
		ser_inv_rec = ser_inv_obj.browse(cr, uid, ser_inv_ids[0])
		for line_ids in ser_order_rec.service_order_line:
			ser_inv_line_obj.create(cr,uid,
			{
			
			'service_id':ser_inv_rec.id,
			'product_id':line_ids.product_id.id,
			'product_uom':line_ids.product_uom.id,
			'product_qty':line_ids.product_qty,
			'price_unit':line_ids.price_unit,
			'kg_discount_per':line_ids.kg_discount_per,
			'kg_discount':line_ids.kg_discount,
			'taxes_id':[(6, 0, [x.id for x in line_ids.taxes_id])],
			
			
			})
			
		return True
	

so2_service_bill()

