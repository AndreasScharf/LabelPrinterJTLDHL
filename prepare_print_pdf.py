from jinja2 import Template
from weasyprint import HTML



def _insert_breaklines(line):

    if line:
        return line.replace('\n', '<br>')
            
    return False

import base64

def image_bytes_to_base64_uri(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """
    Convert raw image bytes to a base64 data URI for embedding in HTML.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"

def prepare_pdf_blob( send_addr, data, postmarks ):
    # convert images
    for i in range(len(postmarks)):
        if postmarks[i]:
            postmarks[i] = image_bytes_to_base64_uri(postmarks[i])


    html_tpl = open("labels.html", "r", encoding="utf-8").read()
    
    data = list(map(_insert_breaklines, data))

    t = Template(html_tpl)
  
    html = t.render(
        logo_url='url("./assets/header.png")',   # common logo (optional)
        tl=data[0], tr=data[1], bl=data[2], br=data[3],
        send_addr= send_addr,
        tl_img=postmarks[0],   # per-segment extra picture (optional)
        tr_img=postmarks[1],   # per-segment extra picture (optional)
        bl_img=postmarks[2],
        br_img=postmarks[3],
        
    )

    open("tmp.html", "w", encoding="utf-8").write(html)

    # base_url="." makes relative image paths work
    h = HTML(string=html, base_url=".")

    pdf_blob = h.write_pdf()
    return pdf_blob
