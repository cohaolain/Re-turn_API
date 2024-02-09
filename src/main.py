import json
import os
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Lock
import requests
import logging

from barcode_helpers import verify_checksum


API_NAME = "ohaolain Re-Turn API"

app = Flask(API_NAME)
CORS(app)

# Setup logging
logger = logging.getLogger(API_NAME)

formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(name)s] Level=%(levelname)s %(message)s', "%Y-%m-%d %H:%M:%S")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler('re-turn_api.log')  # Create a handler that will write all logs to 'app.log' file
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.setLevel(logging.INFO)

cache_file = "cache.json"
if not os.path.exists(cache_file):
    with open(cache_file, 'w') as f:
        json.dump({}, f)
cache_lock = Lock()

def load_cache(lockless=False):
    if lockless:
        with open(cache_file, 'r') as f:
            return json.load(f)
        
    with cache_lock:
        with open(cache_file, 'r') as f:
            return json.load(f)

def update_cache(barcode_no, value):
    with cache_lock:
        cache = load_cache(lockless=True)
        cache[barcode_no] = value

        with open(cache_file, 'w') as f:
            json.dump(cache, f)



CACHE_TIMEOUT_SECONDS = 86400
@app.route('/barcode', methods=['GET'])
def barcode(try_convert_to_ean13=True):
    barcode_no = request.args.get('barcodeNo')
    start_time = time.time()

    def get_common_log_line_contents():
        ip = request.headers['X-Real-Ip'] if 'X-Real-Ip' in request.headers else request.remote_addr
        return f"IP={ip} QueryTimeMs={(time.time() - start_time)*1000} BarcodeNo={barcode_no}"
    
    if not barcode_no:
        logger.warn(f"MsgType=BarcodeRequestInvalid {get_common_log_line_contents()} Reason=BarcodeNotProvided")
        return jsonify({"success": False, "message": "'barcodeNo' is required."}), 400
    
    if not barcode_no.isnumeric():
        logger.warn(f"MsgType=BarcodeRequestInvalid {get_common_log_line_contents()} Reason=BarcodeNotNumeric")
        return jsonify({"success": False, "message": "'barcodeNo' must be a number."}), 400
    
    likely_good_barcode = verify_checksum(barcode_no)

    try_again_with_upc_code_if_eac13_not_in_scheme = False
    if try_convert_to_ean13 and len(barcode_no) == 12:
        # This has been read/provided as a UPC A barcode, but this can also be
        # written as an EAN13 barcode by prepending a zero 
        # (likely visible under barcode in text).
        # The API call below returns true _only_ when the number matches exactly
        # the barcode registered - i.e. the optional zero matters if it's there.
        # Therefore, let's also try query _with_ the zero prepended.
        # In fact, it's probably more likely to match this way - so try it first!
        barcode_no = f"0{barcode_no}"
        logger.warn(f"Prepending 0 to 12-digit barcode yielding {barcode_no}")
        try_again_with_upc_code_if_eac13_not_in_scheme = True
            
    cache = load_cache()
        
    cached_value = None
    if barcode_no in cache:
        if time.time() - cache[barcode_no]["timestamp"] < CACHE_TIMEOUT_SECONDS:
            is_in_return_scheme = cache[barcode_no]["isPartOfReturnScheme"]

            # Check to see if we want another shot at this without an applied conversion
            if not is_in_return_scheme and try_again_with_upc_code_if_eac13_not_in_scheme:
                return barcode(try_convert_to_ean13=False)

            logger.info(f"MsgType=BarcodeRequestSuccess {get_common_log_line_contents()} BarcodeValidChecksum={likely_good_barcode} IsPartOfReturnScheme={is_in_return_scheme} ResponseFrom=Cache")
            return jsonify({"success": True, "isPartOfReturnScheme": is_in_return_scheme, "responseFrom": "cache", "barcodeNo": barcode_no, "barcodeValidChecksum": likely_good_barcode, "queryTimeMs": (time.time() - start_time)*1000}), 200
        cached_value = cache[barcode_no]
    
    url = "https://re-turn.ie/wp-admin/admin-ajax.php"
    headers = {
          "accept": "*/*",
          "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
          "sec-fetch-dest": "empty",
          "sec-fetch-mode": "cors",
          "sec-fetch-site": "same-origin",
          "x-requested-with": "XMLHttpRequest"
     }
    
    data = {
         'action': 'barcode_api_callback',
         'barcodeNo': barcode_no,
     }
    
    response = requests.post(url, headers=headers, data=data)
    if response.ok:
        good_container_str = "Your drink container is part of Re-turn Ireland’s Deposit Return Scheme"
        bad_container_str = "Not in Re-turn Scheme"
        valid_response = (good_container_str in response.text) or (bad_container_str in response.text)
        if valid_response:
            is_in_return_scheme = good_container_str in response.text

            result = {"timestamp": time.time(), "isPartOfReturnScheme": is_in_return_scheme}
            
            update_cache(barcode_no, result)

            # Check to see if we want another shot at this without an applied conversion
            if not is_in_return_scheme and try_again_with_upc_code_if_eac13_not_in_scheme:
                return barcode(try_convert_to_ean13=False)
                
            # Best case scenario
            logger.info(f"MsgType=BarcodeRequestSuccess {get_common_log_line_contents()} BarcodeValidChecksum={likely_good_barcode} IsPartOfReturnScheme={is_in_return_scheme} ResponseFrom=API")
            return jsonify({"success": True, "isPartOfReturnScheme": is_in_return_scheme, "responseFrom": "api", "barcodeNo": int(barcode_no), "barcodeValidChecksum": likely_good_barcode, "queryTimeMs": (time.time() - start_time)*1000}), 200
        
        if cached_value:
            is_in_return_scheme = cached_value["isPartOfReturnScheme"]
            logger.info(f"MsgType=BarcodeRequestFailureWithStaleCacheFallback {get_common_log_line_contents()} BarcodeValidChecksum={likely_good_barcode} IsPartOfReturnScheme={is_in_return_scheme} ResponseFrom=StaleCacheFallback Reason=ValidResponseButCouldNotParse")
            return jsonify({"success": True, "isPartOfReturnScheme": is_in_return_scheme, "responseFrom": "stale_cache_fallback", "barcodeNo": int(barcode_no), "barcodeValidChecksum": likely_good_barcode, "queryTimeMs": (time.time() - start_time)*1000}), 200

        logger.error(f"MsgType=BarcodeRequestFailure {get_common_log_line_contents()} BarcodeValidChecksum={likely_good_barcode} Reason=ValidResponseButCouldNotParse")
        return jsonify({"success": False, "message": "Got ok response from API, but was unable to parse it.", "barcodeNo": int(barcode_no), "barcodeValidChecksum": likely_good_barcode, "queryTimeMs": (time.time() - start_time)*1000}), 500
    else:
        if cached_value:
            is_in_return_scheme = cached_value["isPartOfReturnScheme"]
            logger.info(f"MsgType=BarcodeRequestFailureWithStaleCacheFallback {get_common_log_line_contents()} BarcodeValidChecksum={likely_good_barcode} IsPartOfReturnScheme={is_in_return_scheme} ResponseFrom=StaleCacheFallback Reason=InvalidResponseFromAPI StatusCode={response.status_code} ResponseReason='{response.reason}'")
            return jsonify({"success": True, "isPartOfReturnScheme": is_in_return_scheme, "responseFrom": "stale_cache_fallback", "barcodeNo": int(barcode_no), "barcodeValidChecksum": likely_good_barcode, "queryTimeMs": (time.time() - start_time)*1000}), 200

        logger.error(f"MsgType=BarcodeRequestFailure {get_common_log_line_contents()} BarcodeValidChecksum={likely_good_barcode} Reason=InvalidResponseFromAPI StatusCode={response.status_code} ResponseReason='{response.reason}'")
        return jsonify({"success": False, "message": f"Invalid Response from Re-Turn API - Status Code: {response.status_code}, Reason: {response.reason}", "barcodeNo": int(barcode_no), "barcodeValidChecksum": likely_good_barcode, "queryTimeMs": (time.time() - start_time)*1000}), response.status_code
    

if __name__ == '__main__':
    app.run()
else:
    gunicorn_app = app
