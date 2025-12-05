# src/database/crud.py
"""
CRUD operations cho các bảng Category, ProductLine, Product, FileVectorStore
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from .models import Category, ProductLine, Product, FileVectorStore


# ==================== CATEGORY ====================
def create_category(db: Session, id: str, name: str) -> Category:
    """Tạo category mới"""
    category = Category(id=id, name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def get_category(db: Session, category_id: str) -> Optional[Category]:
    """Lấy category theo id"""
    return db.query(Category).filter(Category.id == category_id).first()


def get_category_by_name(db: Session, name: str) -> Optional[Category]:
    """Lấy category theo tên"""
    return db.query(Category).filter(Category.name == name).first()


def get_all_categories(db: Session) -> List[Category]:
    """Lấy tất cả categories"""
    return db.query(Category).all()


def get_or_create_category(db: Session, id: str, name: str) -> Category:
    """Lấy hoặc tạo category mới nếu chưa tồn tại"""
    category = get_category(db, id)
    if not category:
        category = create_category(db, id, name)
    return category


# ==================== PRODUCT LINE ====================
def create_product_line(db: Session, id: str, name: str, category_id: str) -> ProductLine:
    """Tạo product line mới"""
    product_line = ProductLine(id=id, name=name, category_id=category_id)
    db.add(product_line)
    db.commit()
    db.refresh(product_line)
    return product_line


def get_product_line(db: Session, product_line_id: str) -> Optional[ProductLine]:
    """Lấy product line theo id"""
    return db.query(ProductLine).filter(ProductLine.id == product_line_id).first()


def get_product_line_by_name(db: Session, name: str, category_id: str) -> Optional[ProductLine]:
    """Lấy product line theo tên và category"""
    return db.query(ProductLine).filter(
        ProductLine.name == name,
        ProductLine.category_id == category_id
    ).first()


def get_product_lines_by_category(db: Session, category_id: str) -> List[ProductLine]:
    """Lấy tất cả product lines của một category"""
    return db.query(ProductLine).filter(ProductLine.category_id == category_id).all()


def get_all_product_lines(db: Session) -> List[ProductLine]:
    """Lấy tất cả product lines"""
    return db.query(ProductLine).all()


def get_or_create_product_line(db: Session, id: str, name: str, category_id: str) -> ProductLine:
    """Lấy hoặc tạo product line mới nếu chưa tồn tại"""
    product_line = get_product_line(db, id)
    if not product_line:
        product_line = create_product_line(db, id, name, category_id)
    return product_line


# ==================== PRODUCT ====================
def create_product(db: Session, id: str, name: str, product_line_id: str) -> Product:
    """Tạo product mới"""
    product = Product(id=id, name=name, product_line_id=product_line_id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: str) -> Optional[Product]:
    """Lấy product theo id"""
    return db.query(Product).filter(Product.id == product_id).first()


def get_product_by_name(db: Session, name: str, product_line_id: str) -> Optional[Product]:
    """Lấy product theo tên và product line"""
    return db.query(Product).filter(
        Product.name == name,
        Product.product_line_id == product_line_id
    ).first()


def get_products_by_product_line(db: Session, product_line_id: str) -> List[Product]:
    """Lấy tất cả products của một product line"""
    return db.query(Product).filter(Product.product_line_id == product_line_id).all()


def get_all_products(db: Session) -> List[Product]:
    """Lấy tất cả products"""
    return db.query(Product).all()


def get_or_create_product(db: Session, id: str, name: str, product_line_id: str) -> Product:
    """Lấy hoặc tạo product mới nếu chưa tồn tại"""
    product = get_product(db, id)
    if not product:
        product = create_product(db, id, name, product_line_id)
    return product


# ==================== FILE VECTOR STORE ====================
def create_file(db: Session, id: str, name: str, product_id: str) -> FileVectorStore:
    """Tạo file mới"""
    file = FileVectorStore(id=id, name=name, product_id=product_id)
    db.add(file)
    db.commit()
    db.refresh(file)
    return file


def get_file(db: Session, file_id: str) -> Optional[FileVectorStore]:
    """Lấy file theo id"""
    return db.query(FileVectorStore).filter(FileVectorStore.id == file_id).first()


def get_file_by_name(db: Session, name: str, product_id: str) -> Optional[FileVectorStore]:
    """Lấy file theo tên và product"""
    return db.query(FileVectorStore).filter(
        FileVectorStore.name == name,
        FileVectorStore.product_id == product_id
    ).first()


def get_files_by_product(db: Session, product_id: str) -> List[FileVectorStore]:
    """Lấy tất cả files của một product"""
    return db.query(FileVectorStore).filter(FileVectorStore.product_id == product_id).all()


def get_all_files(db: Session) -> List[FileVectorStore]:
    """Lấy tất cả files"""
    return db.query(FileVectorStore).all()


def get_or_create_file(db: Session, id: str, name: str, product_id: str) -> FileVectorStore:
    """Lấy hoặc tạo file mới nếu chưa tồn tại"""
    file = get_file(db, id)
    if not file:
        file = create_file(db, id, name, product_id)
    return file


# ==================== HELPER ====================
def delete_file(db: Session, file_id: str) -> bool:
    """Xóa file"""
    file = get_file(db, file_id)
    if file:
        db.delete(file)
        db.commit()
        return True
    return False


def delete_product(db: Session, product_id: str) -> bool:
    """Xóa product và cascade xóa các files"""
    product = get_product(db, product_id)
    if product:
        db.delete(product)
        db.commit()
        return True
    return False


def delete_product_line(db: Session, product_line_id: str) -> bool:
    """Xóa product line và cascade xóa products + files"""
    product_line = get_product_line(db, product_line_id)
    if product_line:
        db.delete(product_line)
        db.commit()
        return True
    return False


def delete_category(db: Session, category_id: str) -> bool:
    """Xóa category và cascade xóa tất cả con cháu"""
    category = get_category(db, category_id)
    if category:
        db.delete(category)
        db.commit()
        return True
    return False
