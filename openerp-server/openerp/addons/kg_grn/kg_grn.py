from datetime import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
import time
from operator import itemgetter
from itertools import groupby
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
import logging
logger = logging.getLogger('server')

class kg_stock_picking(osv.osv):
        
    _inherit = "stock.picking"
    _name = "stock.picking"
    
    def _check_lineitem(self, cr, uid, ids, context=None):
        picking_rec = self.browse(cr, uid, ids[0])
        if not picking_rec.move_lines:
            return False
            
        return True
            
    
    
    _columns = {
    
    'name': fields.char('Reference', size=64, select=True, readonly=True,
                    states={'draft':[('readonly', False)]}),
    'active': fields.boolean('Active'),
    'dc_no': fields.char('DC.NO', size=128),
    'dc_date':fields.date('DC.Date'),
    'inward_type': fields.many2one('kg.inwardmaster', 'Inward Type'),
    'po_id':fields.many2one('purchase.order', 'Pending POS'),
    'state': fields.selection([
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('auto', 'Waiting'),
            ('confirmed', 'Waiting for Confirmation'),
            ('assigned', 'Waiting for Approval'),
            ('done', 'Done'),
            ('qawaiting', 'QA Waiting'),
            ('inv', 'Invoiced'),
            ], 'Status', readonly=True, select=True, track_visibility='onchange'),
            
    'stock_journal_id': fields.many2one('stock.journal','Stock Journal', invisible=True),
    'origin': fields.char('Source Document', size=64, invisible=True),
    'dep_name': fields.many2one('kg.depmaster','Dep.Name',required=True, translate=True, select=True),
    'date': fields.date('Date', required=True, readonly=True),
    'user_id' : fields.many2one('res.users', 'User', readonly=False),
    'kg_dep_indent_line':fields.many2many('kg.depindent.line', 'kg_depline_picking', 'kg_depline_id', 'stock_picking_id', 'Department Indent'),
    'grn_type': fields.selection([('frompo','From PO'),('direct','Direct')], 'GRN Type'),
    'kg_seq_id':fields.many2one('ir.sequence','Document Type',domain=[('code','=','stock.picking')],readonly=True,
                    states={'draft':[('readonly', False)]}),
    'min_date': fields.date('Scheduled Time', select=1, help="Scheduled time for the shipment to be processed"),
    'move_lines': fields.one2many('stock.move', 'picking_id', 'Internal Moves', 
        states={'draft': [('readonly', True)], 'cancel': [('readonly', True)], 'done': [('readonly', True)]}),
    'issue_by':fields.char('Issued By', size=64),
    
    
    # SubStore Consumption:
    'name': fields.char('Consumption No', size=64, select=True,readonly=True,
                    states={'draft':[('readonly', False)]}),
    'outward_type':fields.many2one('kg.outwardmaster', 'Outward Type',required=True, readonly=True,
                    states={'draft':[('readonly', False)]}),
    'cons_flag': fields.boolean('Cons Flag'),
    'grn_total':fields.float('GRN Total'),
    'creation_date':fields.datetime('Creation Date'),
    
    }
    
    _defaults = {
    
    'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
    'cons_flag': True,
    'name': '',
    'active': True,
    'creation_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    
    }
    
    
    
    
    
    def onchange_seq_id(self, cr, uid, ids, kg_seq_id,name):
        value = {'name':''}
        if kg_seq_id:
            next_seq_num = self.pool.get('ir.sequence').kg_get_id(cr, uid, kg_seq_id,'id',{'noupdate':False})
            print "next_seq_num:::::::::::", next_seq_num
            value = {'name': next_seq_num}
        return {'value': value}
    
    
    def action_assign_wkf(self, cr, uid, ids, context=None):
        logger.info('[KG OpenERP] Class: kg_stock_picking, Method: action_assign_wkf called...')
        """ Changes picking state to assigned.
        @return: True
        """
        self.write(cr, uid, ids, {'state': 'confirmed'})
        return True 
    
    
    def action_process(self, cr, uid, ids, context=None):
        
        logger.info('[KG OpenERP] Class: kg_stock_picking, Method: action_process called...')
        picking_record = self.browse(cr,uid,ids[0])
        po_id = picking_record.po_id.id
        move_obj=self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        
        if not picking_record.move_lines:
            raise osv.except_osv(
                _('No Consumption Lines'),
                _('Consumption Lines should not be Empty !!!'))
        else:
            move_ids=move_obj.search(cr, uid, [( 'picking_id','=',ids[0])])
            for i in range(len(move_ids)):
                move_record=move_obj.browse(cr, uid, move_ids[i], context=context)
                product_record = product_obj.browse(cr, uid,move_record.product_id.id)
                if move_record.po_to_stock_qty > move_record.cons_qty:
                    raise osv.except_osv(
                    _('Consumption Qty Error'),
                    _('System not allow to enter consumption qty greater than Sub Store Qty!!!'))
                else:
                    print "NO Issue"
        if context is None:
            context = {}
        context.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': len(ids) and ids[0] or False
        })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.partial.picking',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
            'nodestroy': True,
        }
    
    def action_confirm(self, cr, uid, ids, context=None):
        logger.info('[KG OpenERP] Class: kg_stock_picking, Method: action_confirm called...')
        pickings = self.browse(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'confirmed'})
        todo = []
        for picking in pickings:
            for r in picking.move_lines:
                if r.state == 'draft':
                    todo.append(r.id)
        todo = self.action_explode(cr, uid, todo, context)
        if len(todo):
            self.pool.get('stock.move').action_confirm(cr, uid, todo, context=context)
        return True
        
    def draft_force_assign(self, cr, uid, ids, *args):
        logger.info('[KG OpenERP] Class: kg_stock_picking, Method: draft_force_assign called...')
        
        wf_service = netsvc.LocalService("workflow")
        pick = self.browse(cr, uid, ids)
        if not pick[0].move_lines:
                raise osv.except_osv(_('No Item Lines!'),_('You cannot process consumption entry without Item Lines and Qty with Zero.'))
        else:
            for move in pick[0].move_lines:
                if move.product_qty == 0:
                    raise osv.except_osv(
                    _('Item Line Qty not Zero!'),
                    _('You cannot process consumption entry without Item Lines Qty with Zero.'))        
            
            wf_service.trg_validate(uid, 'stock.picking', pick[0].id,
                'button_confirm', cr)
        return True
    
    def kg_picking_cancel(self, cr, uid, ids, context=None):
        pick_rec = self.browse(cr, uid, ids[0])
    
    
    # The Below part for Sub store consumption process 
    
    
    def create(self, cr, uid, vals, context=None):
        
        if vals.has_key('user_id') and vals['user_id']:
            user_dep_name = self.pool.get('res.users').browse(cr,uid,vals['user_id'])
            if user_dep_name.dep_name:
                vals.update({'dep_name':user_dep_name.dep_name.id})
        res = super(kg_stock_picking, self).create(cr, uid,vals, context=context)
        return res
    
    def write(self, cr, uid,ids, vals, context=None):
    
        if vals.has_key('user_id') and vals['user_id']:
            user_dep_name = self.pool.get('res.users').browse(cr,uid,vals['user_id'])
            if user_dep_name.dep_name:
                vals.update({'dep_name':user_dep_name.dep_name.id})
                         
        res = super(kg_stock_picking, self).write(cr, uid, ids,vals, context)
        
        return res
        
    def kg_confirm(self, cr, uid, ids, context=None):
        
        logger.info('[KG OpenERP] Class: kg_stock_picking_in, Method: kg_confirm called...')
        
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        self.write(cr, uid, ids, {'state': 'assigned'})
        pick = self.browse(cr, uid, ids[0])
        #for pick in self.browse(cr, uid, ids, context=context):
        ids2 = [move.id for move in pick.move_lines if move.po_to_stock_qty == 0]
        if not pick.move_lines:
            raise osv.except_osv(_('Item Line Empty!'),_('You cannot process Consumption Entry without Item Line.'))
        else:           
            for move in pick.move_lines:
                product_record = product_obj.browse(cr, uid,move.product_id.id)
                if move.move_type != 'cons':
                    raise osv.except_osv(
                    _('Manual Entries Not Allow !'),
                    _('System not allow to create manual line entries. Need to remove a line and it contains product %s'%(move.product_id.name)))                                   
                if move.po_to_stock_qty > move.cons_qty:
                    raise osv.except_osv(
                    _('Consumption Qty Error !!'),
                    _('Consumption Entry Qty should not be greater than Sub Store Available Qty for Product %s' %(move.product_id.name)))
                                                
                else:
                    move.write({'state': 'assigned'})
            move_obj.unlink(cr, uid, ids2)
            return True
    
    def draft_validate(self, cr, uid, ids, context=None):
        logger.info('[KG OpenERP] Class: kg_stock_picking, Method: draft_validate called...')
        wf_service = netsvc.LocalService("workflow")
        self.draft_force_assign(cr, uid, ids)
        for pick in self.browse(cr, uid, ids, context=context):
            move_ids = [x.id for x in pick.move_lines]
            self.pool.get('stock.move').force_assign(cr, uid, move_ids)
            wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
        return self.action_process(
            cr, uid, ids, context=context)
        
    def onchange_user_id(self, cr, uid, ids, user_id, context=None):
        logger.info('[KG OpenERP] Class: kg_stock_picking, Method: onchange_user_id called...')
        value = {'dep_name': ''}
        if user_id:
            user = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
            value = {'dep_name': user.dep_name.id}
        return {'value': value}
        
    def item_load(self,cr,uid,ids,context={}):
        logger.info('[KG OpenERP] Class: kg_stock_picking, Method: item_load called...')
        stock_move_obj = self.pool.get('stock.move')
        dep_obj = self.pool.get('kg.depmaster')
        product_obj = self.pool.get('product.product')
        stock_picking_record = self.browse(cr,uid,ids[0])
        dep_id = stock_picking_record.dep_name.id
        dep_name = stock_picking_record.dep_name.dep_name
        dep_record = dep_obj.browse(cr,uid,dep_id)
        dest_location_id = dep_record.stock_location.id 
        
        picking_obj = self.pool.get('stock.picking')
        picking_id = picking_obj.search(cr, uid, [('state','=','draft'),('id','!=',stock_picking_record.id),('dep_name','=',dep_name),('type','=','internal')])
        if picking_id:
            raise osv.except_osv(
                    _('Consumption Already Created!'),
                    _('Still there are consumption which is not in done state !!!.'))
        else:
            
            if stock_picking_record.move_lines:
                raise osv.except_osv(
                        _('Consumption Already Created !'),
                        _('System not allow to create Consumption again !!!.'))
            else:
                sql_out = """ select id,product_id,product_qty,stock_uom,stock_rate,expiry_date,batch_no from stock_move where move_type='out' and state='done' 
                                and location_dest_id =%s order by product_id """    %(dest_location_id)
                cr.execute(sql_out)
                data_out = cr.dictfetchall()
                for i in data_out:
                    out_id = i['id']
                    product_id = i['product_id']
                    qty = i['product_qty']
                    stock_uom = i['stock_uom']
                    exp_date = i['expiry_date'] or ''
                    batchno = i['batch_no'] or ''
                    final_exp_date = ''
                    final_batch_no = ''
                    #### Expiry Date and Batch No #####
                    lot_obj = self.pool.get('stock.production.lot')
                    lot_in_id = lot_obj.search(cr, uid,
                             [('product_id','=',product_id),('lot_type','=','in')])
                    exp = []
                    batch = []
                    exp_data = []
                    batch_data = []
                    if lot_in_id:
                        for j in lot_in_id:
                            lot_in_rec = lot_obj.browse(cr, uid,j)
                            if lot_in_rec.expiry_date != False:
                                exp_date= lot_in_rec.expiry_date
                                exp.append(exp_date)
                            if lot_in_rec.batch_no != False:
                                batch_no = lot_in_rec.batch_no
                                batch.append(batch_no)
                            else:
                                pass
                                
                        if len(exp) !=1:
                                
                            for exp_num in range(len(exp)-1):
                                if exp[exp_num] == exp[exp_num + 1]:
                                    if exp[exp_num] in exp_data:
                                        continue
                                    else:
                                        exp_data.append(exp[exp_num])
                                else:
                                    if exp[exp_num +1] in exp_data:
                                        continue
                                    else:
                                        exp_data.append(exp[exp_num + 1])
                                        
                        else:
                            exp_data.append(exp[0])
                                
                        
                        final_exp_date = '\n'.join(exp_data)
                        
                        if len(batch) !=1:
                        
                            for batch_num in range(len(batch)-1):
                                if batch[batch_num] == batch[batch_num + 1]:
                                    if batch[batch_num] in batch_data:
                                        continue
                                    else:
                                        batch_data.append(batch[batch_num])
                                else:
                                    if batch[batch_num +1] in batch_data:
                                        continue
                                    else:
                                        batch_data.append(batch[batch_num + 1])
                        else:
                            batch_data.append(batch[0])
                        
                        final_batch_no = '\n'.join(batch_data)
                
                    price = i['stock_rate'] or 0.0
                    sql = """ select sum(product_qty),product_uom,src_id from stock_move where move_type='cons' and state='done' 
                                and location_id =%s and product_id=%s and src_id=%s
                                group by product_uom,src_id"""%(dest_location_id,product_id,out_id)
                    cr.execute(sql)
                    data = cr.dictfetchall()
                    if not data:
                        product = product_id
                        new_cons_qty = qty
                        uom = stock_uom
                        price = price
                        product_name = product_obj.browse(cr,uid,product_id)
                        name = product_name.name_template
                        if new_cons_qty > 0:
                            self.write(cr,uid,ids[0],{'state':'confirmed'})
                            stock_move_obj.create(cr,uid,
                            {
                            
                            'picking_id': ids[0],
                            'product_id': product,
                            'name':name,
                            'product_qty': 0.0,
                            'po_to_stock_qty': 0.0,
                            'cons_qty':new_cons_qty,
                            'stock_uom':uom,
                            'product_uom': uom,
                            'location_id':dep_record.stock_location.id,
                            'location_dest_id':dep_record.used_location.id,
                            'move_type': 'cons',
                            'state': 'confirmed',
                            'price_unit': price or 0.0,
                            'src_id':out_id,
                            'expiry_date':final_exp_date,
                            'batch_no':final_batch_no
                            
                            })
                        else:
                            pass
                            
                    else:
                                            
                        cons_out_id = [d['src_id'] for d in data if 'src_id' in d]
                        else_qty = [d['sum'] for d in data if 'sum' in d]
                        orig_qty = else_qty[0]
                        new_cons_qty = qty - orig_qty 
                        uom = stock_uom
                        #price = price[0] or 0.0
                        product_name = product_obj.browse(cr,uid,product_id)
                        name = product_name.name_template
                        if new_cons_qty > 0:
                            self.write(cr,uid,ids[0],{'state':'confirmed'})
                            stock_move_obj.create(cr,uid,
                                {
                                
                                'picking_id': ids[0],
                                'product_id': product_id,
                                'name':name,
                                'product_qty': 0.0,
                                'po_to_stock_qty': 0.0,
                                'cons_qty':new_cons_qty,
                                'stock_uom':uom or False,
                                'product_uom': uom or False,
                                'location_id':dep_record.stock_location.id,
                                'location_dest_id':dep_record.used_location.id,
                                'move_type': 'cons',
                                'state': 'confirmed',
                                'price_unit': price or 0.0,
                                'src_id':out_id,
                                'expiry_date':final_exp_date,
                                'batch_no':final_batch_no
                                })
                        else:
                            print "Few Qty is Zero...."
                                                
                            
        return True
        
    def unlink(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        if context is None:
            context = {}
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.state in ['done','cancel']:
                raise osv.except_osv(_('Error!'), _('You cannot sasasaremove the picking which is in %s state!')%(pick.state,))
            else:
                ids2 = [move.id for move in pick.move_lines]
                ctx = context.copy()
                ctx.update({'call_unlink':True})
                if pick.state != 'draft':
                    #Cancelling the move in order to affect Virtual stock of product
                    move_obj.action_cancel(cr, uid, ids2, ctx)
                #Removing the move
                move_obj.unlink(cr, uid, ids2, ctx)

        return super(kg_stock_picking, self).unlink(cr, uid, ids, context=context)
        
    ## GRN to PO Bill creation Part ##
    
    def action_invoice_create(self, cr, uid, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
                
        if context is None:
            context = {}

        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        partner_obj = self.pool.get('res.partner')
        po_obj = self.pool.get('purchase.order')
        pol_obj = self.pool.get('purchase.order.line')
        
        invoices_group = {}
        res = {}
        inv_type = type
        for picking in self.browse(cr, uid, ids, context=context):
            po_rec = picking.po_id
            po_obj.write(cr,uid,po_rec.id, {'bill_flag': True})         
            
            if picking.invoice_state != '2binvoiced':
                continue
            partner = self._get_partner_to_invoice(cr, uid, picking, context=context)
            if isinstance(partner, int):
                partner = partner_obj.browse(cr, uid, [partner], context=context)[0]
            if not partner:
                raise osv.except_osv(_('Error, no partner!'),
                    _('Please put a partner on the picking list if you want to generate invoice.'))

            if not inv_type:
                inv_type = self._get_invoice_type(picking)
            if group and partner.id in invoices_group:
                invoice_id = invoices_group[partner.id]
                invoice = invoice_obj.browse(cr, uid, invoice_id)
                invoice_vals_group = self._prepare_invoice_group(cr, uid, picking, partner, invoice, context=context)
                invoice_obj.write(cr, uid, [invoice_id], invoice_vals_group, context=context)
            else:
                invoice_vals = self._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
                invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
                invoices_group[partner.id] = invoice_id
            res[picking.id] = invoice_id
            for move_line in picking.move_lines:
                if move_line.state == 'cancel':
                    continue
                if move_line.scrapped:
                    # do no invoice scrapped products
                    continue
                vals = self._prepare_invoice_line(cr, uid, group, picking, move_line,
                                invoice_id, invoice_vals, context=context)
                if vals:
                    invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)
                    self._invoice_line_hook(cr, uid, move_line, invoice_line_id)
                if move_line.purchase_line_id:
                    pl_id = move_line.purchase_line_id.id
                    pol_obj.write(cr, uid, pl_id, {'line_bill': True})                  

            invoice_obj.button_compute(cr, uid, [invoice_id], context=context,
                    set_total=(inv_type in ('in_invoice', 'in_refund')))
            self.write(cr, uid, [picking.id], {
                'invoice_state': 'invoiced',
                }, context=context)
            self._invoice_hook(cr, uid, picking, invoice_id)
        self.write(cr, uid, res.keys(), {
            'invoice_state': 'invoiced',
            }, context=context)
        return res
    
    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        po_rec = picking.po_id
        val1 = po_rec.value1 or 0.0
        val2 = po_rec.value2 or 0.0
        other_ch1 = po_rec.po_expenses_type1 or False
        other_ch2 = po_rec.po_expenses_type2 or False
        sub = po_rec.amount_untaxed
        dis = po_rec.discount
        tax = po_rec.amount_tax
        total = po_rec.amount_total
        bill = po_rec.bill_type
        if isinstance(partner, int):
            partner = self.pool.get('res.partner').browse(cr, uid, partner, context=context)
        if inv_type in ('out_invoice', 'out_refund'):
            account_id = partner.property_account_receivable.id
            payment_term = partner.property_payment_term.id or False
        else:
            account_id = partner.property_account_payable.id
            payment_term = partner.property_supplier_payment_term.id or False
        comment = self._get_comment_invoice(cr, uid, picking)
        invoice_vals = {
        
            'name': self.pool.get('ir.sequence').get(cr, uid, 'account.invoice'),
            'origin': (picking.name or '') + (picking.origin and (':' + picking.origin) or ''),
            'type': inv_type,
            'account_id': account_id,
            'partner_id': partner.id,
            'comment': comment,
            'payment_term': payment_term,
            'fiscal_position': partner.property_account_position.id,
            'date_invoice': context.get('date_inv', False),
            'company_id': picking.company_id.id,
            'user_id': uid,
            'po_id':picking.po_id.id,
            'grn_id':picking.id,
            'po_expenses_type1':other_ch1,
            'po_expenses_type2':other_ch2,
            'value1':val1,
            'value2':val2,
            'state':'proforma',
            'supplier_invoice_number': context.get('sup_inv_no', False),
            'sup_inv_date': context.get('sup_inv_date', False),
            'bill_type':bill,
            'po_date':po_rec.date_order,
            'grn_date':picking.date
            
            
            
        }
        cur_id = self.get_currency_id(cr, uid, picking)
        if cur_id:
            invoice_vals['currency_id'] = cur_id
        if journal_id:
            invoice_vals['journal_id'] = journal_id
        return invoice_vals

    def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id,
        invoice_vals, context=None):
        pol_rec = move_line.purchase_line_id
        
        if group:
            name = (picking.name or '') + '-' + move_line.name
        else:
            name = move_line.name
        origin = move_line.picking_id.name or ''
        if move_line.picking_id.origin:
            origin += ':' + move_line.picking_id.origin

        if invoice_vals['type'] in ('out_invoice', 'out_refund'):
            account_id = move_line.product_id.property_account_income.id
            
            if not account_id:
                account_id = move_line.product_id.categ_id.id
                if not account_id:
                    account_id = move_line.product_id.categ_id.property_account_income_categ.id
        else:
            account_id = move_line.product_id.property_account_expense.id
            
            if not account_id:
                account_id = move_line.product_id.categ_id.id
                if not account_id:
                    account_id = move_line.product_id.categ_id.property_account_expense_categ.id
                
        if invoice_vals['fiscal_position']:
            fp_obj = self.pool.get('account.fiscal.position')
            fiscal_position = fp_obj.browse(cr, uid, invoice_vals['fiscal_position'], context=context)
            account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)
        # set UoS if it's a sale and the picking doesn't have one
        uos_id = move_line.product_uos and move_line.product_uos.id or False
        if not uos_id and invoice_vals['type'] in ('out_invoice', 'out_refund'):
            uos_id = move_line.product_uom.id

        return {
            'name': name,
            'origin': origin,
            'invoice_id': invoice_id,
            'uos_id': uos_id,
            'poline_id':move_line.purchase_line_id,
            'product_id': move_line.product_id.id,
            'account_id': account_id,
            'price_unit': self._get_price_unit_invoice(cr, uid, move_line, invoice_vals['type']),
            'discount': self._get_discount_invoice(cr, uid, move_line),
            'quantity': move_line.po_to_stock_qty or 0.00,
            'invoice_line_tax_id': [(6, 0, self._get_taxes_invoice(cr, uid, move_line, invoice_vals['type']))],
            'account_analytic_id': self._get_account_analytic_invoice(cr, uid, picking, move_line),
            'discount':pol_rec.kg_discount_per,
            'kg_disc_amt':pol_rec.kg_discount,
        }           
    
    
