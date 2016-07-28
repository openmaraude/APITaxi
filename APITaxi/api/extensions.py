#coding: utf-8
from flask_uploads import UploadSet, DOCUMENTS, DATA, ARCHIVES

documents = UploadSet('documents', DOCUMENTS + DATA + ARCHIVES)
