# if you are using VirtualEnv and cannot specify which python 
# interpreter to use in your webserver conf, 
# (WSGIPythonHome for Apache mod_wsgi),
# uncomment the two following lines and adapt the path
#
#activate_this = '/home/opendatataxi/adsapp/bin/activate_this.py'
#execfile(activate_this, dict(__file__=activate_this))

# if you cannot specify the path of your app in your webserver 
# virtualhost conf
# (WSGIDaemonProcess python-path= for Apache mod_wsgi),
# uncomment the two following lines and adapt the path
# 
#import sys
#sys.path.insert(0, '/home/opendatataxi/adsapp/backoffice_operateurs')


import os
from APITaxi import create_app
application = create_app()