kg_stock_picking()


class kg_stock_picking_in(osv.osv):
    
    __name = "stock.picking"
    _inherit="stock.picking.in"
    
    
    def _check_lineitem(self, cr, uid, ids, context=None):
        for grn in self.browse(cr, uid, ids):
            if grn.grn_type == 'direct':
                tot = 0.0
                for line in grn.move_lines:
                    tot += line.product_qty
                if tot <= 0.0:
                    return False
            return True
            
    _constraints = [
        (_check_lineitem, 'You can not save an empty GRN !!',['move_lines']),
        ]
    
    
    _columns = {
    
    'name': fields.char('Reference', size=64, select=True, states={'assigned':[('readonly', True)]}),
    'dc_no': fields.char('DC.NO', size=128, required=True, states={'done':[('readonly', True)]}),
    'dc_date':fields.date('DC.Date',states={'done':[('readonly', True)]}),
    'inward_type': fields.many2one('kg.inwardmaster', 'Inward Type',required=True, readonly=True, states={'draft':[('readonly', False)]}),
    'po_id':fields.many2one('purchase.order', 'Pending POS', required=True, readonly=True, states={'draft':[('readonly', False)]},
        domain="[('state','=','approved'), '&', ('order_line.pending_qty','>','0'), '&', ('grn_flag','=',False), '&', ('partner_id','=',partner_id), '&', ('order_line.line_state','!=','cancel')]"), 
        
    'date': fields.date('GRN Date', select=True,readonly=True),
    'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced")], "Invoice Control", select=True, required=True, track_visibility='onchange',readonly=True),
    'state': fields.selection([
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('auto', 'Waiting'),
            ('confirmed', 'Waiting for Confirmation'),
            ('assigned', 'Waiting for Approval'),
            ('done', 'Done'),
            ('qawaiting', 'QA Waiting'),
            ('inv', 'Invoiced'),
            ], 'Status', readonly=True, select=True, track_visibility='onchange'),
    'partner_id': fields.many2one('res.partner', 'Partner', required=True,readonly=True, states={'draft':[('readonly', False)]}),
    'stock_journal_id': fields.many2one('stock.journal','Stock Journal', invisible=True),
    'origin': fields.char('Source Document', size=64, invisible=True),
    'grn_type': fields.selection([('frompo','From PO'),('direct','Direct')], 'GRN Type',readonly=True),
    'kg_seq_id':fields.many2one('ir.sequence','Document Type', required=True,readonly=False, states={'assigned':[('readonly', True)]} ,
            domain=[('code','=','stock.picking.in')]),
    'min_date': fields.date('Scheduled Time', select=1, help="Scheduled time for the shipment to be processed"),
    'active': fields.boolean('Active'),
    'user_id': fields.many2one('res.users', 'User'),
    'move_lines': fields.one2many('stock.move', 'picking_id', 'Internal Moves',
            states={'draft': [('readonly', True)], 'cancel': [('readonly', True)], 'done': [('readonly', True)]}),
    'grn_total':fields.float('GRN Total',readonly=True),
    'creation_date':fields.datetime('Creation Date'),
    
  
    
    }
    
    _defaults = {
    
    'date' : fields.date.context_today,
    'invoice_state' : '2binvoiced',
    'grn_type': 'frompo',
    'name': '',
    'active': True,
    'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
    'creation_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    
    }
 
    def kg_confirm_in(self, cr, uid, ids, context=None):        
        logger.info('[KG OpenERP] Class: kg_stock_picking_in, Method: kg_confirm called...')
        
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')      
        pick = self.browse(cr, uid, ids[0])
        
        if pick.name == '':
            grn_no = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.in')
            self.write(cr,uid,ids,{'name':grn_no})

        if pick.dc_date and pick.dc_date > pick.date:
            raise osv.except_osv(_('DC Date Error!'),_('DC Date Should Be Less Than GRN Date.'))            
        if not pick.move_lines:
            raise osv.except_osv(_('Item Line Empty!'),_('You cannot process GRN without Item Line.'))
        else:
            grn_tot = 0         
            for move in pick.move_lines:
                move.purchase_line_id.write({'move_line_id':move.id})
                grn_tot += move.product_qty * move.price_unit
                product_id = move.product_id.id
                product_record = product_obj.browse(cr, uid,move.product_id.id)
                
                exp = []
                exp_data = []
                batch = []
                batch_data = []
                if move.exp_line_id:
                    for exp_line in move.exp_line_id:
                        
                        move_id = move.id
                        
                        # Expiry Date #
                        expdate = exp_line.exp_date
                        exp_date = datetime.strptime(expdate, '%Y-%m-%d').strftime('%d/%m/%Y')
                        exp.append(exp_date)
                        
                        if len(exp) !=1:
                           
                            for exp_num in range(len(exp)-1):
                                if exp[exp_num] == exp[exp_num + 1]:
                                    if exp[exp_num] in exp_data:
                                        continue
                                    else:
                                        exp_data.append(exp[exp_num])
                                else:
                                    if exp[exp_num +1] in exp_data:
                                        continue
                                    else:
                                        exp_data.append(exp[exp_num + 1])
                        else:
                            exp_data.append(exp[0])
                
                        expiry_date = '\n'.join(exp_data)
                        
                        # Batch No #
                        batch_no = exp_line.batch_no
                        batch.append(batch_no)
                    
                        if len(batch) !=1:
                
                            for batch_num in range(len(batch)-1):
                                if batch[batch_num] == batch[batch_num + 1]:
                                    if batch[batch_num] in batch_data:
                                        continue
                                    else:
                                        batch_data.append(batch[batch_num])
                                else:
                                    if batch[batch_num +1] in batch_data:
                                        continue
                                    else:
                                        batch_data.append(batch[batch_num + 1])
                        else:
                            batch_data.append(batch[0])
                        
                        batch_nos = '\n'.join(batch_data)
                                
                        move_obj.write(cr,uid,move_id, {'expiry_date':expiry_date,'batch_no':batch_nos})
                
                if not move.purchase_line_id and pick.grn_type == 'frompo':
                    raise osv.except_osv(
                    _('Error ::: Extra Item Line added in GRN !'),
                    _('System not allow to add new line in GRN with Purchase Order Line !!'))               

                if move.product_qty == 0:
                    raise osv.except_osv(
                    _('Item Line Qty can not Zero!'),
                    _('You cannot process GRN with Item Line Qty Zero for Product %s.' %(move.product_id.name)))
                if move.purchase_line_id and move.po_to_stock_qty > move.po_qty:
                    raise osv.except_osv(
                    _('If GRN From PO'),
                    _('GRN Qty should not be greater than PO Pending Qty for Product %s' %(move.product_id.name)))
                
                exp_grn_qty = 0
                if product_record.expiry == True:
                    if not move.exp_line_id:
                        raise osv.except_osv(_('Warning!'), _('You should specify Expiry date and batch no for this item %s !!'%(move.product_id.name)))
                
                if product_record.expiry == True and move.exp_line_id:
                    for exp_line in move.exp_line_id:
                        
                        today = date.today()
                        if move.date > exp_line.exp_date:
                            raise osv.except_osv(
                                _('Expiry Date Should Not Be Less Than Current Date!'),
                                _('Change the product expiry date to greater than current date for Product %s' %(move.product_id.name)))
                        
                        exp_grn_qty += exp_line.product_qty
                        
                        if exp_grn_qty > move.po_to_stock_qty:
                            raise osv.except_osv(_('Please Check!'), _('Quantity that specified in Expiry Line should not exceed than GRN Quantity for %s !!' %(move.product_id.name)))
                
                uos_coeff = product_obj.read(cr, uid, product_id, ['po_uom_coeff'])
                if move.product_uom.id != product_record.uom_id.id:
                    stock_qty = move.po_to_stock_qty * uos_coeff['po_uom_coeff']
                    move.write({
                        'product_qty':stock_qty,
                        'stock_uom':product_record.uom_id.id,
                        'state': 'assigned',
                            })
                else:
                    move.write({'state': 'assigned'})
            self.write(cr, uid, ids, {'state': 'assigned', 'grn_total' : grn_tot})
            
        return True
    
    
    def action_assign_wkf(self, cr, uid, ids, context=None):
        logger.info('[KG OpenERP] Class: kg_stock_picking_in, Method: action_assign_wkf called...')
        self.write(cr, uid, ids, {'state': 'assigned'})
        return True     
    
    def action_process(self, cr, uid, ids, context=None):
        logger.info('[KG OpenERP] Class: kg_stock_picking_in, Method: action_process called...')
        picking_record = self.browse(cr,uid,ids[0])
        po_id = picking_record.po_id.id
        move_obj=self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        po_obj = self.pool.get('purchase.order')
        move_ids=move_obj.search(cr, uid, [( 'picking_id','=',ids[0])])
        po_obj.write(cr,uid,po_id, {'grn_flag':False})
                
        for i in range(len(move_ids)):
            move_record=move_obj.browse(cr, uid, move_ids[i], context=context)
            product_record = product_obj.browse(cr, uid,move_record.product_id.id)
            
            exp = []
            exp_data = []
            batch = []
            batch_data = []
            if move_record.exp_line_id:
                for exp_line in move_record.exp_line_id:
                    
                    move_id = move_record.id
                    
                    # Expiry Date #
                    expdate = exp_line.exp_date
                    exp_date = datetime.strptime(expdate, '%Y-%m-%d').strftime('%d/%m/%Y')
                    exp.append(exp_date)
                    
                    if len(exp) !=1:
                       
                        for exp_num in range(len(exp)-1):
                            if exp[exp_num] == exp[exp_num + 1]:
                                if exp[exp_num] in exp_data:
                                    continue
                                else:
                                    exp_data.append(exp[exp_num])
                            else:
                                if exp[exp_num +1] in exp_data:
                                    continue
                                else:
                                    exp_data.append(exp[exp_num + 1])
                            
                    else:
                        exp_data.append(exp[0])
                    
                    expiry_date = '\n'.join(exp_data)
                    
                    # Batch No #
                    batch_no = exp_line.batch_no
                    batch.append(batch_no)
                
                    if len(batch) !=1:
            
                        for batch_num in range(len(batch)-1):
                            if batch[batch_num] == batch[batch_num + 1]:
                                if batch[batch_num] in batch_data:
                                    continue
                                else:
                                    batch_data.append(batch[batch_num])
                            else:
                                if batch[batch_num +1] in batch_data:
                                    continue
                                else:
                                    batch_data.append(batch[batch_num + 1])
                    else:
                        batch_data.append(batch[0])
                    
                    batch_nos = '\n'.join(batch_data)
                            
                    move_obj.write(cr,uid,move_id, {'expiry_date':expiry_date,'batch_no':batch_nos})
            
            if not move_record.purchase_line_id and picking_record.grn_type == 'frompo':
                    raise osv.except_osv(
                    _('Error ::: Extra Item Line added in GRN !'),
                    _('System not allow to add new line in GRN with Purchase Order Line !!'))               
            
            if move_record.purchase_line_id and move_record.po_to_stock_qty > move_record.po_qty:
                raise osv.except_osv(
                _('If GRN From PO'),
                _('GRN Qty should not be greater than PO Pending Qty.!!!'))
                
            exp_grn_qty = 0
            if product_record.expiry == True and move_record.exp_line_id:
                for exp_line in move_record.exp_line_id:
                    
                    today = date.today()
                    if move_record.date > exp_line.exp_date:
                        raise osv.except_osv(
                            _('Expiry Date Should Not Be Less Than Current Date!'),
                            _('Change the product expiry date to greater than current date for Product %s' %(move_record.product_id.name)))
                    
                    exp_grn_qty += exp_line.product_qty
                    
                    if exp_grn_qty > move_record.po_to_stock_qty:
                        raise osv.except_osv(_('Please Check!'), _('Quantity that specified in Expiry Line should not exceed than GRN Quantity for %s !!' %(move_record.product_id.name)))
            else:
                print "NO Issue"
        
        if context is None:
            context = {}
        context.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': len(ids) and ids[0] or False
        })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.partial.picking',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
            'nodestroy': True,
        }
        
    def action_confirm(self, cr, uid, ids, context=None):
        logger.info('[KG OpenERP] Class: kg_stock_picking_in, Method: action_confirm called...')
        pickings = self.browse(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'confirmed'})
        todo = []
        for picking in pickings:
            for r in picking.move_lines:
                if r.state == 'draft':
                    todo.append(r.id)
        todo = self.action_explode(cr, uid, todo, context)
        if len(todo):
            self.pool.get('stock.move').action_confirm(cr, uid, todo, context=context)
        return True
    
        
    def draft_picking(self, cr, uid, ids,context=None):
        logger.info('[KG OpenERP] Class: kg_stock_picking_in, Method: draft_picking called...')
        self.write(cr,uid,ids,{'state':'draft'})
        return True
    
    def _prepare_order_line_move(self, cr, uid, po_order, order_line, picking_id, context=None):
        logger.info('[KG OpenERP] Class: kg_stock_picking_in, Method: _prepare_order_line_move called...')
        print "order_line.price_subtotal / order_line.product_qty,---------->>", order_line.price_subtotal / order_line.product_qty,
        
        return {
            'name': order_line.product_id.name or '/',
            'product_id': order_line.product_id.id,
            'product_qty': order_line.pending_qty,
            'po_qty' : order_line.pending_qty,
            'po_to_stock_qty': order_line.pending_qty,
            'product_uom': order_line.product_uom.id,
            'product_uos': order_line.product_uom.id,
            'location_id': po_order.partner_id.property_stock_supplier.id,
            'location_dest_id': po_order.location_id.id,
            'picking_id': picking_id,
            'partner_id': po_order.dest_address_id.id or po_order.partner_id.id,
            'move_dest_id': order_line.move_dest_id.id,
            'state': 'confirmed',
            'type':'in',
            'move_type': 'in',
            'purchase_line_id': order_line.id,
            'company_id': po_order.company_id.id,
            'price_unit': order_line.price_unit,
            'expiry_flag':order_line.product_id.expiry,
            'pi_id':order_line.pi_line_id.id,
            'tax_id': [(6, 0, [x.id for x in order_line.taxes_id])],
            'kg_discount_per':order_line.kg_discount_per,
            'kg_discount': order_line.kg_discount
        }
        
    def update_potogrn(self,cr,uid,ids,picking_id=False,context={}):
        logger.info('[KG OpenERP] Class: kg_stock_picking_in, Method: update_potogrn called...')
        po_id = False
        obj = self.browse(cr,uid,ids[0])
        po_obj=self.pool.get('purchase.order')
        picking_obj=self.pool.get('stock.picking')
        picking_po_id = picking_obj.browse(cr,uid,obj.po_id.id)
        po_order = obj.po_id
        pol_obj = self.pool.get('purchase.order.line')
        po_obj.write(cr,uid,po_order.id, {'grn_flag': True})
            
        self.pool.get('stock.picking').write(cr,uid,ids,
        {
        
        'origin': po_order.name + ((po_order.origin and (':' + po_order.origin)) or ''),
        'invoice_state': '2binvoiced',
        'type': 'in',
        'purchase_id': po_order.id,
        'company_id': po_order.company_id.id,
        'state' : 'confirmed',
        'move_lines' : [],      
        
        })
        picking_id = obj.id
        todo_moves = []
        stock_move = self.pool.get('stock.move')
        wf_service = netsvc.LocalService("workflow")
        order_lines=po_order.order_line
        
        for order_line in order_lines:
            if order_line.pending_qty > 0 and order_line.line_state != 'cancel':
                move = stock_move.create(cr, uid, self._prepare_order_line_move(cr, uid, po_order, order_line, picking_id, context=context))
                if order_line.move_dest_id:
                    order_line.move_dest_id.write({'location_id': po_order.location_id.id})
                todo_moves.append(move)
            else:
                print "NO Qty or Cancel"

        wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
        return [picking_id]
        
    def view_purchase_order(self, cr, uid, ids, context=None):
        logger.info('[KG OpenERP] Class: kg_stock_picking_in, Method: view_purchase_order called...')       
        mod_obj = self.pool.get('ir.model.data')
        for pick in self.browse(cr, uid, ids, context=context):
            po_id = pick.po_id.id
        action_model, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'purchase', 'purchase_form_action'))
        action = self.pool.get(action_model).read(cr, uid, action_id, context=context)
        ctx = eval(action['context'])
        ctx.update({
            'search_default_purchase_id': po_id
        })
        form_view_ids = [view_id for view_id, view in action['views'] if view == 'form']
        view_id = form_view_ids and form_view_ids[0] or False
        action.update({
            'views': [],
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': po_id
        })
        action.update({
            'context': ctx,
        })
        return action


    def print_grn(self, cr, uid, ids, context=None):        
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'stock.picking', ids[0], 'send_rfq', cr)
        datas = {
                 'model': 'stock.picking',
                 'ids': ids,
                 'form': self.read(cr, uid, ids[0], context=context),
        }
        return {'type': 'ir.actions.report.xml', 'report_name': 'grn.print', 'datas': datas, 'nodestroy': True,'name': 'GRN'}
    
