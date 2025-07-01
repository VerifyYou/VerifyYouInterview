from flask import Blueprint
from flask import Flask
from flask import jsonify
from flask import json
from flask import request

import os

config_app = Blueprint('config_app',__name__)

@config_app.route('/v1/config/get', methods=['POST', 'PUT'])
def config_get():
  config = {
    'verifyyou_ios': {
      'required_version': '1.1.107',
    },
    'verifyyou_android': {
      'required_version': '1.1.107',
    },
  }

  return jsonify({
    'status': 'success',
    'config': json.dumps(config),
  })
