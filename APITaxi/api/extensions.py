#coding: utf-8
from flask.ext.uploads import UploadSet, DOCUMENTS, DATA, ARCHIVES

documents = UploadSet('documents', DOCUMENTS + DATA + ARCHIVES)
