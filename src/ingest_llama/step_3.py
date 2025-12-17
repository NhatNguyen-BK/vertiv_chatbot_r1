from .step_2 import process_data_md
from llama_index.core import Document
from llama_index.core.schema import TextNode
import os
import re

def split_by_headers_preserve_markdown(text: str, file_name: str):
    """
    Tách markdown theo headers (# và ##) nhưng GIỮ NGUYÊN header markers trong text
    """
    # Regex để tìm headers (# hoặc ##)
    header_pattern = re.compile(r'^(#{1,2})\s+(.+)$', re.MULTILINE)
    
    sections = []
    current_section = []
    current_headers = []
    
    lines = text.split('\n')
    
    for line in lines:
        match = header_pattern.match(line)
        
        if match:
            # Gặp header mới
            # Lưu section cũ nếu có
            if current_section:
                section_text = '\n'.join(current_section).strip()
                if section_text:
                    sections.append({
                        'text': section_text,
                        'headers': current_headers.copy()
                    })
            
            # Bắt đầu section mới
            level = len(match.group(1))  # Số lượng #
            header_text = match.group(2).strip()
            
            # Reset headers tùy theo level
            if level == 1:
                current_headers = [header_text]
            elif level == 2:
                if len(current_headers) > 0:
                    current_headers = [current_headers[0], header_text]
                else:
                    current_headers = [header_text]
            
            current_section = [line]  # Giữ nguyên dòng header với #
        else:
            current_section.append(line)
    
    # Lưu section cuối cùng
    if current_section:
        section_text = '\n'.join(current_section).strip()
        if section_text:
            sections.append({
                'text': section_text,
                'headers': current_headers.copy()
            })
    
    # Convert sang TextNode
    nodes = []
    for idx, section in enumerate(sections):
        node = TextNode(
            text=section['text'],
            metadata={
                'file_name': file_name,
                'section_index': idx,
                'headers': section['headers']
            }
        )
        nodes.append(node)
    
    return nodes

def get_nodes_from_document(pdf_path):
    merged_text, product_name, file_name = process_data_md(pdf_path)
    
    # Tách theo headers nhưng giữ nguyên markdown format
    nodes = split_by_headers_preserve_markdown(merged_text, file_name)
    
    return nodes