kg_stock_picking_in()

class kg_dep_issue(osv.osv):
    
    __name = "stock.picking"
    _inherit="stock.picking.out"
    
    
    def _check_line(self, cr, uid, ids, context=None):
        logger.info('[KG ERP] Class: kg_purchase_indent, Method: _check_line called...')
        for out in self.browse(cr,uid,ids):
            if out.kg_dep_indent_line==[]:
                tot = 0.0
                for line in out.move_lines:
                    tot += line.product_qty
                if tot <= 0.0:          
                    return False
                if not line.depindent_line_id:
                    return False
            return True
            
    _constraints = [
        (_check_line, 'You can not save an empty Issue and with out Department Indent Line !!',['move_lines']),
        ]
    
    
    _columns = {
    
    'name': fields.char('Dep.Issue NO', size=64, select=True, readonly=False,
                    states={'assigned':[('readonly', True)]}),
    'dep_name': fields.many2one('kg.depmaster','Dep.Name',required=True, translate=True, select=True, readonly=True, states={'draft': [('readonly', False)]}),
    'date': fields.date('Date', required=True, readonly=True),
    'active': fields.boolean('Active'),
    'kg_dep_indent_line':fields.many2many('kg.depindent.line', 'kg_depline_picking', 'kg_depline_id', 'stock_picking_id', 'Department Indent', 
        domain="[('indent_id.state','=','approved'), '&', ('indent_id.main_store','=',False),'&', ('indent_id.dep_name','=',dep_name),'&', ('issue_pending_qty','>','0'),'&', ('pi_cancel' ,'!=', 'True')]", 
            readonly=True, states={'draft': [('readonly', False)]}),
    'state': fields.selection([
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('auto', 'Waiting'),
            ('confirmed', 'Waiting for Confirmation'),
            ('assigned', 'Waiting for Approval'),
            ('done', 'Done'),
            ('qawaiting', 'QA Waiting'),
            ], 'Status', readonly=True, select=True, track_visibility='onchange'),
    'stock_journal_id': fields.many2one('stock.journal','Stock Journal', invisible=True),
    'origin': fields.char('Source Document', size=64, invisible=True),
    'user_id' : fields.many2one('res.users', 'User', readonly=False),
    'kg_seq_id':fields.many2one('ir.sequence','Document Type',domain=[('code','=','stock.picking.out')],
            readonly=False, states={'assigned':[('readonly', True)]}),
    
    'min_date': fields.date('Scheduled Time', select=1, help="Scheduled time for the shipment to be processed"),
    'outward_type':fields.many2one('kg.outwardmaster', 'Outward Type',required=True, readonly=True,
                    states={'draft':[('readonly', False)]}),
   
    'move_lines': fields.one2many('stock.move', 'picking_id', 'Internal Moves',
            states={'draft': [('readonly', True)], 'cancel': [('readonly', True)], 'done': [('readonly', True)],'assigned': [('readonly', True)]}),
    
    'issue_by':fields.char('Issued By', size=64),
    
    }
    
    _defaults = {
    
    'active' : True,
    'date' : fields.date.context_today,
    'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
    'name': '',

    
    }
    
    def onchange_seq_id(self, cr, uid, ids, kg_seq_id,name):
        print "kgggggggggggggggggg --  onchange_seq_id called"      
        value = {'name':''}
        if kg_seq_id:
            next_seq_num = self.pool.get('ir.sequence').kg_get_id(cr, uid, kg_seq_id,'id',{'noupdate':False})
            print "next_seq_num:::::::::::", next_seq_num
            value = {'name': next_seq_num}
        return {'value': value}
        
    
    def onchange_user_id(self, cr, uid, ids, user_id, context=None):
        logger.info('[KG OpenERP] Class: kg_dep_issue, Method: onchange_user_id called...')
        value = {'dep_name': ''}
        if user_id:
            user = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
            value = {'dep_name': user.dep_name.id}
        return {'value': value}
        
    def update_issue(self,cr,uid,ids,context=False,):
        logger.info('[KG OpenERP] Class: kg_dep_issue, Method: update_issue called...')
        
        depindent_line_obj = self.pool.get('kg.depindent.line')
        move_obj = self.pool.get('stock.move')
        prod_obj = self.pool.get('product.product')
        line_ids = []              
        res={}
        line_ids = []
        res['move_lines'] = []
        obj =  self.browse(cr,uid,ids[0])
        if obj.move_lines:
            move_lines = map(lambda x:x.id,obj.move_lines)
            move_obj.unlink(cr,uid,move_lines)
        issue_dep_id = obj.dep_name.id
        obj.write({'state': 'confirmed'})
        if obj.kg_dep_indent_line:
            depindent_line_ids = map(lambda x:x.id,obj.kg_dep_indent_line)
            depindent_line_browse = depindent_line_obj.browse(cr,uid,depindent_line_ids)
            
            depindent_line_browse = sorted(depindent_line_browse, key=lambda k: k.product_id.id)
            groups = []
            for key, group in groupby(depindent_line_browse, lambda x: x.product_id.id):
                groups.append(map(lambda r:r,group))
            for key,group in enumerate(groups):
                qty = sum(map(lambda x:float(x.issue_pending_qty),group)) #TODO: qty
                depindent_line_ids = map(lambda x:x.id,group)
                prod_browse = group[0].product_id           
                uom =False
                
                indent = group[0].indent_id
                dep = indent.dep_name.id
                        
                uom = group[0].uom.id or False
                
                depindent_obj = self.pool.get('kg.depindent').browse(cr, uid, indent.id)
                dep_stock_location = depindent_obj.dest_location_id.id
                main_location = depindent_obj.src_location_id.id
                                    
                vals = {
                
                    'product_id':prod_browse.id,
                    'product_uom':uom,
                    'product_uos':uom,
                    'stock_uom':uom,
                    'po_to_stock_qty':qty,
                    'product_qty':qty,
                    'po_qty':qty,
                    'name':prod_browse.name,
                    'location_id':main_location,
                    'location_dest_id':dep_stock_location,
                    'state' : 'confirmed',
                    'move_type' : 'out',
                    'depindent_line_id' : group[0].id,
                    }
                    
                if ids:
                    self.write(cr,uid,ids[0],{'move_lines':[(0,0,vals)]})
        self.write(cr,uid,ids,res)
        return True
        
    def action_process(self, cr, uid, ids, context=None):
        logger.info('[KG OpenERP] Class: kg_dep_issue, Method: action_process called...')
        picking_record = self.browse(cr,uid,ids[0])
        move_obj=self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        po_obj = self.pool.get('purchase.order')
        lot_obj = self.pool.get('stock.production.lot')
        move_ids=move_obj.search(cr, uid, [( 'picking_id','=',ids[0])])
        
        for i in range(len(move_ids)):
            move_record=move_obj.browse(cr, uid, move_ids[i], context=context)
            product_record = product_obj.browse(cr, uid,move_record.product_id.id)
            sql = """ select lot_id from kg_out_grn_lines where grn_id=%s""" %(move_record.id)
            cr.execute(sql)
            data = cr.dictfetchall()
            
            if not data:
                raise osv.except_osv(
                _('No GRN Entry !!'),
                _('There is no GRN reference for this Issue. You must associate GRN entries '))
            else:
                val = [d['lot_id'] for d in data if 'lot_id' in d]
                tot = 0.0
                for i in val:
                    lot_rec = lot_obj.browse(cr, uid, i)
                    tot += lot_rec.pending_qty
                if tot < move_record.product_qty:
                    raise osv.except_osv(
                    _('Stock not available !!'),
                    _('Associated GRN have less Qty compare to issue Qty. You can issue upto %s'%(tot)))
                else:
                    print "Store have enough stock........."
                    
            if move_record.depindent_line_id and move_record.po_to_stock_qty > move_record.po_qty:
                raise osv.except_osv(
                _('If Issue From Department Indent'),
                _('Issue Qty should not be greater than Indent Qty.!!!'))
            
            else:
                print "NO Issue"
        
        
        if context is None:
            context = {}
        context.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': len(ids) and ids[0] or False
        })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.partial.picking',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
            'nodestroy': True,
        }
        
    def kg_confirm_out(self, cr, uid, ids, context=None):
        
        logger.info('[KG OpenERP] Class: kg_dep_issue, Method: kg_confirm_out called...')
        
        move_obj = self.pool.get('stock.move')
        lot_obj = self.pool.get('stock.production.lot')
        product_obj = self.pool.get('product.product')
        self.write(cr, uid, ids, {'state': 'assigned'})
        pick = self.browse(cr, uid, ids[0])
        
        #for pick in self.browse(cr, uid, ids, context=context):
        if not pick.move_lines:
            raise osv.except_osv(_('Item Line Empty!'),_('You cannot process Issue without Item Line.'))
        else:
            
            for move in pick.move_lines:
                exp = []
                exp_data = []
                batch = []
                batch_data = []
                expiry_date = ''
                batch_nos = ''
                product_id = move.product_id.id
                product_uom = move.product_uom.id
                stock_uom = move.stock_uom.id               
                product_record = product_obj.browse(cr, uid,move.product_id.id)
                sql = """ select lot_id from kg_out_grn_lines where grn_id=%s""" %(move.id)
                cr.execute(sql)
                data = cr.dictfetchall()
                if not data:
                    raise osv.except_osv(
                    _('No GRN Entry !!'),
                    _('There is no GRN reference for this Issue. You must associate GRN entries '))
                else:                   
                    val = [d['lot_id'] for d in data if 'lot_id' in d]
                    #### Need to check UOM then will write price #####
                    stock_tot = 0.0
                    po_tot = 0.0
                    lot_browse = lot_obj.browse(cr, uid,val[0])
                    
                    for tmp in val:
                        lot_browse = lot_obj.browse(cr, uid,tmp)
                        # Expiry Date #
                        expdate = lot_browse.expiry_date
                        if expdate:
                            exp_date = datetime.strptime(expdate, '%Y-%m-%d').strftime('%d/%m/%Y')
                            exp.append(exp_date)
                            
                            if len(exp) !=1:
                               
                                for exp_num in range(len(exp)-1):
                                    if exp[exp_num] == exp[exp_num + 1]:
                                        if exp[exp_num] in exp_data:
                                            continue
                                        else:
                                            exp_data.append(exp[exp_num])
                                    else:
                                        if exp[exp_num +1] in exp_data:
                                            continue
                                        else:
                                            exp_data.append(exp[exp_num + 1])
                                    
                            else:
                                exp_data.append(exp[0])
                    
                            expiry_date = '\n'.join(exp_data)
                    
                        # Batch No #
                        batch_no = lot_browse.batch_no
                        if batch_no:
                            batch.append(batch_no)
                            
                            if len(batch) !=1:
                    
                                for batch_num in range(len(batch)-1):
                                    if batch[batch_num] == batch[batch_num + 1]:
                                        if batch[batch_num] in batch_data:
                                            continue
                                        else:
                                            batch_data.append(batch[batch_num])
                                    else:
                                        if batch[batch_num +1] in batch_data:
                                            continue
                                        else:
                                            batch_data.append(batch[batch_num + 1])
                            else:
                                batch_data.append(batch[0])
                            
                            batch_nos = '\n'.join(batch_data)           
                    
                    
                    grn_id = lot_browse.grn_move
                    move.write({'price_unit': lot_browse.price_unit or 0.0,
                                'stock_rate': lot_browse.price_unit or 0.0,
                                'expiry_date': expiry_date,
                                'batch_no':batch_nos
                                })                                          
                    
                    for i in val:
                        lot_rec = lot_obj.browse(cr, uid, i)
                        stock_tot += lot_rec.pending_qty
                        po_tot += lot_rec.po_qty
                        uom = lot_rec.product_uom.name
                    if stock_tot < move.product_qty:
                        raise osv.except_osv(
                        _('Stock not available !!'),
                        _('Associated GRN have less Qty compare to issue Qty. You can issue upto %s %s'%(po_tot,uom)))
                    else:
                        pass
                    
                if move.product_qty == 0:
                    raise osv.except_osv(
                    _('Item Line Qty can not Zero!'),
                    _('You cannot process Issue with Item Line Qty Zero for Product %s.' %(move.product_id.name)))
                if move.depindent_line_id and move.po_to_stock_qty > move.po_qty:
                    raise osv.except_osv(
                    _('If Issue From Indent'),
                    _('Issue Qty should not be greater than Department Indent Qty for Product %s' %(move.product_id.name)))
                uos_coeff = product_obj.read(cr, uid, product_id, ['po_uom_coeff'])
                if move.product_uom.id != product_record.uom_id.id:
                    stock_qty = move.po_to_stock_qty * uos_coeff['po_uom_coeff']
                    move.write({
                        'product_qty':stock_qty,
                        'stock_uom':product_record.uom_id.id,
                        'state': 'assigned',
                            })
                else:
                    move.write({'state': 'assigned'})
            return True
            
    def print_issue_slip(self, cr, uid, ids, context=None):     
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'stock.picking', ids[0], 'send_rfq', cr)
        datas = {
                 'model': 'stock.picking',
                 'ids': ids,
                 'form': self.read(cr, uid, ids[0], context=context),
        }
        return {'type': 'ir.actions.report.xml', 'report_name': 'issueslip.on.screen.report', 'datas': datas, 'nodestroy': True}
                    
