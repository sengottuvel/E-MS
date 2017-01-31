import xmlrpclib

username = 'admin' #the user
pwd = 'admin'      #the password of the user
dbname = 'machineshop'    #the database

# Server Connectivity

sock_common = xmlrpclib.ServerProxy ('http://localhost:8070/xmlrpc/common')
uid = sock_common.login(dbname, username, pwd)
sock = xmlrpclib.ServerProxy('http://localhost:8070/xmlrpc/object')

## Scheduler List
sock.execute(dbname, uid, pwd, 'kg.inwardmaster', 'user_entry_count')
