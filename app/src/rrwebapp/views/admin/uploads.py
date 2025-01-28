"""
uploads - support upload and download of files, e.g., for agegrade factors
"""

# standard

# pypi
from flask import request, jsonify
from flask.views import MethodView
from flask_uploads.exceptions import UploadNotAllowed

# homegrown
from . import bp

# NOTE: configure_uploads is called in rrwebapp.create_app, else circular import

# upload files
class AGFactorUploadApi(MethodView):
    def post(self):
        from ... import agfactors
        
        try:
            filename = agfactors.save(request.files['upload'])
        except UploadNotAllowed:
            return jsonify({'error': 'file type not allowed'})

        return jsonify({
            'upload' : {'id': filename },
            'files' : {
                'data' : {
                    filename : {'filename': filename}
                },
            },
        })
bp.add_url_rule('/agfactoruploads', view_func=AGFactorUploadApi.as_view('agfactoruploads'), methods=['POST'])


