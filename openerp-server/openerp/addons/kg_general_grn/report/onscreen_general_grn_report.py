# -*- encoding: utf-8 -*-
##############################################################################
#
#	OpenERP, Open Source Management Solution
#	Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#	$Id$
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from kg_purchase_order import JasperDataParser
from jasper_reports import jasper_report
import pooler
import time, datetime
import base64
import netsvc
from osv import osv, fields
from tools.translate import _
from osv.orm import browse_record, browse_null
import os

class onscreen_general_grn_report(JasperDataParser.JasperDataParser):
	def __init__(self, cr, uid, ids, data, context):
		print"cr.............",cr
		sql_del = """delete from tmp_kg_general_grn WHERE user_id=%s"""%(uid)
		cr.execute(sql_del,)
		print"sql_del.............",sql_del
		
		for s in ids:
			sql = """INSERT INTO tmp_kg_general_grn(grn_id,user_id) values(%s,%s)""" % (s,uid)
			cr.execute(sql,)
			sql_c="""commit"""
			cr.execute(sql_c,)
			print "-----------------hai ----------------------"
		super(onscreen_general_grn_report, self).__init__(cr, uid, ids, data, context)

	def generate_data_source(self, cr, uid, ids, data, context):
		return 'records'


	def generate_ids(self, cr, uid, ids, data, context):
		return {}

	def generate_properties(self, cr, uid, ids, data, context):
		return val
		
	def generate_parameters(self, cr, uid, ids, data, context):
		val={}		
		val['user_id'] = uid
		print "val....................", val		
		return val
		
		

	def generate_records(self, cr, uid, ids, data, context):
		pool= pooler.get_pool(cr.dbname)		
		return {}

jasper_report.report_jasper('report.onscreen_general_grn_report', 'kg.general.grn', parser=onscreen_general_grn_report)
