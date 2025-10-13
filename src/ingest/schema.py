from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class DocMeta(BaseModel):
    product_line: str               # UPS | Thermal | DC_Power | ...
    product_name: Optional[str] = None
    model: Optional[str] = None     # ví dụ: Liebert GXT5, NetSure 7100, v.v.
    sku: Optional[str] = None
    region: Optional[str] = None    # VN | APAC | Global ...
    language: str = "vi"            # vi | en | zh ...
    doc_type: str                   # spec | manual | brochure | faq | whitepaper
    version: Optional[str] = None
    publish_date: Optional[date] = None
    source: str                     # tên file hoặc URL gốc
    page_range: Optional[List[int]] = None
    checksum: Optional[str] = None