import http.client
import json
import urllib.parse
import os
import json
import fitz  # PyMuPDF
import base64
import requests
import zipfile
import io
from PIL import Image  # optional, if you want to load the PNGs

from dotenv import load_dotenv

BEARER_TOKEN = ''

DHL_USERNAME = os.getenv('DHL_USERNAME')
DHL_PASSWORD = os.getenv('DHL_PASSWORD')
DHL_CLIENT_ID = os.getenv('DHL_CLIENT_ID')
DHL_CLIENT_SECRET = os.getenv('DHL_CLIENT_SECRET')

def api_version_resource():
    conn = http.client.HTTPSConnection("api-eu.dhl.com")
    payload = ''
    headers = {}
    try:
        conn.request("GET", "/post/de/shipping/im/v1/", payload, headers)
        res = conn.getresponse()
        data = res.read()
        return True
    except:
        return False

def user_resource():
    """
    Authenticate with DHL Internetmarke API and retrieve user details.

    This function requests an access token and related account information
    from DHL's Internetmarke API using credentials stored in environment variables.

    Returns:
        tuple: A tuple containing the following values:
            - access_token (str): Bearer token for authenticated API requests
            - walletBalance (int): Current account balance
            - token_type (str): Type of token (e.g., "BearerToken")
            - expires_in (int): Token lifetime in seconds
            - issued_at (str): Timestamp when the token was issued
            - external_customer_id (str): DHL customer ID
            - authenticated_user (str): Authenticated username (e.g., email)

    Example:
        >>> access_token, walletBalance, token_type, expires_in, issued_at, external_customer_id, authenticated_user = user_resource()
        >>> print("Access token:", access_token)
        >>> print("Wallet balance:", walletBalance)
        >>> print("Authenticated user:", authenticated_user)
    """
    DHL_USERNAME = os.getenv('DHL_USERNAME')
    DHL_PASSWORD = os.getenv('DHL_PASSWORD')
    DHL_CLIENT_ID = os.getenv('DHL_CLIENT_ID')
    DHL_CLIENT_SECRET = os.getenv('DHL_CLIENT_SECRET')

    conn = http.client.HTTPSConnection("api-eu.dhl.com")
    payload = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'username': DHL_USERNAME,        # Replace with your Internetmarke username
        'password': DHL_PASSWORD,          # Replace with your Internetmarke password
        'client_id': DHL_CLIENT_ID,   # Replace with your client_id
        'client_secret': DHL_CLIENT_SECRET # Replace with your client_secret
    })
    headers = {
    'content-type': 'application/x-www-form-urlencoded',
    }
    conn.request("POST", "/post/de/shipping/im/v1/user", payload, headers)
    res = conn.getresponse()
    response_str = res.read()

    # Convert JSON string to Python dict
    data = json.loads(response_str)
    # load access token
    global BEARER_TOKEN
    BEARER_TOKEN = data['access_token']

    return (
        data['access_token'], 
        data["walletBalance"], 
        data["token_type"], 
        data["expires_in"], 
        data["issued_at"], 
        data["external_customer_id"], 
        data["authenticated_user"]
    )

def get_shopping_chart_id():

    conn = http.client.HTTPSConnection("api-eu.dhl.com")
    payload = ''
    headers = {
    'Authorization': 'Bearer {}'.format(BEARER_TOKEN),
    'Content-Length': '0'
    }
    conn.request("POST", "/post/de/shipping/im/v1/app/shoppingcart", payload, headers)
    res = conn.getresponse()
    data = res.read()

    response = data.decode("utf-8")
    return json.loads(response)['shopOrderId']



def get_shopping_chart_pdf(order_id):
    import http.client
    import json

    conn = http.client.HTTPSConnection("api-eu.dhl.com")
    payload = json.dumps({
    "type": "AppShoppingCartPDFRequest",
    "shopOrderId": order_id,
    "total": 270,
    "createManifest": True,
    "createShippingList": 0,
    "dpi": "DPI203",
    "pageFormatId": 1,
    "positions": [
        {
        "productCode": 290,
        "imageID": 0,
        "address": {
                "sender": {
                "name": "Max Mustermann",
                "additionalName": "Deutsche Post AG",
                "addressLine1": "string",
                "addressLine2": "3rd Floor",
                "postalCode": "10115",
                "city": "Berlin",
                "country": "DEU"
            },
                "receiver": {
                "name": "Max Mustermann",
                "additionalName": "Deutsche Post AG",
                "addressLine1": "string",
                "addressLine2": "3rd Floor",
                "postalCode": "10115",
                "city": "Berlin",
                "country": "DEU"
            }
        },
        "voucherLayout": "FRANKING_ZONE",

        "positionType": "AppShoppingCartPDFPosition",
        "position": {
            "labelX": 1,
            "labelY": 1,
            "page": 1
        }
        }
    ]
    })
    headers = {
        'content-type': 'application/json',
        'Authorization': 'Bearer {}'.format(BEARER_TOKEN),
    }
    conn.request("POST", "/post/de/shipping/im/v1/app/shoppingcart/pdf", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))

