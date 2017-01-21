{ "name"         : "Variant of field type one2many and many2many for sorted associations"
, "version"      : "1.0"
, "author"       : "Swing Entwicklung betrieblicher Informationssysteme GmbH"
, "website"      : "http://www.swing-system.com"
, "description"  : """
Variant of field type one2many for sorted associations

Usage:

| import one2many_sorted
| ...
|    _columns = \
|        { 'partner_ids'  : one2many_sorted.one2many_sorted
|            ( 'res.partner'
|            , 'parent_id'
|            , 'Sorted Partner List'
|            , order='name.upper(), title'
|            , search=[('is_company', '=', 'False')]
|            , set={'is_company' : False}
|            )
|        }
| ...

In the example above, the primary sort criteria is "name" (not case-sensitive), the secondary is "title".
Only partners that are physical persons (not is_company) are selected - and only those can be added.

Another possibility is to define a text-property with naming convention "<obj>.<field>.order" 
(in the example above this would be "res.partner.parent_id.order").
The value of this property is the sort criteria.

The advantage of properties is, that they can by company-individual.

A third possibility is to hand over a "context" key named "one2many_sorted_order" that contains the name of a property.

If no "context" key is found, then the property with the naming convention is taken.
If no property is defined, the programmed sort order is taken.
Otherwise no sorting takes place.

many2many_sorted has a similar syntax but without search feature.

Note that it works on translated term, not only the text stored in the DB !


"""
, "category"     : "Tools"
, "depends"      : ["base"]
, "init_xml"     : []
, "demo"         : []
, "update_xml"   : []
, "test"         : []
, "auto_install" : False
, "installable"  : True
, 'application'  : False
}
