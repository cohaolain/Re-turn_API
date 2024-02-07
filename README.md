# Ireland's Re-turn Scheme Barcode Checker API

## Introduction
This API allows you to check whether a given barcode number corresponds to an item which is part of Ireland's Re-turn Deposit Return Scheme for plastic bottles and aluminium/metal cans.

## Disclaimer
> This is a third-party API, which in turn utilizes the barcode lookup feature available on Re-turn's website.  
>
> It is developed independently, and it is not affiliated with, or endorsed by, Re-turn.
> 
> I'm just trying to provide a useful tool to help support people in using this scheme, in the form of a fun little project :)

## Endpoint
The main endpoint for the Re-turn API is `https://re-turn.cohaolain.ie/api/barcode`. This endpoint accepts GET requests and requires one parameter: 'barcodeNo'. The barcodeNo should be a numeric value representing the product's unique identification code.

## Usage
To use this API, send a GET request to `https://re-turn.cohaolain.ie/api/barcode` with your barcode number as a query parameter. For example:

```bash
curl "https://re-turn.cohaolain.ie/api/barcode?barcodeNo=5010038455463"
```
Gives us the response:
```json
{"barcodeNo":5010038455463,"barcodeValidChecksum":true,"isPartOfReturnScheme":true,"queryTimeMs":0.29397010803222656,"responseFrom":"cache","success":true}
```

## Response Format
The API will return a JSON object containing the following fields:

- `success` (boolean): Indicates whether the request was successful or not.
- `isPartOfReturnScheme` (boolean): Indicates whether the product is part of Re-turn Ireland's Deposit Return Scheme.
- `barcodeValidChecksum` (boolean): Indicates whether the barcode checksum is valid according to a checksum algorithm.
- `message` (string): Includes an error message if 'success' is false.
- `responseFrom` (string): Specifies where the response came from - either "api", "cache", or "stale_cache_fallback".
- `queryTimeMs` (float): Time taken for the query, in milliseconds.
- `barcodeNo` (integer): The barcode number that was provided in the request.

## Error Handling
If there are any issues with the request, such as a missing or non-numeric 'barcodeNo', the API will return an error response with a status code of 400 and include a descriptive error message in the `message` field. For instance:

```json
{
    "success": false,
    "message": "'barcodeNo' must be a number."
}
```

## Caching
Barcodes that have been queried recently have their outcome cached by the API server. This cache expires after 24 hours, to ensure changes are picked up. If there are issues ascertaining whether a barcode is included in the scheme, the last retrieved value will be used (yielding `responseFrom=stale_cache_fallback` in the response).

## Logging
The Re-turn API server logs information about its operations. The log entries include messages that specify the outcome of each query, the IP address of the client making the request, the time taken for the query, the barcode number being checked, and whether the barcode is theoretically valid according to a built-in checksum algorithm, and any other relevant details.