kg_dep_issue()


class kg_stock_move(osv.osv):
    
    _name = "stock.move"
    _inherit = "stock.move"
    _rec_name = "product_id"    
    
    _columns = {
    
    'name': fields.char('Description', select=True),
    'date': fields.date('Date'),
    'po_qty': fields.float('Pending Qty', readonly=True),
    'cons_qty': fields.float('Available Qty', readonly=True),
    'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
            required=False, states={'done':[('readonly', True)], 'cancel':[('readonly',True)], 'assigned':[('readonly',False)]}),
   'product_id': fields.many2one('product.product', 'Product', required=True, select=True, domain=[('type','<>','service')],
        readonly=True, states={'draft':[('readonly', False)]}),
   'product_uom': fields.many2one('product.uom', 'Unit of Measure',
        readonly=True, states={'draft':[('readonly', False)]}),
    'name': fields.char('Description', required=True, select=True,
        readonly=True, states={'draft':[('readonly', False)]}),
   'location_dest_id': fields.many2one('stock.location', 'Destination Location', required=True,
        readonly=True, states={'draft':[('readonly', False)]}, 
        select=True, help="Location where the system will stock the finished products."),
    'location_id': fields.many2one('stock.location', 'Source Location', required=True, select=True,
        readonly=True, states={'draft':[('readonly', False)]}),
    'po_to_stock_qty' : fields.float('Quantity'),
    'stock_uom': fields.many2one('product.uom', 'Stock UOM'),
        
    'state': fields.selection([('draft', 'Draft'),
                                   ('cancel', 'Cancelled'),
                                   ('confirmed', 'Waiting for Confirmation'),
                                   ('assigned', 'Waiting for Approval'),
                                   ('done', 'Done'),
                                   ], 'Status', readonly=True, select=True),
                                   
    'move_type': fields.selection([('in', 'IN'),('out','out'),('cons','Cons'),('dummy','Dummy')], 'Move Type'),
    'depindent_line_id': fields.many2one('kg.depindent.line','Indent Line'),
    'notes': fields.text('Remarks'),
    'expiry_date': fields.text('Expiry Date'),
    'batch_no':fields.text('Batch No'),
    'kg_grn_moves': fields.many2many('stock.production.lot','kg_out_grn_lines','grn_id','lot_id', 'GRN Entry',
                    domain="[('product_id','=',product_id), '&', ('pending_qty','>','0'), '&', ('lot_type','!=','out')]",
                    readonly=True, states={'confirmed':[('readonly', False)],'assigned':[('readonly',False)]}),
    'expiry_flag': fields.boolean('Expiry'),
    'pi_id': fields.many2one('purchase.requisition.line', 'PI ID'),
    'gp_id': fields.many2one('kg.gate.pass', 'GP NO'),
    'gp_line_id': fields.many2one('kg.gate.pass.line', 'GP Line No'),
    'sa_id': fields.many2one('sale.order', 'Sale NO'),
    'sa_line_id': fields.many2one('sale.order.line', 'Sale Line'),
    'src_id': fields.many2one('stock.move', 'SRC'),
    'stock_rate':fields.float('Stock Rate'),
    'tax_id': fields.many2many('account.tax', 'purchase_order_taxxes', 'order_id', 'taxes_id', 'Taxes'),
    'kg_discount_per': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount')),
    'kg_discount': fields.float('Discount Amount'),
    'exp_line_id':fields.one2many('kg.grn.exp.batch', 'grn_line_id','Expiry Batch Line'),
    
        
    }
    
    _defaults = {
    
    'move_type': 'dummy',
    }   
    
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, partner_id=False, grn_type=False):
        logger.info('[KG OpenERP] Class: kg_stock_move, Method: onchange_product_id called...')
        if not prod_id:
            return {}
        lang = False
        if partner_id:
            addr_rec = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if addr_rec:
                lang = addr_rec and addr_rec.lang or False
        ctx = {'lang': lang}

        product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=ctx)[0]
        if product.expiry == True:
            flag = True
        else:
            flag = False
            
        uos_id  = product.uos_id and product.uos_id.id or False
        result = {
            'product_uom': product.uom_id.id,
            'product_uos': uos_id,
            'product_qty': 1.00,
            'prodlot_id' : False,
            'expiry_flag':flag,
        }
        if not ids:
            result['name'] = product.partner_ref
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        return {'value': result}    
            
    def onchange_quantity(self, cr, uid, ids, product_id,product_uom,product_qty, po_to_stock_qty, po_id=False):
        logger.info('[KG OpenERP] Class: kg_stock_move, Method: onchange_quantity called...')
        
        if product_id and product_uom and po_to_stock_qty:
            product_obj = self.pool.get('product.product')
            product_record = product_obj.browse(cr, uid, product_id)
            uos_coeff = product_obj.read(cr, uid, product_id, ['po_uom_coeff'])
            if ids:
                for move in self.read(cr, uid, ids):
                    if po_to_stock_qty > move['po_qty'] and move['move_type'] == 'in':
                            raise osv.except_osv(
                            _('If GRN From PO'),
                            _('GRN Qty should not be greater than PO Pending Qty.!!!'))
                    
                    if po_to_stock_qty > move['po_qty'] and move['move_type'] == 'out':
                        raise osv.except_osv(
                        _('If Issue From Indent'),
                        _('Issue Qty should not be greater than Indent Pending Qty.!!!'))
                    else:
                        if move['move_type'] == 'cons' and po_to_stock_qty > move['cons_qty']:
                            raise osv.except_osv(                           
                            _('Consumption Qty Issue'),
                            _('Consumption Qty should not be greater than Available Qty.!!!'))
                        
                    if product_uom != product_record.uom_id.id:
                        if po_to_stock_qty: 
                            stock_qty = po_to_stock_qty * uos_coeff['po_uom_coeff']
                            return{'value':{'product_qty':stock_qty,'stock_uom':product_record.uom_id.id}}
                    else:
                        return{'value':{'product_qty':po_to_stock_qty, 'stock_uom':product_record.uom_id.id}}
                        
                return False
            else:
                
                if product_uom != product_record.uom_id.id:
                    if po_to_stock_qty: 
                        stock_qty = po_to_stock_qty * uos_coeff['po_uom_coeff']
                        return{'value':{'product_qty':stock_qty,'stock_uom':product_record.uom_id.id}}
                else:
                    return{'value':{'product_qty':po_to_stock_qty,'stock_uom':product_record.uom_id.id}}
    def unlink(self, cr, uid, ids, context=None):       
        logger.info('[KG OpenERP] Class: kg_stock_move, Method: unlink called...')
        if context is None:
            context = {}
        move = self.read(cr, uid, ids, ['state'], context=context)      
        unlink_ids = []
        for t in move:
            move_rec = self.browse(cr, uid, t['id'])
            if move_rec.picking_id.type == 'in':
                if len(move_rec.picking_id.move_lines) == 1:
                    raise osv.except_osv(_('Invalid action !'), _('This PO have 1 item line.So, System not allow to delete this !!'))
                else:
                    unlink_ids.append(t['id'])
            if move_rec.picking_id.type == 'in':                
                if move_rec.move_type == 'in' and move_rec.state == 'confirmed':
                    unlink_ids.append(t['id'])
                else:
                    raise osv.except_osv(_('Invalid action !'), _('System not allow to delete Confirmed and Done state stock moves !!'))
            
            elif move_rec.picking_id.type == 'out':             
                if move_rec.move_type == 'out' and move_rec.state == 'confirmed':
                    di_line = move_rec.depindent_line_id
                    di_line.write({'line_state' : 'noprocess'})
                    del_sql = """ delete from kg_depline_picking where kg_depline_id=%s and stock_picking_id=%s """ %(move_rec.picking_id.id,di_line.id)
                    cr.execute(del_sql) 
                    unlink_ids.append(t['id'])
                else:
                    raise osv.except_osv(_('Invalid action !'), _('System not allow to delete Confirmed and Done state stock moves !!'))
            else:
                pass
                
        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True
    
    def cons_onchange_qty(self,cr,uid,ids,po_to_stock_qty,product_qty):
        if ids:
                for move in self.read(cr, uid, ids):
                    if move['move_type'] == 'cons' and po_to_stock_qty > move['cons_qty']:
                            raise osv.except_osv(                           
                            _('Consumption Qty Issue'),
                            _('Consumption Qty should not be greater than Available Qty.!!!'))
                    else:
                        return{'value':{'product_qty':po_to_stock_qty}}     
        
