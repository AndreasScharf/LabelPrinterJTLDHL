from jinja2 import Template
from weasyprint import HTML

from utils import asset_path


def _insert_breaklines(line):

    if line:
        return line.replace('\n', '<br>')
            
    return False

import base64
import mimetypes

def image_bytes_to_base64_uri(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """
    Convert raw image bytes to a base64 data URI for embedding in HTML.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"

def image_file_to_base64_uri(path: str) -> str:
    """
    Reads a local image file and returns a base64 data URI for embedding in HTML/PDF.
    """
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"

def prepare_pdf_blob( send_addr, data, postmarks ):
    # convert images
    for i in range(len(postmarks)):
        if postmarks[i]:
            postmarks[i] = image_bytes_to_base64_uri(postmarks[i])

    labels_file = asset_path("labels.html")
    html_tpl = open(labels_file, "r", encoding="utf-8").read()
    
    data = list(map(_insert_breaklines, data))

     # Convert logo.png to base64 data URI
    logo_data_uri = image_file_to_base64_uri(asset_path("header.png"))

    t = Template(html_tpl)
    html = t.render(
        logo_url=logo_data_uri,
        tl=data[0], tr=data[1], bl=data[2], br=data[3],
        send_addr= send_addr,
        tl_img=postmarks[0],   # per-segment extra picture (optional)
        tr_img=postmarks[1],   # per-segment extra picture (optional)
        bl_img=postmarks[2],
        br_img=postmarks[3],
        
    )

    tmp_file = asset_path("tmp.html")
    open(tmp_file, "w", encoding="utf-8").write(html)

    # base_url="." makes relative image paths work
    h = HTML(string=html, base_url=".")

    pdf_blob = h.write_pdf()
    return pdf_blob