def checkout_shopping_chart_png(order_id, positions):

    price_total = 0
    for p in positions:
        price_total = price_total + p['price']

    def build_positions(text, product_code, price):

        name, addiditional_name, street, street2, postalcode, city, country = struct_address(text)
        
        if country.upper() == 'DEUTSCHLAND':
            country = 'DEU'

        return { 
            "productCode": product_code, 
            "imageID": 0,
            "address":  {
                "sender": {
                    "name": "frapp GmbH",
                    "additionalName": " ",
                    "addressLine1": "Bachstraße 24-26",
                    "addressLine2": " ",
                    "postalCode": "96188",
                    "city": "Stettfeld",
                    "country": "DEU"
                },
                "receiver": {
                    "name": name,
                    "additionalName": addiditional_name if addiditional_name else ' ',
                    "addressLine1": street,
                    "addressLine2": street2 if street2 else ' ',
                    "postalCode": postalcode,
                    "city": city,
                    "country": country if country else ' '
                }
            },
            "voucherLayout": "FRANKING_ZONE",
            "positionType": "AppShoppingCartPosition"
        }

    # create connections
    conn = http.client.HTTPSConnection("api-eu.dhl.com")

    payload = json.dumps({
        "type": "AppShoppingCartPNGRequest",
        "shopOrderId": order_id,
        "total": price_total,
        "createManifest": True,
        "createShippingList": 0,

        "dpi": "DPI300",
        "optimizePNG": True,
        "positions": list(map(lambda e: build_positions(e['receiver'], e['product_code'], e['price']), positions))
          
    })
    # print(payload)
    
    headers = {
        'content-type': 'application/json',
        'Authorization': 'Bearer {}'.format(BEARER_TOKEN),
    }
    conn.request("POST", "/post/de/shipping/im/v1/app/shoppingcart/png", payload, headers)
    res = conn.getresponse()
    response_string = res.read().decode('utf-8')

    data = json.loads(response_string)
    return data



def download_and_unpack(download_url):
    images = []

    # Step 1: Download the zip file
    response = requests.get(download_url)
    response.raise_for_status()

    # Step 2: Open zip in memory
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # Step 3: Iterate over PNG files
        for name in z.namelist():
            if name.lower().endswith(".png"):
                # Get file as a bytes-like object (blob)
                with z.open(name) as file:
                    blob = file.read()  # raw bytes

                    # Example 1: Work with raw bytes
                    print(f"{name} → {len(blob)} bytes")

                    # Example 2 (optional): Load directly into PIL without saving
                    image = Image.open(io.BytesIO(blob))
                    print(f"  Image size: {image.size}, format: {image.format}")

                    images.append(image)

    return images

def mm_to_pt(mm: float) -> float:
    """Umrechnung Millimeter -> PDF-Punkte"""
    return mm / 0.3528

def snip_pdf_region_mm_to_bytes(pdf_path: str,
                                page_index: int,
                                x0_mm: float, y0_mm: float, x1_mm: float, y1_mm: float,
                                dpi: int = 192,
                                fmt: str = "png") -> bytes:
    """
    Schneidet ein Rechteck (mm) aus einer PDF-Seite und gibt Bild-Bytes zurück.
    fmt: 'png' oder 'jpeg'
    """
    zoom = dpi / 72.0
    with fitz.open(pdf_path) as doc:
        page = doc[page_index]
        x0, y0, x1, y1 = map(mm_to_pt, [x0_mm, y0_mm, x1_mm, y1_mm])
        rect = fitz.Rect(x0, y0, x1, y1)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect, alpha=False)
        return pix.tobytes(fmt)



def snip_pdf_region_mm_to_b64(pdf_path: str,
                              page_index: int,
                              x0_mm: float, y0_mm: float, x1_mm: float, y1_mm: float,
                              dpi: int = 192,
                              fmt: str = "png") -> str:
    """
    Wie oben, aber als base64-String (ohne data: Prefix) – ideal für Jinja2.
    """
    img_bytes = snip_pdf_region_mm_to_bytes(pdf_path, page_index, x0_mm, y0_mm, x1_mm, y1_mm, dpi, fmt)
    return base64.b64encode(img_bytes).decode("ascii")

# Example:
#snip_pdf_region_mm_to_b64("TestPrint (2).pdf", "figure1.png",page_index=0, x0_mm=1, y0_mm=11, x1_mm=71, y1_mm=52, dpi=200)


import re

def struct_address(address: str):
    """
    Parse a postal address string into components:
    name, additional_name, street, street2, postal code, city, country
    """
    # Normalize and split into lines
    lines = [l.strip() for l in address.strip().splitlines() if l.strip()]
    
    # Defaults
    name = additional_name = street = street2 = postalcode = city = country = ""
    
    if lines:
        name = lines[0]
    
    # Handle optional second line as "additional name" (e.g., department, c/o)
    i = 1
    if i < len(lines) and not re.search(r"\d", lines[i]):
        additional_name = lines[i]
        i += 1
    
    # Next line is usually street
    if i < len(lines):
        street = lines[i]
        i += 1
    
       # Check if next line looks like a postal code + city
    if i < len(lines):
        m = re.match(r"(\d{4,5})\s+(.+)", lines[i])
        if m:
            postalcode, city = m.groups()
            i += 1
        else:
            # If not a postal code → treat as street2
            street2 = lines[i]
            i += 1
            # Try postal code on next line
            if i < len(lines):
                m = re.match(r"(\d{4,5})\s+(.+)", lines[i])
                if m:
                    postalcode, city = m.groups()
                    i += 1
                else:
                    city = lines[i]
                    i += 1
    
    # Remaining line(s) → country or street2
    if i < len(lines):
        country = lines[i]
        i += 1
   
    
    return name, additional_name, street, street2, postalcode, city, country


def main():
    load_dotenv()
    access_token, walletBalance, token_type, expires_in, issued_at, external_customer_id, authenticated_user = user_resource()

    # create a shopping chart with id
    shop_order_id = get_shopping_chart_id()

    positions = [
        { "productCode": 290, "price": 270, "sender": "", "receiver": "" },
        { "productCode": 290, "price": 270, "sender": "", "receiver": "" },
    ]

    # buy shopping chart
    response = checkout_shopping_chart_png(shop_order_id, [])
    images = download_and_unpack(response['link'], )

if __name__ == "__main__":
    main()