kg_stock_move()

class kg_stock_production_lot(osv.osv):
		
	_name = "stock.production.lot"
	_inherit="stock.production.lot"
	_order = 'date' 
	_rec_name = 'batch_no'
	
	def _lot_value(self, cr, user, ids, name, arg, context=None):
		res = {}
		for lot in self.browse(cr, user, ids, context=context):
			if lot.pending_qty >0 and lot.price_unit >0:
				res[lot.id] = lot.pending_qty*lot.price_unit 
			else:
				res[lot.id] = 0.0
		return res	
	
	_columns = {
	
	'grn_move':fields.many2one('stock.move','GRN Move'),
	'grn_no':fields.char('GRN NO', char=128),
	'product_qty':fields.float('Quantity'),
	'pending_qty':fields.float('Pending Qty'),
	'issue_qty':fields.float('Issue Qty'),
	'product_uom':fields.many2one('product.uom', 'UOM'),
	'expiry_date':fields.date('Expiry Date'),
	'batch_no':fields.char('Batch No', size=128),
	'price_unit': fields.float('Rate'),
	'po_uom': fields.many2one('product.uom', 'PO UOM'), 
	'po_qty': fields.float('PO Qty'),
	'user_id':fields.many2one('res.users','LOT User'),
	'grn_type': fields.selection([('material', 'Material'), ('service', 'Service')], 'GRN Type'),
	'brand_id':fields.many2one('kg.brand.master','Brand Name'),
	'source_loc_id':fields.many2one('stock.location','Source Location'),		
	'dest_loc_id':fields.many2one('stock.location','Destination Location'),		
	'lot_value': fields.function(_lot_value, string='Invoiced Ratio', type='float',store = True),
	'inward_type': fields.many2one('kg.inwardmaster', 'Inward Type'), ### Added To avoid double time stock update	
	}   
	
	_defaults = {
	'lot_value':0.00
	}	
	
	def name_get(self, cr, uid, ids, context={}):
		 
		if not len(ids):
			return []

		res=[]

		for emp in self.browse(cr, uid, ids,context=context):
			res.append((emp.id, emp.batch_no or ''))	   
		return res
	
	
	def onchange_qty(self,cr,uid,ids,issue_qty,pending_qty):
		value = {'issue_qty': ''}
		if issue_qty > pending_qty:
			raise osv.except_osv(_('Issue Qty Error !!'), _('Issue qty should be less than GRN pending qty !!!'))	   
						
		else:
			value = {'issue_qty' : issue_qty}
			return {'value': value}	 

kg_stock_production_lot()


class kg_grn_exp_batch(osv.osv):

    _name = "kg.grn.exp.batch"
    _description = "Expiry Date and Batch NO"

    
    _columns = {
        
        'grn_line_id':fields.many2one('stock.move','Move Line'),
        'exp_date':fields.date('Expiry Date'),
        'batch_no':fields.char('Batch No'),
        'product_qty':fields.integer('Product Qty'),
        
        
    }
    
    
    
kg_grn_exp_batch()
