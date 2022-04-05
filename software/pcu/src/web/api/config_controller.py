import json
from flask import request, Blueprint
from flask_cors import CORS
from src.web.api.login_validation.login_validation import verify_token
from src.config.config import set_reference_voltage, set_memory_type, set_log_ip, set_log_port, set_login_password, \
    reboot_pcu

bp = Blueprint('config', __name__, url_prefix='/config', )
CORS(bp)


@bp.route('/memory_type/<mem_type>', methods=['PUT'])
@verify_token
def put_memory_type(mem_type):
    return set_memory_type(mem_type)


@bp.route('/log_ip/<log_ip>', methods=['PUT'])
@verify_token
def put_log_ip(log_ip):
    return set_log_ip(log_ip)


@bp.route('/log_port/<log_port>', methods=['PUT'])
@verify_token
def put_log_port(log_port):
    return set_log_port(log_port)


@bp.route('/password/<password>', methods=['PUT'])
@verify_token
def put_password(password):
    return set_login_password(password)


@bp.route('/reference_voltage/<reference_voltage>', methods=['PUT'])
@verify_token
def put_reference_voltage(reference_voltage):
    return set_reference_voltage(reference_voltage)


@bp.route('/reboot', methods=['PUT'])
@verify_token
def reboot_pi():
    return reboot_pcu()