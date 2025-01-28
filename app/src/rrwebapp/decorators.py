###########################################################################################
# login -- log in / out views for race results web application
#
#       Date            Author          Reason
#       ----            ------          ------
#       10/11/13        Lou King        Create
#
#   Copyright 2013 Lou King
#
###########################################################################################

# standard

# pypi
from functools import wraps
from flask import request, redirect, current_app

#----------------------------------------------------------------------
def ssl_required(fn):
#----------------------------------------------------------------------
    '''
    enable https for a page with this decorator.
    see http://flask.pocoo.org/snippets/93/
    '''
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if current_app.config.get("SSL"):
            if request.is_secure:
                return fn(*args, **kwargs)
            else:
                return redirect(request.url.replace("http://", "https://"))
        
        return fn(*args, **kwargs)
            
    return decorated_view